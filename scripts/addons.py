#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""扫「别人往 productivebees 命名空间里加的 key」。

资源蜜蜂有一套**可配置蜂**：整合包用数据包定义新蜂、新蜜脾，名字则由整合包自己
提供 `assets/productivebees/lang/en_us.json`。这些 key 不在模组本体里——只扫本体
是扫不到的，而它们恰恰是各整合包里露英文的地方。

CurseForge 有反向依赖接口 `/mods/<id>/dependents`，把「用了资源蜜蜂的项目」整个
列出来。**分页参数是 `page`**（`index` 只是回显字段，传它不翻页，会把第一页拿 N
遍——踩过一次：清单看着 5740 行，去重后只有 50 个项目）。

整合包的自定义语言文件很少直接躺在 zip 根上，多半在**内嵌 zip**里：
`overrides/resourcepacks/*.zip`、`config/paxi/{resource,data}packs/*.zip`、
`config/openloader/resources/*.zip`，还有 `overrides/mods/*.jar`（不可分发的模组）。
所以必须往里再拆几层。

整包动辄上百 MB，5000+ 个不可能全下。这里走 **HTTP Range**：只取压缩包尾部的
中央目录看清里面有什么，再单独把要的那几条取回来。

产出：
    versions/dependents.json       项目清单（README 的覆盖范围就是它）
    versions/addon_keys.json       {key: {"en": 原文, "from": [项目…]}}
    build/dependents/results.json  每个项目扫出什么（可断点续扫）

用法:
    python3 scripts/addons.py list            # 拉项目清单
    python3 scripts/addons.py scan [N|all] [--shard=i/N]   # 按下载量从高到低扫
    python3 scripts/addons.py merge          # 合并两个平台各分片的结果并统计
    python3 scripts/addons.py selftest        # 只跑合成用例（不联网，CI 用）
    python3 scripts/addons.py verify [N]      # 验扫描器：合成用例 + 整包暴力对照
    python3 scripts/addons.py gap             # 报还缺多少译文
"""
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / 'versions'
CACHE = ROOT / 'build' / 'dependents'
RESULTS = CACHE / 'results.json'
PROJECT = 377897                                  # Productive Bees
API = 'https://www.curseforge.com/api/v1/mods'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# **任何**命名空间的 en_us 都要翻，不能只翻 assets/productivebees/ 下的那份：
# 游戏是按 key 合并全部语言文件的，文件搁在谁的命名空间下无所谓。附属模组正是
# 把 productivebees 的 key 写在自己那份里——Productive Trees 的三条、Every Compat
# 的蜂箱模板都是这么丢的（暴力对照抓出来的）。
# 只认 en_us：别的语言不是「新 key」，是别人已经翻过的。
LANG = re.compile(r'(^|/)assets/[a-z0-9_.-]+/lang/en_us\.json$', re.I)
# key 属不属于资源蜜蜂看**点分段**：productivebees.xxx、entity.productivebees.xxx、
# block_type.productivebees.xxx 都算，productivebeesfoo.xxx 不算。
KEYNS = re.compile(r'(^|\.)productivebees(\.|$)')
# 内嵌压缩包：资源包/数据包/不可分发的模组 jar 都得再拆一层
NESTED = re.compile(r'\.(zip|jar)$', re.I)

BLOCK = 1 << 20                # Range 一次取 1 MiB：取太碎就是几百个来回，比整包下还慢
MAX_NESTED = 48 << 20          # 单个内嵌包超过这个就不取
MAX_PROJECT = 192 << 20        # 一个项目总共最多取这么多
DEPTH = 3

_lock = threading.Lock()


# ── HTTP ────────────────────────────────────────────────────────────────────

def _open(url, headers=None, timeout=120, tries=5):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(
                url, headers=dict({'User-Agent': UA}, **(headers or {}))),
                timeout=timeout)
        except urllib.error.HTTPError as e:
            last = 'HTTP %d' % e.code
            if e.code not in (403, 408, 429, 500, 502, 503, 504):
                raise RuntimeError(last)
        except Exception as e:                       # noqa: BLE001
            last = type(e).__name__
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(last or '取不到')


def get(url, **kw):
    with _open(url, **kw) as r:
        return r.read(), str(r.url)


def api(path):
    return json.loads(get(API + path)[0])


class Remote(io.RawIOBase):
    """按 Range 读远端文件，够 zipfile 当普通文件用。

    zipfile 只会 seek 到尾巴找中央目录、再 seek 到要的那几条——真正读到的字节
    远少于整包。服务器不支持 Range 就退回整包下载。
    """

    def __init__(self, url):
        self.url = url
        self.pos = 0
        self.blocks = {}
        self.fetched = 0
        with _open(url, headers={'Range': 'bytes=0-1'}) as r:
            cr = r.headers.get('Content-Range')
            self.url = str(r.url)            # 记最终地址，省得每块都重定向一次
            r.read()
        if not cr or '/' not in cr:
            raise RuntimeError('不支持 Range')
        self.size = int(cr.rsplit('/', 1)[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = (off if whence == 0
                    else self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def _block(self, idx):
        if idx not in self.blocks:
            a = idx * BLOCK
            b = min(a + BLOCK, self.size) - 1
            if a > b:
                self.blocks[idx] = b''
            else:
                with _open(self.url, headers={'Range': 'bytes=%d-%d' % (a, b)}) as r:
                    self.blocks[idx] = r.read()
                self.fetched += b - a + 1
        return self.blocks[idx]

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        out = bytearray()
        while n:
            idx, off = divmod(self.pos, BLOCK)
            chunk = self._block(idx)[off:off + n]
            if not chunk:
                break
            out += chunk
            self.pos += len(chunk)
            n -= len(chunk)
        return bytes(out)


def remote_or_local(url):
    """能 Range 就 Range，不能就整包下到内存（很少数会走这条）。"""
    try:
        return Remote(url), 'range'
    except RuntimeError:
        data, _ = get(url)
        return io.BytesIO(data), 'full'


# ── 项目清单 ────────────────────────────────────────────────────────────────

def fetch_list(page_size=50):
    # 接口会跨页重复（totalCount 5740 而去重后只有两千多），所以**不能一见到
    # 重复页就收工**——中间夹着重复页，后面还有新项目。连续几页毫无新货才停。
    seen, out, page, total, dry = set(), [], 1, None, 0
    while True:
        d = api('/%d/dependents?page=%d&pageSize=%d' % (PROJECT, page, page_size))
        total = d['pagination']['totalCount']
        got = d.get('data') or []
        fresh = 0
        for x in got:
            if x['id'] in seen:
                continue
            seen.add(x['id'])
            fresh += 1
            out.append({
                'id': x['id'], 'name': x['name'], 'slug': x['slug'],
                'kind': (x.get('categoryClass') or {}).get('name') or '?',
                'downloads': x.get('downloads') or 0,
                'author': x.get('authorName'),
            })
        dry = 0 if fresh else dry + 1
        if not got or dry >= 8 or len(out) >= total:
            break
        page += 1
        if page > (total // page_size) + 8:
            break
        time.sleep(0.2)
    out.sort(key=lambda r: -r['downloads'])
    VERSIONS.mkdir(exist_ok=True)
    (VERSIONS / 'dependents.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('用了资源蜜蜂的项目：接口说 %d 个，去重后拿到 %d 个' % (total, len(out)))
    return out


def rows():
    p = VERSIONS / 'dependents.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else fetch_list()


# ── 拆包 ────────────────────────────────────────────────────────────────────

def harvest(zf, depth=0, budget=None, stats=None, max_nested=None):
    """从一个已打开的 zip 里收 productivebees 的 en_us，必要时往内嵌包再钻。"""
    found = {}
    stats = stats if stats is not None else {}
    names = zf.namelist()
    stats['entries'] = stats.get('entries', 0) + len(names)
    for n in names:
        if not LANG.search(n):
            continue
        try:
            d = json.loads(zf.read(n).decode('utf-8-sig'))
        except Exception:                             # noqa: BLE001
            stats['bad_json'] = stats.get('bad_json', 0) + 1
            continue
        if isinstance(d, dict):
            found.update({k: v for k, v in d.items()
                          if isinstance(v, str) and KEYNS.search(k)})
            stats['lang_files'] = stats.get('lang_files', 0) + 1
    if depth >= DEPTH:
        return found, stats
    for info in zf.infolist():
        if (not NESTED.search(info.filename)
                or info.file_size > (max_nested or MAX_NESTED)):
            continue
        if budget is not None:
            if budget[0] <= 0:
                stats['budget_hit'] = True
                break
            budget[0] -= info.file_size
        try:
            with zipfile.ZipFile(io.BytesIO(zf.read(info.filename))) as inner:
                sub, _ = harvest(inner, depth + 1, budget, stats, max_nested)
        except Exception:                             # noqa: BLE001
            stats['bad_zip'] = stats.get('bad_zip', 0) + 1
            continue
        stats['nested'] = stats.get('nested', 0) + 1
        found.update(sub)
    return found, stats


def newest_file(pid):
    d = api('/%d/files?pageSize=4&pageIndex=0' % pid)
    return (d.get('data') or [None])[0]


def scan_one(r):
    f = newest_file(r['id'])
    if not f:
        raise RuntimeError('没有可下载的文件')
    src, how = remote_or_local('%s/%d/files/%d/download' % (API, r['id'], f['id']))
    try:
        with zipfile.ZipFile(src) as z:
            keys, stats = harvest(z, budget=[MAX_PROJECT])
    finally:
        try:
            src.close()
        except Exception:                             # noqa: BLE001
            pass
    stats['how'] = how
    stats['fetched'] = getattr(src, 'fetched', None)
    return {'file': f['id'], 'file_name': f.get('fileName'),
            'keys': keys, 'stats': stats}


def load_results():
    return json.loads(RESULTS.read_text(encoding='utf-8')) if RESULTS.is_file() else {}


def save_results(res):
    CACHE.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(res, ensure_ascii=False) + '\n', encoding='utf-8')


def scan(limit, workers=5, shard=None):
    all_rows = rows()
    todo = all_rows if limit is None else all_rows[:limit]
    global RESULTS
    if shard:
        # CI 上分片跑：每片一个结果文件，最后由 merge 合起来
        i, n = shard
        todo = todo[i::n]
        RESULTS = CACHE / ('results-%d.json' % i)
    res = load_results()
    pending = [r for r in todo if str(r['id']) not in res]
    print('清单 %d 个，本轮 %d 个，其中 %d 个还没扫过'
          % (len(all_rows), len(todo), len(pending)))
    done = [0]

    def work(r):
        try:
            out = scan_one(r)
        except Exception as e:                        # noqa: BLE001
            out = {'error': str(e)[:60]}
        with _lock:
            res[str(r['id'])] = dict(out, name=r['name'], downloads=r['downloads'])
            done[0] += 1
            n = len(out.get('keys') or {})
            if n or out.get('error'):
                print('  %-42s %s' % (r['name'][:42],
                                      out.get('error') or ('key %d' % n)))
            if done[0] % 50 == 0:
                save_results(res)
                print('  … %d/%d' % (done[0], len(pending)))

    if pending:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(work, pending))
    save_results(res)
    return report(res)


def fold(cur, new):
    """同一个项目的两份扫描结果合成一份：**key 取并集**。

    一个项目会在多个分片里各出现一次——分片是按「项目 × 游戏版本」切的，
    同一个模组的 1.20.1 那份和 1.21.1 那份落在不同片里。原先这里是
    `res[id] = v` 直接覆盖，于是**谁最后被读到谁说了算**：

        resultsmod-6  enderio_evolution-3.1.3-NeoForge-1.21.1.jar  keys=8
        resultsmod-7  enderio_evolution-1.1.5-Forge-1.20.1.jar     keys=0  ← 把上面那条顶掉

    末影接口：进化的 8 条蜂名就是这么丢的：1.20.1 那一版没带资源蜜蜂的语言文件，
    它那份空结果盖住了 1.21.1 那份。更糟的是这依赖分片顺序——同一份数据换个
    分法就是另一个结论，扫描结果因此不可复现。

    取并集之后，一个项目只要**有任何一个版本**带了 key，那些 key 就留得住。
    """
    if cur is None:
        return dict(new)
    out = dict(cur)
    keys = dict(cur.get('keys') or {})
    keys.update(new.get('keys') or {})
    if keys:
        out['keys'] = keys
        out.pop('error', None)             # 有一版扫成了，就不算这个项目失败
        # 留下真正带 key 的那一版的文件名，复查时能直接对上
        if not (cur.get('keys') or {}):
            for f in ('file', 'version'):
                if new.get(f) is not None:
                    out[f] = new[f]
    elif not new.get('error'):
        out.pop('error', None)
    out['downloads'] = max(cur.get('downloads') or 0, new.get('downloads') or 0)
    # 两边都没有的字段**不许凭空写成 None**：下游是 `r.get('platform', 'curseforge')`
    # 这种「键不在才走默认值」的写法，被写进一个 None 就等于默认值失效——
    # CurseForge 的项目数会从两千多掉到三百，另外多出一个叫 null 的平台。
    for f in ('name', 'platform'):
        v = cur.get(f) or new.get(f)
        if v is not None:
            out[f] = v
    return out


def merge():
    """把两个平台、各分片的结果合到一起再统计。

    CurseForge 有反向依赖接口，Modrinth 没有——那边只能把一万七千个整合包
    全列一遍逐个翻。两边拆包与认 key 用的是同一份代码，所以结果可以直接合。

    同一个项目在多个分片里各有一份，按 {@link fold} 取并集，不许互相顶掉。
    """
    res = {}
    for d, pref in ((CACHE, 'cf'), (ROOT / 'build' / 'modrinth', 'mr')):
        for p in sorted(d.glob('results*.json')):
            # `results.json` 是上一次 merge 自己存下的**合并结果**，再读进来就是把
            # 每个项目算两遍（`cf:mr:xxx` 与 `mr:xxx` 各一份），README 的覆盖数直接
            # 翻倍。CI 每次全新 checkout 碰不到，本地拿 artifact 复算一次就中招。
            if p == RESULTS:
                continue
            for k, v in json.loads(p.read_text(encoding='utf-8')).items():
                rid = '%s:%s' % (pref, k)
                res[rid] = fold(res.get(rid), v)
    save_results(res)
    print('合并 %d 个项目的扫描结果' % len(res))
    return report(res)


def report(res=None):
    res = res if res is not None else load_results()
    keys, ok, bad, withkeys = {}, 0, 0, 0
    for pid, r in res.items():
        if r.get('error'):
            bad += 1
            continue
        ok += 1
        if r.get('keys'):
            withkeys += 1
        for k, v in (r.get('keys') or {}).items():
            e = keys.setdefault(k, {'en': v, 'from': []})
            e['from'].append(r.get('name') or pid)
    # 覆盖范围要能写进 README，而 build/ 是不入库的临时目录——把摘要落到 versions/。
    # 只数**模组本体没有的** key：有些整合包自带一份别的语言的翻译资源包，
    # 里面是模组本体那一千多条 key，算进「自定义」就把表带偏了。
    base = json.loads((VERSIONS / 'keys.json').read_text(encoding='utf-8'))['lang']
    # 同一个整合包/模组两个平台各上架一份（`cf:…` 与 `mr:…` 两条记录），
    # 按名字并成一行再排，否则 README 的表里会出现同名两行、下载量还不一样。
    by_name = {}
    for r in res.values():
        if not r.get('keys'):
            continue
        row = by_name.setdefault(r.get('name'), {'name': r.get('name'),
                                                 'downloads': 0, 'keys': 0})
        row['downloads'] = max(row['downloads'], r.get('downloads') or 0)
        row['keys'] = max(row['keys'],
                          len([k for k in r['keys'] if k not in base]))
    packs = sorted((x for x in by_name.values() if x['keys']),
                   key=lambda x: (-x['keys'], -x['downloads']))
    plat = {}
    for r in res.values():
        p = r.get('platform', 'curseforge')
        plat[p] = plat.get(p, 0) + 1
    (VERSIONS / 'addon_scan.json').write_text(json.dumps(
        {'scanned': ok, 'failed': bad, 'total': len(rows()),
         'platforms': plat, 'keys': len(keys), 'packs': packs},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (VERSIONS / 'addon_keys.json').write_text(json.dumps(
        {k: {'en': v['en'], 'n': len(set(v['from'])),
             'from': sorted(set(v['from']))[:40]}
         for k, v in sorted(keys.items())},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('\n扫过 %d 个项目（%d 个取不到），%d 个自带 productivebees 语言文件，'
          '共见到 %d 个 key' % (ok, bad, withkeys, len(keys)))
    gap()
    return keys


def gap(quiet=False):
    keys = json.loads((VERSIONS / 'addon_keys.json').read_text(encoding='utf-8'))
    zh = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))
    base = json.loads((VERSIONS / 'keys.json').read_text(encoding='utf-8'))['lang']
    extra = {k: v for k, v in keys.items() if k not in base}
    miss = {k: v for k, v in extra.items() if k not in zh}
    if not quiet:
        print('其中模组本体没有的（整合包自己加的）%d 个，我们还缺 %d 个'
              % (len(extra), len(miss)))
        for k in sorted(miss, key=lambda k: -miss[k].get('n', 1))[:25]:
            print('   %-52s %-26s ×%d' % (k[:52], miss[k]['en'][:26],
                                          miss[k].get('n', 1)))
    return miss


# ── 验扫描器 ────────────────────────────────────────────────────────────────

def _zip(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        for n, d in entries.items():
            z.writestr(n, d if isinstance(d, (bytes, str))
                       else json.dumps(d, ensure_ascii=False))
    return b.getvalue()


def verify_synthetic():
    """合成用例。要立住的四条：

    1. key 归谁看**点分段**，不看文件搁在哪个命名空间下；
    2. 只认 en_us，zh_cn 是别人的译文不是新 key；
    3. 内嵌包要一路钻（资源包套数据包）；
    4. 名字像但不是的（productivebeesfoo）不能误收，坏 zip 不能把整个包带崩。
    """
    inner2 = _zip({'assets/pack/lang/en_us.json':
                   {'entity.productivebees.deep_bee': 'Deep Bee'}})
    inner = _zip({
        'assets/productivebees/lang/en_us.json':
            {'productivebees.rp': 'RP', 'item.othermod.decoy': '别收我'},
        'assets/productivebees/lang/zh_cn.json':
            {'productivebees.zh_decoy': '别收我'},
        'nested/again.zip': inner2,
    })
    pack = _zip({
        'manifest.json': {'name': 'x'},
        # 附属模组的典型摆法：PB 的 key 写在自己命名空间的语言文件里
        'overrides/mods/addon.jar': _zip({'assets/addon/lang/en_us.json': {
            'block_type.productivebees.advanced_beehive': 'Advanced %s Beehive',
            'productivebeesfoo.decoy': '别收我',
            'item.addon.decoy': '别收我'}}),
        'overrides/resourcepacks/rp.zip': inner,
        'overrides/mods/broken.jar': b'not a zip at all',
    })
    with zipfile.ZipFile(io.BytesIO(pack)) as z:
        got, stats = harvest(z, budget=[MAX_PROJECT])
    want = {'productivebees.rp', 'entity.productivebees.deep_bee',
            'block_type.productivebees.advanced_beehive'}
    bad = [k for k in got if k not in want] + [k for k in want if k not in got]
    print('合成用例：期望 %s' % sorted(want))
    print('          实收 %s   坏 zip %d 个已跳过'
          % (sorted(got), stats.get('bad_zip', 0)))
    assert not bad, '合成用例不过：多/少了 %s' % bad
    print('  ✅ 别人命名空间里的 PB key 收得到；zh_cn / 别家 key / '
          'productivebeesfoo 都没误收；两层内嵌钻得进去；坏 zip 只跳过不中断')

    # 同一个项目在多个分片里各出现一次（每个游戏版本一份文件）。合并时**取并集**，
    # 不许后读的把先读的顶掉——末影接口：进化的 8 条蜂名就是这么丢过一次：
    # 1.20.1 那一版没带资源蜜蜂语言文件，它那份 keys={} 盖住了 1.21.1 那份。
    # 反着也要验：真·失败的项目不能因为合并就被当成扫成功了。
    a = {'name': 'X', 'version': 'v3', 'file': 'x-1.21.1.jar',
         'keys': {'entity.productivebees.crude_steel_bee': 'Crude Steel Bee'},
         'downloads': 9255, 'platform': 'modrinth-mod'}
    b = {'name': 'X', 'version': 'v1', 'file': 'x-1.20.1.jar',
         'keys': {}, 'downloads': 9255, 'platform': 'modrinth-mod'}
    for order, tag in (((a, b), '带 key 的先读'), ((b, a), '带 key 的后读')):
        got = None
        for r in order:
            got = fold(got, r)
        assert got.get('keys') == a['keys'], '%s：并集丢了 %s' % (tag, got.get('keys'))
        assert not got.get('error'), '%s：不该判失败' % tag
    err = fold(fold(None, {'error': '404'}), {'error': 'timeout'})
    assert err.get('error'), '两份都失败时必须还是失败'
    ok = fold(fold(None, {'error': '404'}), {'keys': {'k': 'v'}})
    assert not ok.get('error') and ok['keys'] == {'k': 'v'}, '有一版扫成了就不算失败'
    # 两边都没有的字段不许凭空写成 None：下游 `r.get('platform', 'curseforge')`
    # 是「键不在才走默认值」，写进一个 None 就让默认值失效，CurseForge 的项目数
    # 会从两千多掉到三百、并多出一个叫 null 的平台。
    bare = fold({'keys': {'k': 'v'}}, {'keys': {}})
    assert 'platform' not in bare and 'name' not in bare, '凭空写出了 %s' % bare
    one = fold({'keys': {}}, {'keys': {'k': 'v'}, 'platform': 'modrinth-mod',
                              'name': 'X', 'file': 'x.jar'})
    assert (one['platform'] == 'modrinth-mod' and one['name'] == 'X'
            and one['file'] == 'x.jar'), one
    print('  ✅ 同项目多分片取并集：两种读入顺序结果一致，'
          '全失败仍判失败，一成一败判成功，空字段不写成 None')


def brute(blob):
    """暴力对照：不看路径，**每个** JSON 都翻，凡是 productivebees 的 key 都算。

    这是给快路径当真值用的——快路径只认 `assets/productivebees/lang/en_us.json`，
    要是有人把 key 塞在别处，这里看得见而快路径看不见，差额就摆出来。
    """
    found = {}

    def walk(zf, depth=0):
        for info in zf.infolist():
            n = info.filename
            if n.lower().endswith('.json') and info.file_size < (8 << 20):
                try:
                    d = json.loads(zf.read(n).decode('utf-8-sig'))
                except Exception:                     # noqa: BLE001
                    continue
                if not isinstance(d, dict):
                    continue
                for k, v in d.items():
                    if isinstance(v, str) and ('productivebees' in k.split('.')[0]
                                               or '.productivebees.' in k):
                        found.setdefault(k, (v, n))
            elif NESTED.search(n) and depth < DEPTH and info.file_size < MAX_NESTED:
                try:
                    with zipfile.ZipFile(io.BytesIO(zf.read(n))) as inner:
                        walk(inner, depth + 1)
                except Exception:                     # noqa: BLE001
                    pass

    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        walk(z)
    return found


def verify(n=3):
    verify_synthetic()
    todo = rows()[:n]
    print('\n整包暴力对照（整个下下来逐个 JSON 翻，和快路径比）：')
    worst = 0
    for r in todo:
        try:
            f = newest_file(r['id'])
            blob, _ = get('%s/%d/files/%d/download' % (API, r['id'], f['id']))
            fast = scan_one(r)['keys']
            slow = brute(blob)
        except Exception as e:                        # noqa: BLE001
            print('  %-38s ❌ %s' % (r['name'][:38], str(e)[:40]))
            continue
        onlyslow = {k: v for k, v in slow.items() if k not in fast}
        print('  %-38s 快 %4d / 暴力 %4d   快路径漏 %d'
              % (r['name'][:38], len(fast), len(slow), len(onlyslow)))
        for k, (v, where) in sorted(onlyslow.items())[:6]:
            print('      漏：%-46s %-20s ← %s' % (k[:46], v[:20], where[:60]))
        worst = max(worst, len(onlyslow))
    print('\n%s' % ('  ✅ 快路径没漏' if not worst
                    else '  ⚠️ 快路径最多漏了 %d 个 key，位置见上' % worst))
    return worst


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] not in ('list', 'scan', 'gap', 'verify', 'report',
                             'selftest', 'merge'):
        sys.exit(__doc__)
    if a[0] == 'selftest':
        verify_synthetic()          # 只跑合成用例，不联网：CI 每次都跑得起
    elif a[0] == 'list':
        fetch_list()
    elif a[0] == 'gap':
        gap()
    elif a[0] == 'report':
        report()
    elif a[0] == 'merge':
        merge()
    elif a[0] == 'verify':
        sys.exit(1 if verify(int(a[1]) if len(a) > 1 else 3) else 0)
    else:
        pos = [x for x in a[1:] if not x.startswith('--')]
        lim = (None if pos and pos[0] == 'all' else int(pos[0]) if pos else 200)
        sh = None
        for x in a:
            if x.startswith('--shard='):
                i, n = x.split('=', 1)[1].split('/')
                sh = (int(i), int(n))
        scan(lim, workers=int(os.environ.get('PB_WORKERS', '5')), shard=sh)
