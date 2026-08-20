#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""四套加载器胶水必须挂齐同样的钩子——少一个就红。

这个 mod 出 20 个平台，加载器胶水按事件类的包名分了四套源目录。**只在眼前那一套
里加功能是最容易犯、也最难自己发现的错**：编译过、CI 绿、自测过，只有另外那十几个
平台的玩家看不到新功能，而没有任何一处会报警。名牌汉化就这么只写在 neoforge 里过了
一轮。

所以把「哪套源码集该有哪些能力」写成表，对不上就失败。**故意只做某几版的，必须在
这里写明理由**——不写理由等于没想过。

用法:
    python3 scripts/hooks.py --check
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETS = {
    'neoforge': '1.21 / 1.21.1',
    'forge': '1.19 – 1.20.1（含 1.20.x 的 NeoForge）',
    'forge_old': '1.17 – 1.18.2',
    'forge_legacy': '1.15.2 – 1.16.5',
}
# 能力名 → 在源码里怎么认出来
MARKS = {
    'tooltip': re.compile(r'onItemTooltip'),
    'nametag': re.compile(r'onRenderName(Tag|plate)'),
    'addon_learn': re.compile(r'AddonNames\.refresh'),
    'cage_server': re.compile(r'ServerNames::onPlayerTick'),
}
# 谁该有什么。**故意的缺口写在 ONLY 里，必须带理由。**
ALL = {'tooltip', 'nametag', 'addon_learn'}
ONLY = {
    'cage_server': (
        {'neoforge'},
        '蜂笼要改的是物品的 DataComponents/CustomData，那套 API 只有 1.21 起是这个'
        '形状；老版本是另一套 NBT，没适配。',
    ),
}


def caps(name):
    src = ROOT / 'mod' / 'src' / name / 'java'
    text = '\n'.join(p.read_text(encoding='utf-8') for p in src.rglob('*.java'))
    return {c for c, pat in MARKS.items() if pat.search(text)}


def main():
    got = {s: caps(s) for s in SETS}
    bad = []
    for s in SETS:
        want = set(ALL)
        for cap, (only, _why) in ONLY.items():
            if s in only:
                want.add(cap)
        miss = sorted(want - got[s])
        extra = sorted(got[s] - want)
        if miss:
            bad.append('%s（%s）少了：%s' % (s, SETS[s], '、'.join(miss)))
        if extra:
            bad.append('%s（%s）多了：%s——要么给其余几套也补上，'
                       '要么在 scripts/hooks.py 的 ONLY 里写明为什么只有它有'
                       % (s, SETS[s], '、'.join(extra)))
    print('四套加载器胶水的能力矩阵：')
    for s in SETS:
        print('  %-14s %-34s %s' % (s, SETS[s], '、'.join(sorted(got[s])) or '（空）'))
    for cap, (only, why) in ONLY.items():
        print('  ℹ️ %s 只有 %s 有：%s' % (cap, '、'.join(sorted(only)), why))
    if bad:
        print()
        for b in bad:
            print('❌ ' + b)
        sys.exit(1)
    print('✅ 四套挂齐了')


if __name__ == '__main__':
    main()
