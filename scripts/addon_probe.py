#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""给 `TestAddonNames` 造夹具：一份「玩家实际会有的语言表」+ 一份真值。

要验的是 `AddonNames` 那条路——整合包自己加的蜂，能不能从**玩家已经装的模组**
里把材料名现学出来。所以夹具不能是我编的，得来自真模组：

    lang    拿一堆真 mod jar 的 `zh_cn.json`（没有中文的退回 `en_us.json`）
            并成一张表，这正是游戏里 `Language.getInstance()` 手上那份。
    expect  从这些模组的材料里挑出**能独立判定中文**的那些，合成
            `entity.productivebees.<材料>_bee` 这类键（值给英文，模拟没译），
            真值由该材料自己的官方中文推出，不经过 AddonNames。

真值的取法与被测代码**互不相干**：这里按「材料 id 对应的锭/块条目的中文，去掉
锭/块字样」取，被测那边走的是多数派公共前缀。两条路都算得出同一个词才算对上。

用法:
    python3 scripts/addon_probe.py <mods 目录> <输出.json>
"""
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

CJK = re.compile(r'[一-鿿]')
LATIN = re.compile(r'[A-Za-z]')
# 材料常见的成品后缀：中文这边去掉它就是材料名
# 真值只认「锭」这一种形态：被测那边走的是多形态投票，两边的依据不一样，
# 对得上才说明不是同一段逻辑自证
SUFFIX = [('_ingot', '锭')]


def merged_lang(mods):
    """模拟游戏里的语言表：有中文用中文，没有就是英文。"""
    en, zh = {}, {}
    for j in sorted(Path(mods).glob('*.jar')):
        try:
            z = zipfile.ZipFile(j)
        except Exception:                                  # noqa: BLE001
            continue
        for n in z.namelist():
            if not (n.startswith('assets/') and '/lang/' in n):
                continue
            tgt = en if n.endswith('/en_us.json') else (
                zh if n.endswith('/zh_cn.json') else None)
            if tgt is None:
                continue
            try:
                d = json.loads(z.read(n).decode('utf-8-sig'))
            except Exception:                              # noqa: BLE001
                continue
            for k, v in d.items():
                if isinstance(v, str):
                    tgt[k] = v
    lang = dict(en)
    lang.update(zh)
    return lang, en, zh


def truth(en, zh):
    """材料 id → 中文。只收**两条以上成品都指向同一个词**的，其余不作数。"""
    votes, n = defaultdict(set), defaultdict(int)
    for k, v in zh.items():
        if not CJK.search(v) or LATIN.search(v):
            continue
        tail = k.rsplit('.', 1)[-1]
        for suf, cn in SUFFIX:
            if tail.endswith(suf) and v.endswith(cn):
                mat, word = tail[:-len(suf)], v[:-len(cn)]
                if len(mat) >= 4 and word:
                    votes[mat].add(word)
                    n[mat] += 1
                break
    # 两条以上成品、且它们指向同一个词，才算这个材料的中文是确定的
    return {m: next(iter(s)) for m, s in votes.items() if len(s) == 1 and n[m] >= 1}


def main(mods, out):
    lang, en, zh = merged_lang(mods)
    print('并出的语言表 %d 条（其中中文 %d 条，来自 %s）'
          % (len(lang), sum(1 for v in lang.values() if CJK.search(v)), mods))
    mats = truth(en, zh)
    print('能独立判定中文的材料 %d 个' % len(mats))

    shapes = [('entity.productivebees.%s_bee', '%s Bee', '%s蜜蜂'),
              ('item.productivebees.honeycomb_%s', '%s Comb', '%s蜜脾'),
              ('block.productivebees.comb_%s', '%s Comb Block', '%s蜜脾块')]
    expect = {}
    for mat, cn in sorted(mats.items()):
        title = ' '.join(w.capitalize() for w in mat.split('_'))
        for kf, ef, zf in shapes:
            key = kf % mat
            if key in lang:
                continue                      # 模组本体已有的不算「整合包自定义」
            lang[key] = ef % title            # 模拟：整合包只给了英文
            expect[key] = zf % cn
    print('合成的「没见过的整合包蜂键」%d 条' % len(expect))
    Path(out).write_text(json.dumps({'lang': lang, 'expect': expect},
                                    ensure_ascii=False), encoding='utf-8')
    print('夹具写到 %s' % out)
    return len(expect)


# 合成夹具：不依赖任何本机模组，CI 里每次构建都跑。正反两面都要覆盖——
# 学得出的要学对，拿不准的必须**学不出**（学错比学不出严重得多）。
SELFTEST = {
    'lang': {
        # 两种基础形态，票一致 → 该学出「泰伯利亚」
        'item.tib.tiberium_ingot': '泰伯利亚锭',
        'block.tib.tiberium_block': '泰伯利亚块',
        'entity.productivebees.tiberium_bee': 'Tiberium Bee',
        'item.productivebees.honeycomb_tiberium': 'Tiberium Comb',
        # 两个模组对同一个 id 两种译法 → 票分裂，必须学不出
        'item.tf.ironwood_ingot': '铁木锭',
        'block.other.ironwood_block': '铁色木块',
        'entity.productivebees.ironwood_bee': 'Ironwood Bee',
        # 只有一种形态 → 样本不足，学不出
        'item.solo.amaramber_ingot': '绯夜脂锭',
        'entity.productivebees.amaramber_bee': 'Amaramber Bee',
        # 非基础形态（工具/血液）不许当样本 → 学不出
        'item.tf.fiery_sword': '炽焰剑',
        'item.tf.fiery_blood': '炽热的血液',
        'entity.productivebees.fiery_bee': 'Fiery Bee',
        # 已经是中文的键不许再动
        'entity.productivebees.iron_bee': '铁蜜蜂',
        'item.mc.iron_ingot': '铁锭',
        'block.mc.iron_block': '铁块',
    },
    'expect': {
        'entity.productivebees.tiberium_bee': '泰伯利亚蜜蜂',
        'item.productivebees.honeycomb_tiberium': '泰伯利亚蜜脾',
    },
    'forbid': ['entity.productivebees.ironwood_bee', 'entity.productivebees.amaramber_bee',
               'entity.productivebees.fiery_bee', 'entity.productivebees.iron_bee'],
}


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--selftest':
        Path(sys.argv[2]).write_text(json.dumps(SELFTEST, ensure_ascii=False),
                                     encoding='utf-8')
        print('合成夹具写到 %s' % sys.argv[2])
        sys.exit(0)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
