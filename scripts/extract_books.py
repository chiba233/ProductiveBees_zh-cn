#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把某一版 jar 里**我们还没有映射**的导览书页面提出来，能自动填的先填上。

导览书那些页高度重复：标题基本是蜂名（我们的蜂名表里全有），正文来来回回就那么
几个句式。所以先机械套一遍——同一句英文在别处已经译过就直接用，标题按蜂名表查——
剩下的才需要人译。

**只提取可翻译的字段**（`name` / `title` / `text` / `subtitle`）。
`type` / `icon` / `entity` / `category` / `flag` / `anchor` / `item` 这些是标识符，
翻了 Patchouli 就读不出来了。

用法:
    python3 scripts/extract_books.py <jar> [--write]
        不加 --write 只报还缺多少、哪些句子要译；加了才落盘。
"""
import json
import sys
import zipfile
from pathlib import Path

import books
import names as namemod
import templates

ROOT = Path(__file__).resolve().parent.parent
# 只有这几个字段是给人看的；其余全是标识符，动了 Patchouli 就读不出来
TEXT_FIELDS = {'name', 'title', 'text', 'subtitle'}


def translatable(path, value):
    if not isinstance(value, str) or not value.strip():
        return False
    if not path or path[-1] not in TEXT_FIELDS:
        return False
    # 形如 productivebees:xxx / botania:yyy 的是 ID，不是文案
    return ':' not in value.split(' ')[0] or ' ' in value


def known_pairs():
    """已有映射里的「英文 → 中文」，同一句话在别处译过就直接用。

    顺便把**链接里的名字**单独收一份：`$(l:…)Iron Bee$(/l)` 这种，
    模板套用时要拿它把名字换掉。
    """
    out, inner = {}, {}
    for mp in sorted(books.BOOKS.rglob('*.json')):
        doc = json.loads(mp.read_text(encoding='utf-8'))
        for _p, en, zh in doc.get('t', []):
            out.setdefault(en, zh)
            _se, pe = templates.skeleton(en)
            _sz, pz = templates.skeleton(zh)
            if len(pe) == len(pz):
                for (ta, na), (tb, nb) in zip(pe, pz):
                    if ta == tb:
                        inner.setdefault(na, nb)
    return out, inner


def main(jar_path, write=False):
    z = zipfile.ZipFile(jar_path)
    have = {p.relative_to(books.BOOKS).as_posix()[:-len('.json')]
            for p in books.BOOKS.rglob('*.json')}
    pages = [n for n in z.namelist()
             if '/patchouli_books/guide/en_us/' in n and n.endswith('.json')]
    pairs, inner = known_pairs()
    tables, _ = namemod.build(jar_path)
    en2zh = dict(tables['en2zh'])
    name2zh = dict(en2zh)
    name2zh.update(inner)                   # 链接里的名字以已有译文为准
    tmpl = templates.learn()
    hand_sk, terms, link_texts = templates.hand()
    name2zh.update(link_texts)

    todo, made = {}, 0
    for n in pages:
        rel = 'patchouli_books/' + n.split('/patchouli_books/')[1].replace(
            '/en_us/', '/zh_cn/')
        if rel in have:
            continue
        raw = z.read(n)
        obj = json.loads(raw.decode('utf-8-sig'))
        entries, unresolved = [], []
        for path, val in books.walk(obj):
            if not translatable(path, val):
                continue
            zh = (pairs.get(val) or en2zh.get(val)
                  or templates.apply(val, tmpl, name2zh, hand_sk, terms))
            if zh:
                entries.append([list(path), val, zh])
            else:
                unresolved.append(val)
                todo.setdefault(val, []).append(rel)
        if write and not unresolved:
            books.dump(rel, {'src': n, 'sha1': books.sha1(raw), 't': entries})
            made += 1
        print('  %-46s 自动填 %3d / 还缺 %d'
              % (rel.split('guide/zh_cn/')[-1], len(entries), len(unresolved)))

    print('\n还要人译的**不重复**句子 %d 条：' % len(todo))
    for s in sorted(todo, key=lambda x: (-len(todo[x]), x))[:40]:
        print('  ×%-3d %s' % (len(todo[s]), s if len(s) < 110 else s[:107] + '…'))
    if write:
        print('\n已落盘 %d 个（只落盘全部能填的那些）' % made)
    return todo


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], '--write' in sys.argv)
