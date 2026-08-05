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
import io
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


def bundled_langs(jar):
    """这一版 jar 里**所有**语言表：本体的，加上它内嵌的那些 jar 里的。

    资源蜜蜂 1.21.1 起把升级组件搬进了 `productivelib`，而那个 mod 是
    **打包在自己 jar 里**发的（`META-INF/jarjar/productivelib-….jar`）。
    只认 `assets/productivebees/` 的话，那 18 个升级组件在游戏里全是英文，
    而且我们这边一点异常都看不到——键表里根本没有它们，覆盖率照样 100%。

    返回 `{命名空间: {key: 英文原文}}`。
    """
    out = {}
    z = zipfile.ZipFile(jar)

    def take(zf, prefix=''):
        for n in zf.namelist():
            m = re.match(r'^assets/([^/]+)/lang/en_us\.json$', n)
            if not m:
                continue
            try:
                d = json.loads(zf.read(n).decode('utf-8-sig'))
            except Exception:                          # noqa: BLE001
                continue
            if isinstance(d, dict):
                out.setdefault(m.group(1), {}).update(
                    {k: v for k, v in d.items() if isinstance(v, str)})
        for n in zf.namelist():
            if not prefix and n.startswith('META-INF/jarjar/') and n.endswith('.jar'):
                try:
                    with zipfile.ZipFile(io.BytesIO(zf.read(n))) as inner:
                        take(inner, n)
                except Exception:                      # noqa: BLE001
                    continue

    take(z)
    return out


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
    # 覆盖率要把**内嵌 jar 的命名空间**一起算进来：漏掉它的话，升级组件整批
    # 显示英文而这里照样报 100%——1.21.1 就这么漏了 18 个物品名。
    en, zh = {}, {}
    for ns, sub in sorted(bundled_langs(jar).items()):
        en.update(sub)
        f = root / 'assets' / ns / 'lang' / 'zh_cn.json'
        if f.is_file():
            zh.update(json.loads(f.read_text(encoding='utf-8')))
    if en:
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
    # 英文原文除了占位符和标点一个字母都没有 → 这一条的内容整个来自运行期传进来
    # 的那个参数，我们**不能往上加字**。加了就直接贴在人家后面：
    # `entity.productivebees.bee_configurable` 英文就是裸的 `%s`，被译成
    # `%s蜜蜂` 之后，1.15.2–1.16.4 里显示成「绿宝石蜜蜂蜜蜂」「Lapis Bee蜜蜂」。
    BARE = re.compile(r'^(?:%(?:\d+\$)?[a-zA-Z%]|[\s:：/,，.。\-—]|\\n)*$')
    CJK = re.compile(r'[一-鿿]')

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
            if BARE.match(e) and CJK.search(v):
                bad.append('lang %s 的英文原文只有占位符（%r），译文却加了字（%r）'
                           '——那几个字会直接贴在运行期传进来的内容后面' % (k, e, v))
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


BEE_DATA = 'data/%s/%s/' % (NS, NS)


def bee_data_names(jar, res, tables):
    """给数据包定义的蜂补一个中文 `name` 字段。

    这些蜂的名字**不走翻译键**。`BeeCreator.create` 是这么写的：

        nbt.putString("name", json.has("name") ? json.get("name").getAsString()
                                               : idToName(id) + " Bee");

    没给 `name` 就按 id 拼一个英文的，原样写进实体 NBT；显示时走
    `entity.productivebees.bee_configurable`（原文就是裸的 `%s`），把那个字符串
    整个塞进去。所以资源包够不着它：物品栏的 tooltip 我们还能在
    `ItemTooltipEvent` 里改，手持时屏幕上方那行名字、以及 JEI 的蜂种条目走的是
    另外两条渲染路径，事件根本不经过。

    但 `name` 这个字段是我们**能给**的——照抄上游那份数据文件，只填 `name`，
    其余字段一个不动（少一个蜂就没颜色、没花、没巢偏好）。填上之后那三条路径
    读到的就都是中文，一处代码都不用动。

    只对**真的用 `bee_configurable` 那几版**做：再往后的版本蜂名走的是注册实体的
    翻译键，本来就是中文，往 NBT 里塞名字反而是多此一举。
    """
    z = zipfile.ZipFile(jar)
    if not any(n.endswith('.class') and b'bee_configurable' in z.read(n)
               for n in z.namelist()):
        return 0
    id2zh, en2zh = tables.get('id2zh', {}), tables.get('en2zh', {})
    n = 0
    for name in z.namelist():
        if not (name.startswith(BEE_DATA) and name.endswith('.json')):
            continue
        try:
            d = json.loads(z.read(name).decode('utf-8-sig'))
        except Exception:                                  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        # 上游多数文件自己写了 `name`，写的是英文——那正是要翻的东西，按它查；
        # 没写的那些，代码会按 id 拼名字，所以按 id 查。
        zh = en2zh.get(d['name']) if isinstance(d.get('name'), str) else None
        if zh is None:
            # 文件可能在子目录下（`gems/emerald.json`），蜂的身份看末段
            zh = id2zh.get(name.rsplit('/', 1)[-1][:-len('.json')])
        if not zh or zh == d.get('name'):
            continue                      # 查不到译名就别动人家的文件
        d['name'] = zh
        p = res / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n',
                     encoding='utf-8')
        n += 1
    return n


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


def pack_meta(jar, man, t):
    """`pack.mcmeta` 同样照参考 jar 抄，只把 description 换成我们的。

    这里有个比「版本号 → 格式号」更细的东西：一个 jar 同时带 `assets/` 与
    `data/` 时，资源包格式号与数据包格式号在 1.19 那几版**不是同一个数**
    （9 与 10）。只写一个 `pack_format`，游戏拿它去校验数据包那一侧，对不上就
    把这个包判成不兼容——列在数据包界面里标红，建世界时还要弹一句「这个世界
    启用了实验性选项，随时都有可能崩溃」。

    Forge 为此加了 `forge:resource_pack_format` 与 `forge:data_pack_format`，
    上游 jar 正是这么写的。与其在这里再维护一张「哪个版本要写哪几个字段」的
    表，不如照抄——目标那一版的资源蜜蜂 jar 装在同一个 mods 目录里、由同一个
    游戏读，它没被标红，它那份就是对的。
    """
    try:
        p = {k: v for k, v in json.loads(
            zipfile.ZipFile(jar).read('pack.mcmeta').decode('utf-8-sig'))['pack'].items()
            if not k.startswith('_')}                      # `_comment` 是人家写给自己看的
    except Exception:                                      # noqa: BLE001
        p = {'pack_format': pack_format(t['minecraft'])}   # 参考 jar 没有就自己推
    p['description'] = '%s 简体中文汉化' % man['zh_name']
    return {'pack': p}


def loader_meta(jar):
    """元数据该怎么写，**照参考 jar 抄**，不按版本号推。

    有两样东西随加载器改过写法：

        文件名       `mods.toml` → `neoforge.mods.toml`（NeoForge 1.20.2 起）
        必需标记     `mandatory=true` → `type="required"`（同一时期）

    写错任何一样，加载器在**扫描阶段**就抛 InvalidModFileException。那不是
    「这一个 mod 不加载」——扫描当场中断，玩家看到的是整个 mods 目录一个都没
    进游戏，老版本上直接闪退（1.15.2/1.16.1 实测如此）。

    所以不猜：目标那一版的资源蜜蜂 jar 就装在同一个 mods 目录里、由同一个加载器
    读，它加载得了，它用的就是这一版认的写法。照它抄，顺带把 `neo` 也定下来——
    文件名叫 neoforge.mods.toml 的那一代，依赖里的加载器 modId 才是 neoforge。
    """
    z = zipfile.ZipFile(jar)
    for name in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
        if name not in z.namelist():
            continue
        text = z.read(name).decode('utf-8-sig', 'replace')
        dep = ''.join(text.split('[[dependencies.')[1:])
        if re.search(r'^\s*mandatory\s*=', dep, re.M):
            marker = 'mandatory=true'
        elif re.search(r'^\s*type\s*=', dep, re.M):
            marker = 'type="required"'
        else:
            # 参考 jar 一个依赖都不声明，抄不到样本，退回按文件名判断
            marker = 'type="required"' if 'neoforge' in name else 'mandatory=true'
        return {'file': name.rsplit('/', 1)[-1], 'marker': marker,
                'neo': 'neoforge' in name}
    sys.exit('❌ 参考 jar %s 里没有 mods.toml，抄不到这一版的写法' % Path(jar).name)


def check_toml(text, lm):
    """出包前核一遍：每个依赖块都得有必需标记，且不许混进另一套写法。

    这道闸挡的就是上面那种「扫描阶段整个中断」的故障——它不像少翻一句，
    没法靠玩家反馈慢慢发现，装上去就是一个模组都进不去。
    """
    try:
        import tomllib
        tomllib.loads(text)                  # 语法先过一遍；加载器读不了就全完
    except ImportError:
        print('  ℹ️ 这个 Python 没有 tomllib，跳过语法解析，只核写法')
    except Exception as e:                                     # noqa: BLE001
        return ['元数据不是合法 TOML：%r' % e]
    bad = []
    blocks = text.split('[[dependencies.')[1:]
    if not blocks:
        return ['元数据里一个依赖块都没有']
    other = 'type=' if lm['marker'].startswith('mandatory') else 'mandatory='
    for i, b in enumerate(blocks, 1):
        if lm['marker'] not in b:
            bad.append('第 %d 个依赖块少了 %s（这一版加载器认这个键）'
                       % (i, lm['marker']))
        if other in b:
            bad.append('第 %d 个依赖块混进了 %s（这一版加载器不认）' % (i, other))
    return bad


def mods_toml(man, ver, t, lm):
    """加载器元数据。写法由 loader_meta 从参考 jar 读出来，这里只负责填。"""
    neo = lm['neo']
    # `displayTest` 只有 neoforge.mods.toml 那一代的加载器会读。1.17–1.20 的
    # Forge 把这个键当无关文本略过——不报错，但也什么都不做（在 fmlloader /
    # fmlcore 的 ModInfo、ModContainer 里根本没有这个字符串）。那几版要靠代码
    # 注册扩展点，见 ServerCompat；1.16 及更早也走同一条路。
    dt = ('# 纯客户端显示层，服务端不会有这个 mod。不写这条，进服时可能被判定\n'
          '# 「mod 不一致」而连不上——汉化把人挡在服务器外面是最不能接受的一类故障。\n'
          'displayTest="IGNORE_ALL_VERSION"\n') if neo else ''
    return '''modLoader="javafml"
loaderVersion="[1,)"
license="Custom: 译文 (C) 星野夢華; Productive Bees (C) JDKDigital, All Rights Reserved"
issueTrackerURL="https://github.com/chiba233/ProductiveBees_zh-cn/issues"

[[mods]]
modId="{modid}_zh_cn"
version="{ver}"
displayName="{zh} 汉化"
authors="星野夢華 (Hoshino Yumeka)"
logoFile="logo.png"
# 像素画，别让加载器把它抹糊
logoBlur=false
{dt}description=\'\'\'
{zh}（{en}）的简体中文汉化：物品、方块、蜜蜂、界面，内置导览书全部页面，
以及基因样本 tooltip 里那行**运行期拼出来的蜂种名**（那一行资源包碰不到，
只能在 ItemTooltipEvent 上拦）。
\'\'\'

[[dependencies.{modid}_zh_cn]]
modId="{loader}"
{marker}
versionRange="[0,)"
ordering="NONE"
side="CLIENT"

[[dependencies.{modid}_zh_cn]]
modId="{modid}"
{marker}
versionRange="[0,)"
ordering="AFTER"
side="CLIENT"
'''.format(modid=man['modid'], ver=ver, zh=man['zh_name'], en=man['en_name'],
           loader='neoforge' if neo else 'forge', dt=dt, marker=lm['marker'])


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

    # 内嵌 jar 里的命名空间也要出货：1.21.1 起升级组件搬进了 productivelib，
    # 那个 mod 是打包在资源蜜蜂 jar 里发的。只出 assets/productivebees 的话，
    # 那 18 个升级组件在游戏里全是英文。哪些键属于哪个命名空间，看**那个命名空间的
    # en_us 里有没有这个键**，不靠键名猜。
    for ns, en in sorted(bundled_langs(jar).items()):
        if ns == NS:
            continue
        sub = {k: v for k, v in lang.items() if k in en}
        if not sub:
            continue
        f = res / 'assets' / ns / 'lang' / 'zh_cn.json'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(dict(sorted(sub.items())), ensure_ascii=False,
                                indent=2) + '\n', encoding='utf-8')
        n_lang += len(sub)
        print('  内嵌的 %s 有 %d 条，出货 %d 条' % (ns, len(en), len(sub)))
    if n_var:
        print('  这一版有 %d 条原文和最新版不同，改用对应的译文' % n_var)

    n_book = books.generate(jar, res)
    tables = names.write(jar, res / 'pbzh' / 'bees.json')
    n_bee = bee_data_names(jar, res, tables)
    if n_bee:
        print('  给 %d 只数据包定义的蜂补了中文 name 字段（手持与 JEI 那两处'
              '够不着事件，只能从数据这一侧给）' % n_bee)

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

    lm = loader_meta(jar)
    toml = mods_toml(man, ver, t, lm)
    wrong = check_toml(toml, lm)
    if wrong:
        for w in wrong:
            print('  ❌', w)
        sys.exit('❌ 加载器元数据写法不对，不出包——这种错会让整个 mods 目录扫描中断')
    print('  元数据照 %s 的 %s 写：%s' % (Path(jar).name, lm['file'], lm['marker']))
    (res / 'META-INF').mkdir()
    (res / 'META-INF' / lm['file']).write_text(toml, encoding='utf-8')
    meta = pack_meta(jar, man, t)
    (res / 'pack.mcmeta').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('  pack.mcmeta 照 %s 抄：%s' % (Path(jar).name, json.dumps(
        {k: v for k, v in meta['pack'].items() if k != 'description'},
        ensure_ascii=False)))
    # mods.toml 里 logoFile 指的是 jar 根目录下的文件
    logo = ROOT / 'src' / 'logo.png'
    if logo.is_file():
        shutil.copy2(logo, res / 'logo.png')
    else:
        sys.exit('❌ 缺 src/logo.png，mods.toml 里却写了 logoFile')

    # 两份都进 jar：LICENSE 讲清楚三类东西各归各的，GPL 正文给代码那部分
    (res / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())
    (res / 'LICENSE-GPL-3.0').write_bytes((ROOT / 'LICENSE-GPL-3.0').read_bytes())

    return res, {'lang': n_lang, 'book': n_book,
                 'types': len(tables['type2zh']), 'book_name': book_name(jar, res)}
