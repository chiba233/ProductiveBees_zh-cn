#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Modrinth 那一侧的整合包扫描。CurseForge 不是全部。

Modrinth 上整合包有一万七千多个。和 CurseForge 不同，它**没有反向依赖接口**，
所以只能把整合包全部列一遍，逐个翻里面有没有资源蜜蜂、有没有自定义蜂名。

好在 `.mrpack` 很小：模组是按 URL 引用的，包里只有 `modrinth.index.json` 与
`overrides/`——多数只有几百 KB。再加上 Range 读（只取压缩包中央目录和要的那几条），
一万七千个包扫得动。

拆包、认 key 的规矩与 CurseForge 那侧**共用同一份代码**（`addons.harvest`），
免得两边各写一套然后结论对不上。

产出：`build/modrinth/results*.json`，与 CurseForge 那侧同构，由
`addons.py merge` 合并。

用法:
    python3 scripts/modrinth.py list
    python3 scripts/modrinth.py scan [N|all] [--shard i/N]
"""
import json
import os
import sys
import threading
import time
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import addons

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / 'versions'
CACHE = ROOT / 'build' / 'modrinth'
API = 'https://api.modrinth.com/v2'
PB = 'jH6iiqkd'                      # Productive Bees 在 Modrinth 的项目 id
PAGE = 100

_lock = threading.Lock()


def api(path):
    return json.loads(addons.get(API + path)[0])


def fetch_list():
    """把 Modrinth 上的整合包全部列出来。"""
    facets = urllib.parse.quote('[["project_type:modpack"]]')
    out, offset, total = [], 0, None
    while True:
        d = api('/search?facets=%s&limit=%d&offset=%d&index=downloads'
                % (facets, PAGE, offset))
        total = d['total_hits']
        hits = d.get('hits') or []
        if not hits:
            break
        for h in hits:
            out.append({'id': h['project_id'], 'slug': h['slug'],
                        'name': h['title'], 'downloads': h.get('downloads') or 0})
        offset += PAGE
        if offset >= min(total, 10000):
            # 搜索接口翻不过 10000 条，剩下的按下载量倒序再来一趟
            break
        time.sleep(0.1)
    if total and total > 10000:
        offset = 0
        while offset < min(total - 10000, 10000):
            d = api('/search?facets=%s&limit=%d&offset=%d&index=newest'
                    % (facets, PAGE, offset))
            hits = d.get('hits') or []
            if not hits:
                break
            for h in hits:
                out.append({'id': h['project_id'], 'slug': h['slug'],
                            'name': h['title'],
                            'downloads': h.get('downloads') or 0})
            offset += PAGE
            time.sleep(0.1)
    seen, rows = set(), []
    for r in out:
        if r['id'] not in seen:
            seen.add(r['id'])
            rows.append(r)
    rows.sort(key=lambda r: -r['downloads'])
    VERSIONS.mkdir(exist_ok=True)
    (VERSIONS / 'modrinth_packs.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('Modrinth 整合包：接口说 %d 个，列到 %d 个' % (total, len(rows)))
    return rows


def rows():
    p = VERSIONS / 'modrinth_packs.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else fetch_list()


def newest_file(pid):
    vs = api('/project/%s/version' % pid)
    for v in vs:
        for f in v.get('files', []):
            if f.get('primary') and f['filename'].endswith('.mrpack'):
                return v, f
        for f in v.get('files', []):
            if f['filename'].endswith('.mrpack'):
                return v, f
    return None, None


def uses_pb(z):
    """这个包里到底有没有资源蜜蜂——看 index 里引用的下载地址。"""
    try:
        idx = json.loads(z.read('modrinth.index.json').decode('utf-8-sig'))
    except Exception:                                 # noqa: BLE001
        return None
    for f in idx.get('files', []):
        for u in f.get('downloads', []):
            if PB in u or 'productivebees' in u.lower():
                return True
    return False


def scan_one(r):
    ver, f = newest_file(r['id'])
    if not f:
        raise RuntimeError('没有 .mrpack')
    src, how = addons.remote_or_local(f['url'])
    try:
        with zipfile.ZipFile(src) as z:
            pb = uses_pb(z)
            keys, stats = addons.harvest(z, budget=[addons.MAX_PROJECT])
    finally:
        try:
            src.close()
        except Exception:                             # noqa: BLE001
            pass
    stats['how'] = how
    stats['pb'] = pb
    return {'file': f['filename'], 'version': ver.get('id'),
            'keys': keys, 'stats': stats, 'platform': 'modrinth'}


def scan(limit, shard=None, workers=5):
    all_rows = rows()
    todo = all_rows if limit is None else all_rows[:limit]
    tag = ''
    if shard:
        i, n = shard
        todo = todo[i::n]
        tag = '-%d' % i
    CACHE.mkdir(parents=True, exist_ok=True)
    out_path = CACHE / ('results%s.json' % tag)
    res = json.loads(out_path.read_text(encoding='utf-8')) if out_path.is_file() else {}
    pending = [r for r in todo if r['id'] not in res]
    print('Modrinth 整合包 %d 个，本片 %d 个，还没扫过 %d 个'
          % (len(all_rows), len(todo), len(pending)))
    done = [0]

    def work(r):
        try:
            got = scan_one(r)
        except Exception as e:                        # noqa: BLE001
            got = {'error': str(e)[:60], 'platform': 'modrinth'}
        with _lock:
            res[r['id']] = dict(got, name=r['name'], downloads=r['downloads'])
            done[0] += 1
            n = len(got.get('keys') or {})
            if n:
                print('  %-42s key %d' % (r['name'][:42], n))
            if done[0] % 100 == 0:
                out_path.write_text(json.dumps(res, ensure_ascii=False) + '\n',
                                    encoding='utf-8')
                print('  … %d/%d' % (done[0], len(pending)))

    if pending:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(work, pending))
    out_path.write_text(json.dumps(res, ensure_ascii=False) + '\n', encoding='utf-8')
    ok = sum(1 for v in res.values() if not v.get('error'))
    withpb = sum(1 for v in res.values() if (v.get('stats') or {}).get('pb'))
    withkeys = sum(1 for v in res.values() if v.get('keys'))
    print('\n扫完 %d 个（失败 %d），其中 %d 个装了资源蜜蜂、%d 个自带蜂名'
          % (ok, len(res) - ok, withpb, withkeys))
    return res


def parse_shard(argv):
    for a in argv:
        if a.startswith('--shard'):
            v = a.split('=', 1)[1] if '=' in a else argv[argv.index(a) + 1]
            i, n = v.split('/')
            return int(i), int(n)
    return None


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] not in ('list', 'scan'):
        sys.exit(__doc__)
    if a[0] == 'list':
        fetch_list()
    else:
        pos = [x for x in a[1:] if not x.startswith('--')]
        lim = (None if pos and pos[0] == 'all'
               else int(pos[0]) if pos else 300)
        scan(lim, parse_shard(a), workers=int(os.environ.get('PB_WORKERS', '5')))
