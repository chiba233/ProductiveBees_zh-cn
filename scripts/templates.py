#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""从**已有译文**里学出句式模板，套到还没译的同款句子上。

导览书的正文来来回回就那么几个句式，只有中间那几个蜂名不同：

    Bred from a $(l:bees/hive/iron)Iron Bee$(/l) and a $(l:bees/wild/ender)Ender Bee$(/l).
    由一只$(l:bees/hive/iron)铁蜜蜂$(/l)和一只$(l:bees/wild/ender)末影蜜蜂$(/l)繁殖而来。

把链接段挖掉就剩骨架：`Bred from a {0} and a {1}.` ↔ `由一只{0}和一只{1}繁殖而来。`
骨架是**从已经译好的条目里算出来的**，不是我另写一份——另写一份就会和正文的
语气、用词慢慢分家。

`a`/`an` 归一：英文按下一个词的首字母变，中文不关心，不归一会白白多出一倍骨架。
"""
import json
import re
from collections import Counter
from pathlib import Path

import books

ROOT = Path(__file__).resolve().parent.parent
HAND = ROOT / 'src' / 'book_templates.json'
LINK = re.compile(r'\$\(l:([^)]*)\)(.*?)\$\(/l\)', re.S)


def skeleton(s):
    """-> (骨架, [(链接目标, 文字), …])"""
    parts = []

    def sub(m):
        parts.append((m.group(1), m.group(2)))
        return '{%d}' % (len(parts) - 1)

    sk = LINK.sub(sub, s)
    # 冠词归一：中文这边没有对应物，不归一等于把同一个句式拆成两个
    sk = re.sub(r'\b[Aa]n\b', 'a', sk)
    return sk, parts


def hand():
    """手写的骨架表与术语表（src/book_templates.json）。"""
    if not HAND.is_file():
        return {}, {}
    d = json.loads(HAND.read_text(encoding='utf-8'))
    sk = {k: v for k, v in d.get('skeletons', {}).items() if not k.startswith('_')}
    tm = {k: v for k, v in d.get('terms', {}).items() if not k.startswith('_')}
    lt = {k: v for k, v in d.get('link_texts', {}).items() if not k.startswith('_')}
    return sk, tm, lt


def apply_hand(sk_en, skeletons, terms):
    """带 %term% 槽的骨架匹配。

    宝石蜂那五十来条用的是同一句话，只有宝石名不同；把术语做成槽，
    一条骨架 + 一张术语表就够了，不必一句句手译。
    """
    for pat, out in skeletons.items():
        if '%term%' not in pat:
            if pat == sk_en:
                return out
            continue
        a, _, b = pat.partition('%term%')
        if not (sk_en.startswith(a) and sk_en.endswith(b)):
            continue
        word = sk_en[len(a):len(sk_en) - len(b)] if b else sk_en[len(a):]
        zh = terms.get(word)
        if zh is not None:
            return out.replace('%term%', zh)
    return None


def learn():
    """从已有映射里学出「英文骨架 → 中文骨架」。

    同一个英文骨架对上两种中文骨架时**丢弃**：说明那个句式还有别的变化因素，
    硬套会出错。宁可留给人译。
    """
    cand = {}
    for mp in sorted(books.BOOKS.rglob('*.json')):
        doc = json.loads(mp.read_text(encoding='utf-8'))
        for _p, en, zh in doc.get('t', []):
            se, pe = skeleton(en)
            sz, pz = skeleton(zh)
            if not pe or len(pe) != len(pz):
                continue
            if [a for a, _ in pe] != [a for a, _ in pz]:
                continue                     # 链接目标对不上，不是同一句
            cand.setdefault(se, Counter())[sz] += 1
    out = {}
    for se, c in cand.items():
        if len(c) == 1:
            out[se] = next(iter(c))
    return out


def apply(en, tmpl, name2zh, hand_sk=None, terms=None):
    """按模板译一句。任何一个蜂名查不到就整句放弃——半截中文比全英文更糟。"""
    se, parts = skeleton(en)
    sz = tmpl.get(se)
    if sz is None and hand_sk:
        sz = apply_hand(se, hand_sk, terms or {})
    if sz is None:
        return None
    if not parts:
        return sz if '{' not in sz else None
    filled = []
    for target, text in parts:
        zh = name2zh.get(text)
        if zh is None:
            return None
        filled.append('$(l:%s)%s$(/l)' % (target, zh))
    try:
        return sz.format(*filled)
    except (IndexError, KeyError):
        return None


def stats():
    t = learn()
    print('从已有译文学到 %d 个句式骨架：' % len(t))
    for se in sorted(t, key=len)[:12]:
        print('   EN %s' % se[:100])
        print('   ZH %s' % t[se][:100])
    return t


if __name__ == '__main__':
    stats()
