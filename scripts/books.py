#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""导览书汉化：把「原文 → 译文」映射套到**模组 jar 里那份**导览书上。

仓库里**没有任何一份上游导览书副本**。`src/books/**.json` 记的是
`{"src": jar 内路径, "sha1": 提取时的指纹, "t": [[JSON路径, 英文, 中文], …]}`，
构建时现取模组自带那份 JSON、逐条套上去。

## 判定是「上游漂移」还是「换了版本」

- **sha1 对得上** → 上游文件跟提取时一模一样，那么每一条译文都必须落位。
  落不下就是这个脚本自己有 bug，**硬失败**。
- **sha1 对不上** → 上游改过了（或者这是模组的另一个版本）。尽力套，落不下的
  逐条计数；整体命中率跌破下限就失败，避免「悄悄少翻一半」。
"""
import hashlib
import json
import sys
import zipfile
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / 'src' / 'books'

# 命中率下限：低于这个数说明不是零星漂移，而是整块对不上了
MIN_HIT = 0.90


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def walk(obj, pre=()):
    """产出 (JSON 路径, 字符串值)。

    路径是 ('pages', 0, 'text') 这样的**元组**，不是 `.pages[0].text` 那种拼接串：
    有些键名本身就带点，拼出来的路径没法还原。
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, pre + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, pre + (i,))
    elif isinstance(obj, str):
        yield pre, obj


def signature(o):
    """一个 JSON 结点的「形状」。译文和原文的字符串完全不同，配对只能靠形状。"""
    if isinstance(o, dict):
        return 'd:' + ','.join(sorted(o))
    if isinstance(o, list):
        return 'l:%d' % len(o)
    return 't:' + type(o).__name__


def pair(en, zh, pre=()):
    """同时走中英文两棵树，产出 (英文路径, 英文串, 中文串)。

    列表按**形状**对齐（difflib），所以上游在中间插一页不会让后面的译文整体错位。
    按下标硬对的话，上游在 pages[7] 插一页就会把第 8 页的中文糊到第 7 页上。

    只产出两边都有的位置：上游新增的（没译文）保持英文，我们多出来的（上游已删）丢弃。
    """
    if isinstance(en, dict) and isinstance(zh, dict):
        for k in en:
            if k in zh:
                yield from pair(en[k], zh[k], pre + (k,))
        return
    if isinstance(en, list) and isinstance(zh, list):
        se = [signature(x) for x in en]
        sz = [signature(x) for x in zh]
        for tag, i1, i2, j1, j2 in SequenceMatcher(
                None, se, sz, autojunk=False).get_opcodes():
            if tag != 'equal':
                continue
            for a, b in zip(range(i1, i2), range(j1, j2)):
                yield from pair(en[a], zh[b], pre + (a,))
        return
    if isinstance(en, str) and isinstance(zh, str):
        yield pre, en, zh


def get_at(obj, path):
    cur = obj
    for step in path:
        try:
            cur = cur[step]
        except (KeyError, IndexError, TypeError):
            return None
    return cur


def set_at(obj, path, value):
    cur = obj
    for step in path[:-1]:
        cur = cur[step]
    cur[path[-1]] = value


def dump(rel, doc):
    # 条目按 JSON 路径排序：重跑提取必须逐字节幂等，否则每次都出一堆纯顺序的假 diff
    if 't' in doc:
        doc['t'] = sorted(doc['t'], key=lambda e: [(1, str(x)) if isinstance(x, str)
                                                   else (0, '%09d' % x) for x in e[0]])
    p = BOOKS / (rel + '.json')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def apply_one(doc, entries, rel, strict, miss):
    """把 [路径, 英文, 中文] 逐条套到 doc 上。返回落位条数。"""
    ok = 0
    for path, en, zh in entries:
        path = tuple(path)
        if get_at(doc, path) == en:
            set_at(doc, path, zh)
            ok += 1
            continue
        # 位置漂了（上游插了一页之类）：全文找这段原文，唯一命中就照样翻
        where = [p for p, v in walk(doc) if v == en]
        if len(where) == 1:
            set_at(doc, where[0], zh)
            ok += 1
            continue
        if strict:
            sys.exit('❌ %s 的 %s 套不上，但上游文件与提取时逐字节相同——\n'
                     '   这是本脚本自己的 bug，不是上游漂移。\n'
                     '   原文: %r' % (rel, list(path), en[:80]))
        miss.append((rel, path, en[:60]))
    return ok


def resolve(names, src):
    """映射里记的路径在这一版 jar 里叫什么。

    Patchouli 的书搬过家：**1.20.1 起在 `assets/` 下，1.19.4 及更早在 `data/` 下**。
    映射是对着新版提的，所以路径记的是 `assets/…`；套到老版本上必须换成 `data/…`，
    否则一个都对不上——而且是静默对不上，出来一本全英文的书。
    """
    if src in names:
        return src
    for a, b in (('assets/', 'data/'), ('data/', 'assets/')):
        if src.startswith(a):
            alt = b + src[len(a):]
            if alt in names:
                return alt
    return None


def generate(jar_path, res_root):
    """把全部映射套到 jar 上，写进资源根目录。返回落位的文件数。

    输出位置**跟着 jar 走**：jar 里在 `data/` 下，我们也写 `data/`。
    写错地方 Patchouli 根本不去读，同样是静默失效。
    """
    if not BOOKS.is_dir():
        sys.exit('❌ 没有 %s' % BOOKS)
    z = zipfile.ZipFile(jar_path)
    names = set(z.namelist())
    total = ok = n = 0
    miss = []
    for mp in sorted(BOOKS.rglob('*.json')):
        rel = mp.relative_to(BOOKS).as_posix()[:-len('.json')]
        doc = json.loads(mp.read_text(encoding='utf-8'))
        src = resolve(names, doc['src'])
        if src is None:
            continue                        # 这个模组版本没这个文件
        up = z.read(src)
        obj = json.loads(up.decode('utf-8-sig'))
        strict = sha1(up) == doc['sha1']
        total += len(doc['t'])
        ok += apply_one(obj, doc['t'], rel, strict, miss)
        t = Path(res_root) / src.replace('/en_us/', '/zh_cn/')
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n',
                     encoding='utf-8')
        n += 1
    rate = (ok / total) if total else 1.0
    print('导览书：%d 个文件、%d/%d 条译文落位（%.1f%%）' % (n, ok, total, rate * 100))
    if miss:
        print('  ⚠️ %d 条没落位（上游改了那一段）：' % len(miss))
        for r, p, e in miss[:10]:
            print('       %s %s  %r' % (r, list(p), e))
    if rate < MIN_HIT:
        sys.exit('❌ 导览书译文命中率 %.1f%% 低于下限 %.0f%%——'
                 '不是零星漂移，是整块对不上了' % (rate * 100, MIN_HIT * 100))
    return n
