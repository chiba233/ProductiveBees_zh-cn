#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""生成三张蜂名表，给 mod 里的显示层用。

**唯一真源是 `src/lang/zh_cn.json` 的 `entity.productivebees.*`。**
禁止在别处手写第二份蜂名表——Java 里也一个中文都不许写死，写死就必然漂移。

为什么需要这三张表：基因样本 tooltip 那一行是

    Component.translatable("productivebees.information.attribute.type", value)

`value` 是从物品 data component 里读出来的裸 String，**不过任何 lang 查表**。
资源包碰不到它，只能在 `ItemTooltipEvent` 上按这三张表现场替换。

    id2zh    productivebees:xxx（可带 _bee 后缀）→ 中文
    en2zh    英文整名 → 中文（歧义名在这里就剔掉）
    type2zh  类型行专用：无 Bee 后缀的 TitleCase → 中文

## 歧义为什么必须在生成期剔掉

上游有两只蜂的英文名一模一样（`Amber Bee` 既是琥珀蜜蜂也是琥珀宝石蜜蜂）。
显示层拿英文名反查中文时无法区分，**宁可显示英文也不能张冠李戴**。
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / 'src' / 'lang' / 'zh_cn.json'

PREFIX = 'entity.productivebees.'
# 这个键的值带占位符，是模板不是蜂名
SKIP_BASE = {'bee_configurable'}
# 不是实体、但会被当成基因类型显示出来的，显示名取自物品键
EXTRA = {'bee_bomb': 'item.productivebees.bee_bomb'}


def title_case(base):
    return ' '.join(w.capitalize() for w in base.split('_') if w)


def _base(key):
    bid = key[len(PREFIX):]
    return bid[:-4] if bid.endswith('_bee') else bid


def build(jar_path):
    """-> (三张表, 歧义清单)"""
    zh_pack = json.loads(LANG.read_text(encoding='utf-8'))
    en = {k: v for k, v in json.loads(zipfile.ZipFile(jar_path).read(
        'assets/productivebees/lang/en_us.json')).items() if k.startswith(PREFIX)}

    id2zh = {}
    for key, zh in zh_pack.items():
        if not key.startswith(PREFIX):
            continue
        base = _base(key)
        if base in SKIP_BASE or '%' in zh:
            continue
        id2zh[base] = zh
    for base, item_key in EXTRA.items():
        if item_key in zh_pack:
            id2zh[base] = zh_pack[item_key]

    # 英文名候选：模组自己的 en_us + 由 id 派生的 TitleCase。
    # 按英文串聚合，一个英文串对上两个中文就是歧义。
    cand = {}
    for base, zh in id2zh.items():
        if base == 'bee':
            continue                        # 裸 'Bee' 由 "(Bee)" 整名规则单独处理
        cand.setdefault(title_case(base) + ' Bee', set()).add(zh)
    for key, env in en.items():
        base = _base(key)
        if '%' in env or len(env) < 4 or base not in id2zh:
            continue
        cand.setdefault(env, set()).add(id2zh[base])

    en2zh, ambiguous = {}, []
    for env, zhs in sorted(cand.items()):
        if len(zhs) == 1:
            en2zh[env] = next(iter(zhs))
        else:
            ambiguous.append((env, sorted(zhs)))

    type2zh = {title_case(base): zh for base, zh in id2zh.items() if base != 'bee'}
    return {'id2zh': id2zh, 'en2zh': en2zh, 'type2zh': type2zh}, ambiguous


def write(jar_path, out_file):
    tables, ambiguous = build(jar_path)
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    Path(out_file).write_text(json.dumps(
        tables, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print('蜂名表：ID %d / 英文名 %d / 类型行 %d'
          % (len(tables['id2zh']), len(tables['en2zh']), len(tables['type2zh'])))
    if ambiguous:
        print('  歧义英文名 %d 个（已剔除，宁可显示英文也不张冠李戴）:' % len(ambiguous))
        for env, zhs in ambiguous:
            print('    %r -> %s' % (env, zhs))
    if not tables['type2zh']:
        raise SystemExit('❌ 类型表是空的——那一行正是这个 mod 存在的理由')
    return tables
