#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""扫「别人往 productivebees 命名空间里加的 key」。

资源蜜蜂有一套**可配置蜂**：整合包用数据包定义新蜂、新蜜脾，名字则由整合包自己的
资源包提供 `assets/productivebees/lang/*.json`。附属模组同理。这些 key 不在模组
本体的 en_us 里，只扫本体是扫不到的——而它们恰恰是各个整合包里露英文的地方。

CurseForge 有反向依赖接口 `/mods/<id>/dependents`，能把「用了资源蜜蜂的项目」
整个列出来（模组 + 整合包，带下载量）。逐个下下来，翻里面所有
`assets/productivebees/lang/*.json`（整合包的还要翻 `overrides/`）。

整合包的 zip 只含 manifest 与 overrides，不含 mod 本体，所以一般只有几 MB～几十 MB。

产出：
    versions/dependents.json   用了资源蜜蜂的项目清单（README 的覆盖范围就是它）
    versions/addon_keys.json   {key: {"en": 原文, "from": [项目…]}}

用法:
    python3 scripts/addons.py list              # 只拉清单，不下包
    python3 scripts/addons.py scan [数量]       # 按下载量从高到低扫，默认 60
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / 'versions'
CACHE = ROOT / 'build' / 'dependents'
PROJECT = 377897
API = 'https://www.curseforge.com/api/v1/mods'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
# 只认真正的语言文件，别把 en_us 之外的语言也当成新 key
LANG = re.compile(r'(^|/)assets/productivebees/lang/en_us\.json$')


def get(url, timeout=180, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={'User-Agent': UA}), timeout=timeout) as r:
                return r.read(), str(r.url)
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
            if e.code not in (403, 408, 429, 500, 502, 503, 504):
                break
        except Exception as e:
            last = repr(e)
        time.sleep(2 ** i)
    raise RuntimeError(last)


def fetch_list():
    out, i = [], 0
    while True:
        d = json.loads(get('%s/%d/dependents?index=%d&pageSize=50'
                           % (API, PROJECT, i * 50))[0])
        out += d['data']
        if len(out) >= d['pagination']['totalCount'] or not d['data']:
            break
        i += 1
        time.sleep(0.25)
    rows = []
    for x in out:
        rows.append({
            'id': x['id'], 'name': x['name'], 'slug': x['slug'],
            'kind': (x.get('categoryClass') or {}).get('name') or '?',
            'downloads': x.get('downloads') or 0,
            'author': x.get('authorName'),
            'pb_file': x.get('dependentFileName'),
        })
    rows.sort(key=lambda r: -r['downloads'])
    VERSIONS.mkdir(exist_ok=True)
    (VERSIONS / 'dependents.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    mods = sum(1 for r in rows if r['kind'] == 'Mods')
    print('用了资源蜜蜂的项目 %d 个（整合包 %d、模组 %d）'
          % (len(rows), len(rows) - mods, mods))
    return rows


def newest_file(pid):
    d = json.loads(get('%s/%d/files?pageSize=6&pageIndex=0' % (API, pid))[0])
    return (d.get('data') or [None])[0]


def keys_in(zpath):
    """翻一个 zip 里所有 productivebees 的 en_us。整合包的在 overrides/ 下。"""
    found = {}
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if not LANG.search(n):
                continue
            try:
                found.update(json.loads(z.read(n).decode('utf-8-sig')))
            except Exception:
                pass
    return found


def scan(limit):
    rows = json.loads((VERSIONS / 'dependents.json').read_text(encoding='utf-8')) \
        if (VERSIONS / 'dependents.json').is_file() else fetch_list()
    CACHE.mkdir(parents=True, exist_ok=True)
    keys, scanned, skipped = {}, [], 0
    for r in rows[:limit]:
        f = None
        try:
            f = newest_file(r['id'])
            if not f:
                raise RuntimeError('没有文件')
            data, final = get('%s/%d/files/%d/download' % (API, r['id'], f['id']))
            name = urllib.parse.unquote(final.rsplit('/', 1)[-1].split('?')[0])
            p = CACHE / ('%d-%s' % (r['id'], name))
            if not p.is_file():
                p.write_bytes(data)
            got = keys_in(p)
        except Exception as e:
            print('  %-44s ❌ %s' % (r['name'][:44], str(e)[:40]))
            skipped += 1
            continue
        if got:
            for k, v in got.items():
                e = keys.setdefault(k, {'en': v, 'from': []})
                e['from'].append(r['name'])
            print('  %-44s %-9s %8d 下载  productivebees key %d'
                  % (r['name'][:44], r['kind'], r['downloads'], len(got)))
        scanned.append(r['name'])
        time.sleep(0.4)

    (VERSIONS / 'addon_keys.json').write_text(json.dumps(
        {k: {'en': v['en'], 'from': sorted(set(v['from']))}
         for k, v in sorted(keys.items())},
        ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('\n扫了 %d 个项目（%d 个取不到），共见到 %d 个 productivebees key'
          % (len(scanned), skipped, len(keys)))
    gap(keys)


def gap(keys=None):
    if keys is None:
        keys = json.loads((VERSIONS / 'addon_keys.json').read_text(encoding='utf-8'))
    zh = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))
    base = json.loads((VERSIONS / 'keys.json').read_text(encoding='utf-8'))['lang']
    extra = {k: v for k, v in keys.items() if k not in base}
    miss = {k: v for k, v in extra.items() if k not in zh}
    print('其中模组本体没有的（整合包/附属自己加的）%d 个，我们还缺 %d 个'
          % (len(extra), len(miss)))
    for k in sorted(miss)[:20]:
        v = miss[k]
        print('   %-56s %-28r 来自 %s'
              % (k, v['en'] if isinstance(v, dict) else v,
                 (v.get('from') or ['?'])[0] if isinstance(v, dict) else '?'))
    return miss


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] not in ('list', 'scan', 'gap'):
        sys.exit(__doc__)
    if a[0] == 'list':
        fetch_list()
    elif a[0] == 'gap':
        gap()
    else:
        scan(int(a[1]) if len(a) > 1 else 60)
