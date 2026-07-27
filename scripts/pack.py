#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 `src/` 里的译文摊成 mod 的资源树，并在出包前逐项点名。

摊出来的东西（全都是**生成物**，不入库）：

    assets/productivebees/lang/zh_cn.json        直接来自 src/lang
    assets/productivebees/patchouli_books/**     拿映射现套到模组自带那份 JSON 上
    pbzh/bees.json                               三张蜂名表，给显示层用
    META-INF/neoforge.mods.toml, pack.mcmeta     按 manifest 现填

三道闸，过不了不出包：覆盖率、占位符与结构、以及构建收尾对着**打好的 jar** 跑的自测。
「装上去只翻了一半」比没翻还糟——玩家不会来报，只会觉得这包很烂。
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import books
import names

ROOT = Path(__file__).resolve().parent.parent
NS = 'productivebees'


def apply_variants(lang, jar):
    """同一个 key 在不同版本的英文不一样时，按**那一版的原文**取译文。

    `nest_locator.not_found_hive` 就是例子：1.16.3/1.16.4 的原文没有参数，
    而现在的原文有。把带 `%s` 的译文硬套上去，游戏里就是
    TranslatableFormatException——不是少翻一句，是点一下就崩。
    """
    p = ROOT / 'src' / 'lang' / 'variants.json'
    if not p.is_file():
        return lang, 0
    var = {k: v for k, v in json.loads(p.read_text(encoding='utf-8')).items()
           if not k.startswith('_')}
    z = zipfile.ZipFile(jar)
    name = 'assets/%s/lang/en_us.json' % NS
    if name not in z.namelist():
        return lang, 0
    en = json.loads(z.read(name))
    out, n = dict(lang), 0
    for k, per_en in var.items():
        if k in en and en[k] in per_en:
            out[k] = per_en[en[k]]
            n += 1
    return out, n


def coverage(jar, root, floor):
    """对着 jar 的 en_us 与导览书逐个点名。"""
    z = zipfile.ZipFile(jar)
    bad, rate = {}, {}
    en_path = 'assets/%s/lang/en_us.json' % NS
    if en_path in z.namelist():
        en = json.loads(z.read(en_path))
        f = root / 'assets' / NS / 'lang' / 'zh_cn.json'
        zh = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
        miss = sorted(set(en) - set(zh))
        rate['lang_keys'] = (len(en) - len(miss)) / max(1, len(en))
        if miss:
            bad['lang_keys'] = miss
    bk = [n for n in z.namelist()
          if n.startswith(('assets/%s/patchouli_books/' % NS, 'data/%s/patchouli_books/' % NS))
          and '/en_us/' in n and n.endswith('.json')]
    if bk:
        miss = [n for n in bk if not (root / n.replace('/en_us/', '/zh_cn/')).is_file()]
        rate['book_files'] = (len(bk) - len(miss)) / len(bk)
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


def sanity(jar, root):
    """占位符红线 + 导览书结构，全部对着模组自己的 en_us 比。

    覆盖率只回答「有没有翻」，这里回答「翻得会不会炸」：

    - 译文的占位符集合必须 ⊆ 英文的。多出来 = 运行时参数不足 →
      TranslatableFormatException。少是译者的合法选择（有的参数其实只是个空格）。
    - 同序号的转换符不许从 `%s` 降级成 `%d`/`%f`，类型对不上两条渲染路径都炸。
    - 结尾裸 `%` 会被 MC 的 FORMAT_PATTERN 匹配到字符串结尾并抛异常。
    - 导览书中文版的 JSON 结构必须与英文版逐键一致：Patchouli 按结构读，
      少一个 `type` 或页数对不上，那一页**静默不显示**，还不报错。
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

    en_path = 'assets/%s/lang/en_us.json' % NS
    if en_path in z.namelist():
        en = json.loads(z.read(en_path))
        zh = json.loads((root / 'assets' / NS / 'lang'
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
        if not (n.startswith(('assets/%s/patchouli_books/' % NS,
                              'data/%s/patchouli_books/' % NS))
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


def book_name(jar, root):
    """导览书的中文名：上游 book.json 的 name 过一遍我们的 lang。不许手写。"""
    z = zipfile.ZipFile(jar)
    p = 'data/%s/patchouli_books/guide/book.json' % NS
    if p not in z.namelist():
        return None
    en = json.loads(z.read(p)).get('name')
    f = root / 'assets' / NS / 'lang' / 'zh_cn.json'
    if not f.is_file():
        return en
    return json.loads(f.read_text(encoding='utf-8')).get(en, en)


# 资源包格式号按 MC 版本走。一个 jar 跨不了多版本，所以每个目标各填各的。
PACK_FORMAT = [((1, 21), 34), ((1, 20, 5), 32), ((1, 20, 3), 22), ((1, 20, 2), 18),
               ((1, 20), 15), ((1, 19, 4), 13), ((1, 19, 3), 12), ((1, 19), 9),
               ((1, 18), 8), ((1, 17), 7), ((1, 16, 2), 6), ((1, 15), 5)]


def pack_format(mc):
    v = tuple(int(x) for x in mc.split('.'))
    for need, fmt in PACK_FORMAT:
        if v >= need:
            return fmt
    return 5


def mods_toml(man, ver, t):
    """加载器元数据。1.20.2 起 NeoForge 换了文件名与依赖 modId，别搞混。"""
    v = tuple(int(x) for x in t['minecraft'].split('.'))
    neo = t['loader'] == 'NeoForge' and v >= (1, 20, 2)
    # `displayTest` 是后来才有的字段：1.16 及更早的 Forge 不认这个 key，
    # 那个年代要靠代码注册 ExtensionPoint.DISPLAYTEST（见 LegacyEntry）。
    dt = ('# 纯客户端显示层，服务端不会有这个 mod。不写这条，进服时可能被判定\n'
          '# 「mod 不一致」而连不上——汉化把人挡在服务器外面是最不能接受的一类故障。\n'
          'displayTest="IGNORE_ALL_VERSION"\n') if v >= (1, 17) else ''
    return '''modLoader="javafml"
loaderVersion="[1,)"
license="Custom: 译文 (C) 星野夢華; Productive Bees (C) JDKDigital, All Rights Reserved"
issueTrackerURL="https://github.com/chiba233/ProductiveBees_zh-cn/issues"

[[mods]]
modId="{modid}_zh_cn"
version="{ver}"
displayName="{zh} 汉化"
authors="星野夢華 (Hoshino Yumeka)"
{dt}description=\'\'\'
{zh}（{en}）的简体中文汉化：物品、方块、蜜蜂、界面，内置导览书全部页面，
以及基因样本 tooltip 里那行**运行期拼出来的蜂种名**（那一行资源包碰不到，
只能在 ItemTooltipEvent 上拦）。
\'\'\'

[[dependencies.{modid}_zh_cn]]
modId="{loader}"
type="required"
versionRange="[0,)"
ordering="NONE"
side="CLIENT"

[[dependencies.{modid}_zh_cn]]
modId="{modid}"
type="required"
versionRange="[0,)"
ordering="AFTER"
side="CLIENT"
'''.format(modid=man['modid'], ver=ver, zh=man['zh_name'], en=man['en_name'],
           loader='neoforge' if neo else 'forge', dt=dt), neo


def build(man, jar, ver, t):
    """摊出 mod 的资源树，返回 (资源根目录, 统计)。"""
    res = ROOT / 'mod' / 'src' / 'main' / 'resources'
    if res.exists():
        shutil.rmtree(res)
    res.mkdir(parents=True)

    lang = json.loads((ROOT / 'src' / 'lang' / 'zh_cn.json').read_text(encoding='utf-8'))
    lang, n_var = apply_variants(lang, jar)
    lang_dst = res / 'assets' / NS / 'lang' / 'zh_cn.json'
    lang_dst.parent.mkdir(parents=True, exist_ok=True)
    lang_dst.write_text(json.dumps(lang, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')
    n_lang = len(lang)
    if n_var:
        print('  这一版有 %d 条原文和最新版不同，改用对应的译文' % n_var)

    n_book = books.generate(jar, res)
    tables = names.write(jar, res / 'pbzh' / 'bees.json')

    rate, fails = coverage(jar, res, man['coverage_floor'])
    for k, v in sorted(rate.items()):
        print('  %s 覆盖率 %.1f%%' % (k, v * 100))
    fails += sanity(jar, res)
    if fails:
        for f in fails:
            print('  ❌', f)
        sys.exit('❌ %d 项没过，不出包——「只翻了一半」或者「翻了会炸」都比没翻还糟'
                 % len(fails))
    print('  占位符 / 导览书结构核验通过')

    toml, neo = mods_toml(man, ver, t)
    (res / 'META-INF').mkdir()
    (res / 'META-INF' / ('neoforge.mods.toml' if neo else 'mods.toml')).write_text(
        toml, encoding='utf-8')
    fmt = pack_format(t['minecraft'])
    (res / 'pack.mcmeta').write_text(json.dumps({'pack': {
        'pack_format': fmt,
        'description': '%s 简体中文汉化' % man['zh_name'],
    }}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # 两份都进 jar：LICENSE 讲清楚三类东西各归各的，GPL 正文给代码那部分
    (res / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())
    (res / 'LICENSE-GPL-3.0').write_bytes((ROOT / 'LICENSE-GPL-3.0').read_bytes())

    return res, {'lang': n_lang, 'book': n_book,
                 'types': len(tables['type2zh']), 'book_name': book_name(jar, res)}
