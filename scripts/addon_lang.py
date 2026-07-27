#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把整合包自定义的 key（`scripts/addons.py` 扫出来的）译成中文。

整合包用数据包给资源蜜蜂加自己的蜂：`entity.productivebees.tiberium_bee`
这种 key 不在模组本体里，名字由整合包自己给。这些恰恰是各整合包里露英文的地方。

绝大多数能**机械推**出来，因为同一个材料在别处早就译过了：

    entity.productivebees.tiberium_bee     Tiberium Bee   →  泰伯利亚蜜蜂
    item.productivebees.honeycomb_tiberium Tiberium Comb  →  泰伯利亚蜜脾
    block.productivebees.comb_tiberium     ...            →  泰伯利亚蜜脾块

所以只要拿到「材料英文 → 材料中文」，一整族 key 就都出来了。材料中文的来源，
按可信度排：

1. 我们自己的译文里已经有同一个材料（别的 key 用过它）——最可信，直接复用；
2. `src/lang/addon_terms.json` 里手写的那张表——那些是别的模组的专有名词
   （匠魂的钢叶、暮色的铁木、Botania 的盖亚），只能人来定。
   表里还有两栏兜底：`keys` 按整条 key 覆盖（玩梗名拼不出「X蜜蜂」），
   `texts` 按**原文**覆盖（同一句描述常在十几个 key 上重复）。

推不出来的**一条都不硬填**：宁可显示英文，也不能出「泰伯利亚Bee」这种半截货。

用法:
    python3 scripts/addon_lang.py            # 只报能填多少、还缺哪些
    python3 scripts/addon_lang.py --write    # 落进 src/lang/zh_cn.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG = ROOT / 'src' / 'lang' / 'zh_cn.json'
TERMS = ROOT / 'src' / 'lang' / 'addon_terms.json'
VERSIONS = ROOT / 'versions'

# key 的形状 → (取材料名的正则, 中文怎么拼)
SHAPES = [
    (re.compile(r'^entity\.productivebees\.(.+)_bee$'), '%s蜜蜂'),
    (re.compile(r'^item\.productivebees\.spawn_egg_(.+)_bee$'), '%s蜜蜂刷怪蛋'),
    (re.compile(r'^item\.productivebees\.honeycomb_(.+)$'), '%s蜜脾'),
    (re.compile(r'^block\.productivebees\.comb_(.+)$'), '%s蜜脾块'),
    (re.compile(r'^item\.productivebees\.configurable_honeycomb_(.+)$'), '%s蜜脾'),
]
# 反过来：从已有译文里把「材料 → 中文」刨出来
HARVEST = [
    (re.compile(r'^entity\.productivebees\.(.+)_bee$'), re.compile(r'^(.+)蜜蜂$')),
    (re.compile(r'^item\.productivebees\.honeycomb_(.+)$'), re.compile(r'^(.+)蜜脾$')),
    (re.compile(r'^block\.productivebees\.comb_(.+)$'), re.compile(r'^(.+)蜜脾块$')),
]


def load(p, default):
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else default


def known_materials(zh):
    """从已有译文里刨出「材料 id → 材料中文」。"""
    out = {}
    for key, val in zh.items():
        for kp, vp in HARVEST:
            mk, mv = kp.match(key), vp.match(val)
            if mk and mv:
                out.setdefault(mk.group(1), mv.group(1))
    return out


def hand_terms():
    """手写表：`materials` 是「材料 id → 中文」，一条能带出一族 key；
    `keys` 是整条覆盖，给那些拼不出「X蜜蜂」的（Cobbee、InfiniBee 这种玩梗名）。"""
    d = load(TERMS, {})
    return ({k: v for k, v in d.get('materials', {}).items() if not k.startswith('_')},
            {k: v for k, v in d.get('keys', {}).items() if not k.startswith('_')},
            {k: v for k, v in d.get('texts', {}).items() if not k.startswith('_')})


def missing_keys():
    keys = load(VERSIONS / 'addon_keys.json', {})
    base = load(VERSIONS / 'keys.json', {'lang': {}})['lang']
    zh = load(LANG, {})
    return ({k: v for k, v in keys.items() if k not in base and k not in zh},
            zh, keys)


def main(write=False):
    miss, zh, all_keys = missing_keys()
    mats = known_materials(zh)
    hand_mat, hand_key, hand_text = hand_terms()

    made, left = {}, {}
    for key, info in sorted(miss.items()):
        en = info['en'] if isinstance(info, dict) else info
        # 先按整条 key，再按**原文**：同一句话在十几个 key 上重复是常事
        # （「想要这种蜜蜂，去查它刷怪蛋的合成配方」在 ATM 系整合包里出现 14 次），
        # 按原文记一条就全覆盖，以后再冒出来也自动命中。
        done = hand_key.get(key) or hand_text.get(en)
        for pat, fmt in ([] if done else SHAPES):
            m = pat.match(key)
            if not m:
                continue
            mat = m.group(1)
            cn = hand_mat.get(mat) or mats.get(mat)
            if cn:
                done = fmt % cn
            break
        if done:
            made[key] = done
        else:
            left[key] = en

    print('整合包自定义 key：见到 %d 个，我们缺 %d 个' % (len(all_keys), len(miss)))
    print('机械推出来 %d 条，剩 %d 条要人定（多半是别的模组的专有名词）'
          % (len(made), len(left)))
    if left:
        print('\n还缺的（按整合包出现次数排）：')
        rank = sorted(left, key=lambda k: -(miss[k].get('n', 1)
                                            if isinstance(miss[k], dict) else 1))
        for k in rank[:40]:
            print('   %-54s %s' % (k[:54], left[k][:40]))
    if write and made:
        zh.update(made)
        LANG.write_text(json.dumps(dict(sorted(zh.items())), ensure_ascii=False,
                                   indent=2) + '\n', encoding='utf-8')
        print('\n已写入 %d 条，src/lang/zh_cn.json 现有 %d 条' % (len(made), len(zh)))
    return left


if __name__ == '__main__':
    rest = main('--write' in sys.argv)
    # CI 用：扫出来的整合包 key 一条都不许没译。没这道闸，下次扫到新包就是
    # 悄悄多一批英文——扫描器越勤快，漏得越多。
    if '--check' in sys.argv and rest:
        sys.exit('❌ 还有 %d 条整合包 key 没译；'
                 '在 src/lang/addon_terms.json 里补，再跑 --write' % len(rest))
