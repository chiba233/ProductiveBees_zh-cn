#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""按真实数据重写 README 里的支持矩阵。

矩阵有二十来行、每行的条数还会随译文补齐而变，手写必然过时。
数据来自 versions/targets.json 与 versions/keys.json（scan 的产物）。

用法:
    python3 scripts/readme.py            # 重写 README 里两个标记之间的部分
    python3 scripts/readme.py --check    # 只检查是否需要重写（CI 用）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN = '<!-- 支持矩阵开始 · 由 scripts/readme.py 生成，勿手改 -->'
END = '<!-- 支持矩阵结束 -->'


def mcver(v):
    return [int(x) for x in v.split('.')]


def table():
    t = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
    k = json.loads((ROOT / 'versions' / 'keys.json').read_text(encoding='utf-8'))['lang']
    zh = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))

    rows = []
    for tag in sorted(t, key=lambda x: (mcver(t[x]['minecraft']), t[x]['loader']),
                      reverse=True):
        v = t[tag]
        need = [key for key, tags in k.items() if tag in tags]
        have = [key for key in need if key in zh]
        pct = 100 * len(have) / max(1, len(need))
        if not v.get('buildable'):
            state = '暂无（构建工具链够不着 1.16 及更早）'
        elif pct >= 99.95:
            state = '✅ 可用'
        else:
            state = '⏳ 差 %d 条' % (len(need) - len(have))
        rows.append('| %s | %s | %d / %d（%.1f%%） | %d | %s |'
                    % (v['minecraft'], v['loader'], len(have), len(need), pct,
                       v['book_files'], state))

    out = [BEGIN,
           '',
           '| Minecraft | 加载器 | 已汉化条目 | 导览书页数 | 状态 |',
           '|---|---|---|---|---|']
    out += rows
    out += ['', END]
    return '\n'.join(out)


def main(check=False):
    p = ROOT / 'README.md'
    s = p.read_text(encoding='utf-8')
    i, j = s.index(BEGIN), s.index(END) + len(END)
    new = s[:i] + table() + s[j:]
    if check:
        if new != s:
            sys.exit('❌ README 的支持矩阵与 versions/ 里的数据对不上，'
                     '跑 python3 scripts/readme.py 重写')
        print('✅ README 支持矩阵与数据一致')
        return
    p.write_text(new, encoding='utf-8')
    print('README 支持矩阵已按 versions/ 重写')


if __name__ == '__main__':
    main('--check' in sys.argv)
