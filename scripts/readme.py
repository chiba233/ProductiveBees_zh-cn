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
CBEGIN = '<!-- 覆盖范围开始 · 由 scripts/readme.py 生成，勿手改 -->'
CEND = '<!-- 覆盖范围结束 -->'
TOP = 25


def mcver(v):
    return [int(x) for x in v.split('.')]


def table():
    t = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
    k = json.loads((ROOT / 'versions' / 'keys.json').read_text(encoding='utf-8'))['lang']
    zh = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))

    base = ROOT / 'src' / 'books' / 'patchouli_books' / 'guide' / 'zh_cn'
    books = {p.relative_to(base).as_posix().replace('.json.json', '')
             for p in base.rglob('*.json')}
    kb = json.loads((ROOT / 'versions' / 'keys.json').read_text(encoding='utf-8'))['books']
    rows = []
    for tag in sorted(t, key=lambda x: (mcver(t[x]['minecraft']), t[x]['loader']),
                      reverse=True):
        v = t[tag]
        need = [key for key, tags in k.items() if tag in tags]
        have = [key for key in need if key in zh]
        nb = [b for b, tags in kb.items() if tag in tags]
        hb = [b for b in nb if b in books]
        if v.get('buildable'):
            state = '✅ 可用'
        else:
            miss = []
            if len(have) < len(need):
                miss.append('%d 条词条' % (len(need) - len(have)))
            if len(hb) < len(nb):
                miss.append('%d 页导览书' % (len(nb) - len(hb)))
            state = '⏳ 待补 ' + '、'.join(miss) if miss else '⏳ 待接构建'
        rows.append('| %s | %s | %d / %d | %d / %d | %s |'
                    % (v['minecraft'], v['loader'], len(have), len(need),
                       len(hb), len(nb), state))

    out = [BEGIN,
           '',
           '| Minecraft | 加载器 | 词条 | 导览书 | 状态 |',
           '|---|---|---|---|---|']
    out += rows
    out += ['', END]
    return '\n'.join(out)


def coverage():
    """覆盖了哪些整合包。数据来自 scripts/addons.py 的扫描摘要。

    整合包会用数据包给资源蜜蜂加自己的蜂，名字由整合包自己给——这些 key 不在
    模组本体里。下面这张表就是「扫到谁自定义了蜂名、有多少条」。
    """
    p = ROOT / 'versions' / 'addon_scan.json'
    if not p.is_file():
        return CBEGIN + '\n' + CEND
    d = json.loads(p.read_text(encoding='utf-8'))
    packs = d['packs']
    plat = d.get('platforms') or {}
    # 两个平台的量级差很多，分开说：CurseForge 有反向依赖接口，能直接问「谁用了
    # 资源蜜蜂」；Modrinth 没有，只能把整合包全列一遍逐个翻。
    where = '、'.join(
        '%s %d 个' % ({'curseforge': 'CurseForge', 'modrinth': 'Modrinth 整合包',
                       'modrinth-mod': 'Modrinth 模组'}.get(k, k), v)
        for k, v in sorted(plat.items())) or 'CurseForge %d 个' % d['scanned']
    out = [CBEGIN, '',
           '已逐个翻过 **%d** 个整合包与模组（%s；%d 个取不到文件）。'
           '其中 **%d** 个自带蜂名——它们用数据包加了自己的蜂，名字不在模组本体里。'
           '这些名字**也在本汉化里**：'
           % (d['scanned'], where, d['failed'], len(packs)),
           '',
           '| 整合包 | 自定义条目 | 下载量 |',
           '|---|---:|---:|']
    for x in packs[:TOP]:
        # 整合包名字里真的有竖线（TechEv || Discovery），不转义会把表格撑散
        out.append('| %s | %d | %s |'
                   % (x['name'].replace('|', r'\|'), x['keys'],
                      '{:,}'.format(x['downloads'])))
    if len(packs) > TOP:
        out.append('| …另有 %d 个 | | |' % (len(packs) - TOP))
    out += ['', '未列出的整合包同样适用：本汉化覆盖模组本体的全部词条，'
            '整合包自定义的蜂名是额外补充的一层。', '', CEND]
    return '\n'.join(out)


def main(check=False):
    p = ROOT / 'README.md'
    s = p.read_text(encoding='utf-8')
    i, j = s.index(BEGIN), s.index(END) + len(END)
    new = s[:i] + table() + s[j:]
    if CBEGIN in new:
        a, b = new.index(CBEGIN), new.index(CEND) + len(CEND)
        new = new[:a] + coverage() + new[b:]
    if check:
        if new != s:
            sys.exit('❌ README 的生成段落与 versions/ 里的数据对不上，'
                     '跑 python3 scripts/readme.py 重写')
        print('✅ README 的支持矩阵与覆盖范围都与数据一致')
        return
    p.write_text(new, encoding='utf-8')
    print('README 的支持矩阵与覆盖范围已按 versions/ 重写')


if __name__ == '__main__':
    main('--check' in sys.argv)
