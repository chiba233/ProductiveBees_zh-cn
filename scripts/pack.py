#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把上游的译文摊成这个 mod 的资源树，并核验覆盖率。

**由 build.py 在装好 sys.path 之后导入**——它依赖上游仓库 `scripts/` 里的
`paths` / `gen_books` / `gen_pb_hanhua`。这个仓库一行译文都不存，全部现取。

三样东西：

1. `assets/productivebees/lang/zh_cn.json`  —— 直接来自上游资源包
2. `assets/productivebees/patchouli_books/**` —— 拿「原文 → 译文」映射现套到
   模组自带那份 JSON 上（所以构建时非有那个 jar 不可）
3. `pbzh/bees.json` —— 三张蜂名表，给 Java 那层用

第 3 样是关键：`Gene.appendHoverText` 把裸 String 塞进
`Component.translatable("...attribute.type", value)` 的参数位，那个串是运行期数据，
不过任何 lang 查表，资源包碰不到。表**只在上游生成一次**（`gen_pb_hanhua.py`），
这里只是把它抠出来——Java 里一个中文都不许写死，否则又变成两份译名。
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def name_tables(common):
    """从上游生成的显示层脚本里抠出三张表。

    为什么这么取而不是让上游多导一份：这个包不该逼上游为它改代码。
    上游自己的 check.py 做蜂名漂移检查时用的就是同一招。
    """
    js = common / 'kubejs' / 'client_scripts' / 'pb_hanhua_tooltip.js'
    if not js.is_file():
        sys.exit('❌ 上游没生成 pb_hanhua_tooltip.js，抠不出蜂名表')
    text = js.read_text(encoding='utf-8')
    out = {}
    for want, key in (('PB_ID2ZH', 'id2zh'), ('PB_EN2ZH', 'en2zh'),
                      ('PB_TYPE2ZH', 'type2zh')):
        m = re.search(r'const %s = (\{.*?\});\n' % want, text, re.S)
        if not m:
            sys.exit('❌ 上游脚本里找不到 %s' % want)
        out[key] = json.loads(m.group(1))
    if not out['type2zh']:
        sys.exit('❌ 类型表是空的——那一行正是这个 mod 存在的理由')
    return out


def coverage(jar, ns, root, floor):
    """对着 jar 的 en_us 与导览书逐个点名。"""
    z = zipfile.ZipFile(jar)
    bad, rate = {}, {}
    en_path = 'assets/%s/lang/en_us.json' % ns
    if en_path in z.namelist():
        en = json.loads(z.read(en_path))
        f = root / 'assets' / ns / 'lang' / 'zh_cn.json'
        zh = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
        miss = sorted(set(en) - set(zh))
        rate['lang_keys'] = (len(en) - len(miss)) / max(1, len(en))
        if miss:
            bad['lang_keys'] = miss
    books = [n for n in z.namelist()
             if n.startswith('assets/%s/patchouli_books/' % ns)
             and '/en_us/' in n and n.endswith('.json')]
    if books:
        miss = [n for n in books
                if not (root / n.replace('/en_us/', '/zh_cn/')).is_file()]
        rate['book_files'] = (len(books) - len(miss)) / len(books)
        if miss:
            bad['book_files'] = miss
    fails = []
    for k, need in floor.items():
        if k.startswith('_') or rate.get(k) is None:
            continue
        if rate[k] < need:
            fails.append('%s 覆盖率 %.1f%% 低于下限 %.0f%%，缺 %d 项：%s'
                         % (k, rate[k] * 100, need * 100,
                            len(bad.get(k, [])), bad.get(k, [])[:5]))
    return rate, fails


def sanity(jar, ns, root):
    """占位符红线 + 导览书结构，全部对着模组自己的 en_us 比。

    覆盖率只回答「有没有翻」，这里回答「翻得会不会炸」。
    """
    bad = []
    z = zipfile.ZipFile(jar)
    TOK = re.compile(r'%(?:(\d+)\$)?(\d+)?(?:\.(\d+))?([a-zA-Z%])')
    TRAIL = re.compile(r'(?<!%)%$')

    def profile(t):
        prof, seq = {}, 0
        for m in TOK.finditer(t):
            if m.group(4) == '%':
                continue
            if m.group(1):
                idx = int(m.group(1))
            else:
                seq += 1
                idx = seq
            prof.setdefault(idx, m.group(4))
        return prof

    en_path = 'assets/%s/lang/en_us.json' % ns
    if en_path in z.namelist():
        en = json.loads(z.read(en_path))
        zh = json.loads((root / 'assets' / ns / 'lang'
                         / 'zh_cn.json').read_text(encoding='utf-8'))
        for k, v in zh.items():
            if not isinstance(v, str):
                bad.append('lang %s 的值不是字符串' % k)
                continue
            e = en.get(k)
            if e is None:
                continue
            pe, pz = profile(e), profile(v)
            if set(pz) - set(pe):
                bad.append('lang %s 多出占位符 %s（运行时参数不足会抛异常）'
                           % (k, sorted(set(pz) - set(pe))))
            down = [i for i in set(pe) & set(pz) if pe[i] == 's' and pz[i] != 's']
            if down:
                bad.append('lang %s 第 %s 个参数把 %%s 降级了（类型对不上，必炸）'
                           % (k, sorted(down)))
            if TRAIL.search(v) and not TRAIL.search(e):
                bad.append('lang %s 译文以裸 %% 结尾（MC 会当非法格式抛异常）' % k)

    def shape(o):
        if isinstance(o, dict):
            return {k: shape(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [shape(x) for x in o]
        return type(o).__name__

    for n in z.namelist():
        if not (n.startswith('assets/%s/patchouli_books/' % ns)
                and '/en_us/' in n and n.endswith('.json')):
            continue
        t = root / n.replace('/en_us/', '/zh_cn/')
        if not t.is_file():
            continue
        try:
            if shape(json.loads(z.read(n))) != shape(
                    json.loads(t.read_text(encoding='utf-8'))):
                bad.append('导览书 %s 的中文版结构与英文版不一致'
                           '（Patchouli 按结构读，对不上那一页会静默不显示）'
                           % n.rsplit('/', 1)[-1])
        except Exception as e:
            bad.append('导览书 %s 解析失败: %r' % (n, e))
    return bad


def book_name(jar, ns, root):
    """导览书的中文名：上游 book.json 的 name 过一遍我们的 lang。不许手写。"""
    z = zipfile.ZipFile(jar)
    p = 'data/%s/patchouli_books/guide/book.json' % ns
    if p not in z.namelist():
        return None
    en = json.loads(z.read(p)).get('name')
    f = root / 'assets' / ns / 'lang' / 'zh_cn.json'
    if not f.is_file():
        return en
    return json.loads(f.read_text(encoding='utf-8')).get(en, en)


def mods_toml(man, ver):
    return '''modLoader="javafml"
loaderVersion="[1,)"
license="GPL-3.0-or-later"
issueTrackerURL="https://github.com/chiba233/ProductiveBees_zh-cn/issues"

[[mods]]
modId="{modid}_zh_cn"
version="{ver}"
displayName="{zh} 汉化"
authors="星野夢華 (Hoshino Yumeka)"
# 纯客户端显示层，服务端不会有这个 mod。不写这条，进服时可能被判定「mod 不一致」
# 而连不上——汉化把人挡在服务器外面是最不能接受的一类故障。
displayTest="IGNORE_ALL_VERSION"
description=\'\'\'
{zh}（{en}）的简体中文汉化：物品、方块、蜜蜂、界面，内置导览书全部页面，
以及基因样本 tooltip 里那行**运行期拼出来的蜂种名**（那一行资源包碰不到，
只能在 ItemTooltipEvent 上拦）。

摘自 All the Mods 10 汉化补丁「绿油油版」，与整合包版同一份译名真源。
\'\'\'

[[dependencies.{modid}_zh_cn]]
modId="neoforge"
type="required"
versionRange="[21,)"
ordering="NONE"
side="CLIENT"

[[dependencies.{modid}_zh_cn]]
modId="{modid}"
type="required"
versionRange="[0,)"
ordering="AFTER"
side="CLIENT"
'''.format(modid=man['modid'], ver=ver, zh=man['zh_name'], en=man['en_name'])


def build(man, jar, mods_dir, ver, common, pack_dir, gen_books, gen_pb_hanhua):
    """摊出 mod 的资源树，返回 (资源根目录, 统计)。"""
    print('套导览书映射 …')
    gen_books.main(str(mods_dir))
    print('生成蜂名表 …')
    # 上游那个脚本是从 sys.argv 认 jar 的。**不改上游**——它是整合包自己的东西，
    # 不该为这个包让路。这里临时把 argv 顶掉就行。
    saved = sys.argv
    try:
        sys.argv = ['gen_pb_hanhua', str(jar)]
        gen_pb_hanhua.main()
    finally:
        sys.argv = saved

    res = ROOT / 'mod' / 'src' / 'main' / 'resources'
    if res.exists():
        shutil.rmtree(res)
    res.mkdir(parents=True)

    n_lang = n_book = 0
    for ns in man['namespaces']:
        src = pack_dir / 'assets' / ns
        if not src.is_dir():
            sys.exit('❌ 上游出货树里没有 assets/%s' % ns)
        dst = res / 'assets' / ns
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        lf = dst / 'lang' / 'zh_cn.json'
        if lf.is_file():
            n_lang += len(json.loads(lf.read_text(encoding='utf-8')))
        n_book += sum(1 for _ in dst.rglob('patchouli_books/**/*.json'))

    rate, fails = coverage(jar, man['namespaces'][0], res, man['coverage_floor'])
    for k, v in sorted(rate.items()):
        print('  %s 覆盖率 %.1f%%' % (k, v * 100))
    fails += sanity(jar, man['namespaces'][0], res)
    if fails:
        for f in fails:
            print('  ❌', f)
        sys.exit('❌ %d 项没过，不出包——「只翻了一半」或者「翻了会炸」都比没翻还糟'
                 % len(fails))
    print('  占位符 / 导览书结构核验通过')

    tables = name_tables(common)
    (res / 'pbzh').mkdir()
    (res / 'pbzh' / 'bees.json').write_text(
        json.dumps(tables, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
        encoding='utf-8')
    print('  蜂名表: ID %d / 英文名 %d / 类型行 %d'
          % (len(tables['id2zh']), len(tables['en2zh']), len(tables['type2zh'])))

    (res / 'META-INF').mkdir()
    (res / 'META-INF' / 'neoforge.mods.toml').write_text(
        mods_toml(man, ver), encoding='utf-8')
    (res / 'pack.mcmeta').write_text(json.dumps({'pack': {
        'pack_format': man['pack_format'],
        'supported_formats': man['supported_formats'],
        'description': '%s 简体中文汉化 · 绿油油版' % man['zh_name'],
    }}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (res / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())

    return res, {'lang': n_lang, 'book': n_book, 'types': len(tables['type2zh']),
                 'book_name': book_name(jar, man['namespaces'][0], res)}
