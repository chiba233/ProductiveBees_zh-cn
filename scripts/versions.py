#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把资源蜜蜂**所有版本**的 key 并起来，算出我们还缺什么。

这个仓库的目的是覆盖几乎所有用了资源蜜蜂的热门整合包。整合包用的版本五花八门，
所以判断「翻全了没有」不能只对着一个 jar——得对着**全历史版本的并集**。

干三件事：

1. 把 CurseForge 上这个模组的文件列表整个翻一遍，按 (MC 版本, 加载器) 取最新的一份
2. 逐个下下来（按 sha256 记档），抽出 `en_us` 的全部 key 与导览书文件清单
3. 算并集，报出我们的 `src/lang/zh_cn.json` 还缺哪些——**这就是待办清单**

产出 `versions/targets.json`（每个目标的 fileID + sha256，构建时按它取 jar）
与 `versions/keys.json`（每个 key 出现在哪些版本里）。

用法:
    python3 scripts/versions.py scan      # 重新扫（联网，会下十几个 jar）
    python3 scripts/versions.py gap       # 只报缺口（用已存的 keys.json，不联网）
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / 'versions'
CACHE = ROOT / 'build' / 'pbjars'
PROJECT = 377897                       # CurseForge 上的 Productive Bees
API = 'https://www.curseforge.com/api/v1/mods/%d' % PROJECT
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
LOADERS = ('NeoForge', 'Forge', 'Fabric', 'Quilt')


def is_release(mc):
    """只认 1.x 的正式版。CurseForge 的 gameVersions 里混着快照与内部编号
    （实测有个 "26.1.2"），当成 MC 版本解析会算出荒唐的 Java 版本。"""
    p = mc.split('.')
    return len(p) >= 2 and p[0] == '1' and all(x.isdigit() for x in p)


def java_for(mc):
    """那一版 Minecraft 跑在哪个 Java 上——决定字节码目标，也决定一个 jar 跨不了多少版本。"""
    p = [int(x) for x in mc.split('.')[:3]] + [0, 0]
    if p[1] <= 16:
        return 8
    if p[1] == 17:
        return 17
    if p[1] <= 19:
        return 17
    if p[1] == 20 and p[2] < 5:
        return 17
    return 21


def toolchain(mc, ld):
    """这个平台由哪条构建路径出包。

    ModDevGradle 建立在 NeoForm 上，覆盖不到 1.16 及更早。那批不走 Gradle，
    走 `scripts/legacy.py`：对着 Forge 官方 jar 直接 javac——这个 mod 不调任何
    Minecraft 方法（全按类型反射），所以不需要重映射，也就不需要那一套工具链。
    """
    p = [int(x) for x in mc.split('.')[:3]] + [0, 0]
    return 'gradle' if p[1] >= 17 else 'javac'


def buildable(mc, ld):
    """我们**当前的构建工具链**能不能出这个平台的 jar。

    写进数据里而不是嘴上说，免得矩阵看着很宽、实际出不来。
    """
    p = [int(x) for x in mc.split('.')[:3]] + [0, 0]
    if toolchain(mc, ld) == 'javac':
        return ld == 'Forge'          # 那个年代只有 Forge
    if p[1] >= 20:
        return True
    return ld == 'Forge'              # 1.17–1.19 的 NeoForge 不存在


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), str(r.url)


def mcver(v):
    try:
        return [int(x) for x in v.split('.')]
    except ValueError:
        return [0]


def list_files():
    """把文件列表整个翻一遍。"""
    out = []
    for page in range(0, 20):
        d = json.loads(get('%s/files?pageSize=50&pageIndex=%d' % (API, page))[0])
        if not d.get('data'):
            break
        out += d['data']
        time.sleep(0.25)
    return out


def pick_targets(files):
    """按 (MC 版本, 加载器) 取最新的一份。fileID 越大越新。"""
    best = {}
    for f in files:
        gv = f.get('gameVersions') or []
        loaders = [g for g in gv if g in LOADERS]
        mcs = [g for g in gv if is_release(g)]
        for mc in mcs:
            for ld in (loaders or ['Forge']):
                k = (mc, ld)
                if k not in best or f['id'] > best[k]['id']:
                    best[k] = f
    return best


def download(f):
    CACHE.mkdir(parents=True, exist_ok=True)
    url = '%s/files/%d/download' % (API, f['id'])
    # 文件名从跳转后的地址取；本地已有就不再拉正文
    data, final = get(url, timeout=300)
    name = urllib.parse.unquote(final.rsplit('/', 1)[-1].split('?')[0])
    p = CACHE / name
    if not p.is_file():
        p.write_bytes(data)
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def probe(jar):
    """抽出这一版的 en_us key 与导览书文件清单。

    key 取**本体加内嵌 jar** 的并集：1.21.1 起升级组件搬进了 `productivelib`，
    而那个 mod 是打包在资源蜜蜂 jar 里（`META-INF/jarjar/`）发的。只认
    `assets/productivebees/` 的话，那 18 个物品名不会出现在键表里，
    缺口报表和覆盖率都看不见它们，游戏里却是实打实的英文。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pack                                          # noqa: PLC0415
    langs = pack.bundled_langs(jar)
    if not langs:
        return None, None
    en = {}
    for _, sub in sorted(langs.items()):
        en.update(sub)
    z = zipfile.ZipFile(jar)
    bk = sorted(n.split('guide/en_us/')[1][:-5] for n in z.namelist()
                if 'guide/en_us/' in n and n.endswith('.json'))
    return en, bk


def scan():
    files = list_files()
    print('CurseForge 上共 %d 个文件' % len(files))
    targets, keys, books = {}, defaultdict(list), defaultdict(list)
    picked = pick_targets(files)
    print('按 (MC 版本, 加载器) 取最新，共 %d 个目标' % len(picked))
    for (mc, ld) in sorted(picked, key=lambda k: (mcver(k[0]), k[1]), reverse=True):
        f = picked[(mc, ld)]
        try:
            jar, sha = download(f)
        except Exception as e:
            print('  %-8s %-9s ❌ %r' % (mc, ld, e))
            continue
        en, bk = probe(jar)
        if en is None:
            print('  %-8s %-9s ❌ 没有 en_us' % (mc, ld))
            continue
        tag = '%s-%s' % (mc, ld.lower())
        targets[tag] = {
            'minecraft': mc, 'loader': ld, 'java': java_for(mc),
            'buildable': buildable(mc, ld), 'toolchain': toolchain(mc, ld),
            'legacy': ld == 'Forge' or mcver(mc)[:2] <= [1, 20],
            'jar': jar.name, 'curseforge_project_id': PROJECT,
            'curseforge_file_id': f['id'], 'sha256': sha,
            'lang_keys': len(en), 'book_files': len(bk),
        }
        for k in en:
            keys[k].append(tag)
        for b in bk:
            books[b].append(tag)
        print('  %-8s %-9s %-40s lang %4d  导览书 %3d'
              % (mc, ld, jar.name, len(en), len(bk)))
        time.sleep(0.3)

    VERSIONS.mkdir(exist_ok=True)
    (VERSIONS / 'targets.json').write_text(json.dumps(
        targets, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (VERSIONS / 'keys.json').write_text(json.dumps(
        {'lang': {k: sorted(v) for k, v in sorted(keys.items())},
         'books': {k: sorted(v) for k, v in sorted(books.items())}},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('\n并集：lang key %d 个，导览书文件 %d 个' % (len(keys), len(books)))
    gap()


def have_books():
    base = ROOT / 'src' / 'books' / 'patchouli_books' / 'guide' / 'zh_cn'
    return {p.relative_to(base).as_posix().replace('.json.json', '')
            for p in base.rglob('*.json')}


def gap():
    """报缺口——这就是待办清单。lang 与导览书都要报：只报 lang 会让人以为
    只差一点点，其实有些目标是卡在导览书上。"""
    data = json.loads((VERSIONS / 'keys.json').read_text(encoding='utf-8'))
    targets = json.loads((VERSIONS / 'targets.json').read_text(encoding='utf-8'))
    zh = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))
    allkeys = data['lang']
    miss = {k: v for k, v in allkeys.items() if k not in zh}
    print('\n=== 覆盖情况 ===')
    print('全历史版本 lang key 并集 %d 个；我们有 %d 条译文；**缺 %d 个**'
          % (len(allkeys), len(zh), len(miss)))
    print('\n按目标看（缺几个就是那个整合包会露几处英文）：')
    books = have_books()
    for tag in sorted(targets, key=lambda t: (mcver(targets[t]['minecraft']),
                                              targets[t]['loader']), reverse=True):
        need = [k for k, v in allkeys.items() if tag in v]
        bad = [k for k in need if k not in zh]
        nb = [k for k, v in data['books'].items() if tag in v]
        bb = [k for k in nb if k not in books]
        flag = '✅' if not bad and not bb else '❌'
        print('  %s %-16s lang %4d/%-4d 缺%-4d  导览书 %3d/%-3d 缺%d'
              % (flag, tag, len(need) - len(bad), len(need), len(bad),
                 len(nb) - len(bb), len(nb), len(bb)))
    if miss:
        pref = defaultdict(int)
        for k in miss:
            pref[re.sub(r'\.[^.]+$', '', k) if k.count('.') > 1 else k] += 1
        print('\n缺的 key 按前缀（多半成规律，能批量补）：')
        for p, c in sorted(pref.items(), key=lambda x: -x[1])[:12]:
            print('  %-56s %d' % (p, c))
    return miss


def derive():
    """把**能从版本号推出来的字段**重算一遍，不必重下 20 个 jar。

    java / buildable / toolchain / legacy 全是版本的函数，手写迟早对不上。
    `loader_version` 例外：它是外面那个加载器的发行版本，已经填了的**不动**——
    换一个版本号就等于把一个已经绿的平台重新赌一次，不值当。
    """
    p = VERSIONS / 'targets.json'
    t = json.loads(p.read_text(encoding='utf-8'))
    changed = []
    for tag, v in t.items():
        for k, val in (('java', java_for(v['minecraft'])),
                       ('buildable', buildable(v['minecraft'], v['loader'])),
                       ('toolchain', toolchain(v['minecraft'], v['loader'])),
                       ('legacy', v['loader'] == 'Forge'
                        or mcver(v['minecraft'])[:2] <= [1, 20])):
            if v.get(k) != val:
                changed.append('%s.%s: %r → %r' % (tag, k, v.get(k), val))
                v[k] = val
    p.write_text(json.dumps(t, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
                 encoding='utf-8')
    print('派生字段重算完毕，%d 处变化：' % len(changed))
    for c in changed:
        print('  ', c)
    return changed


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('scan', 'gap', 'derive'):
        sys.exit(__doc__)
    {'scan': scan, 'gap': gap, 'derive': derive}[sys.argv[1]]()
