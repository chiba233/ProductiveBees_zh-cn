#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""1.15.2 – 1.16.5 的构建路径：不走 Gradle，直接 javac。

**为什么不用 ModDevGradle**：它建立在 NeoForm 上，够不着 1.16 及更早。
**为什么不用 ForgeGradle 5**：那条路要另配一套 Gradle 7 + Java 8 的环境，
只为了一件事——把源码里的 `getString()` 重映射成 `func_150261_e()`。

而这个 mod 根本不需要重映射：
它一个 Minecraft 方法都不直接调（{@code LegacyEntry} 全靠按类型反射），
只用到 Forge 自己的类——那些名字本来就不参与混淆。于是编译期需要的东西只剩：

1. **Forge 官方 universal jar**（按 sha256 钉死）——`@Mod`、`MinecraftForge`、
   `ItemTooltipEvent` 都是真货，签名由它说了算，不是我猜的；
2. **Gson 2.8.0**（按 sha256 钉死）——1.16 那批 Minecraft 自带的就是这一档。
   拿最老的那版当编译期依赖，等于给「别用新 Gson API」加了一道机械闸：
   写了 `JsonParser.parseReader` 当场编不过（这个坑 1.17.1 上真踩过）；
3. 几个**空壳桩类**：Minecraft 的 `ITextComponent`、eventbus 的 `Event`/`IEventBus`
   之类，只为让 javac 能把 Forge 那些类的继承链走通。桩类**不进 jar**，
   运行期加载的是游戏里真的那些。缺哪个由 javac 自己说——照它报的错现补，
   不是我列一张清单去猜。

出包前还有两道**锚到字节**的闸：
- 源码里写死的 Minecraft 类名（`StringTextComponent` 等），必须能在**那一版
  资源蜜蜂真 jar 的常量池**里找到——名字对不上当场失败；
- 打好的 jar 里不许混进任何 `net/` 开头的类（桩类漏出去会顶掉游戏的真类）。

用法:
    python3 scripts/legacy.py lock          # 拉 Forge 版本号并写进 deps.lock.json
    python3 scripts/legacy.py build 1.0.0 1.16.5-forge
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
BUILD = ROOT / 'build'
LOCK_PATH = ROOT / 'deps.lock.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PROMOS = 'https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json'
FORGE = ('https://maven.minecraftforge.net/net/minecraftforge/forge/'
         '%(v)s/forge-%(v)s-universal.jar')
GSON = ('https://repo1.maven.org/maven2/com/google/code/gson/gson/'
        '%(v)s/gson-%(v)s.jar')
# 那一版的 SRG 映射表：游戏里运行时真正用的名字，出处比任何猜测都硬
MCP = ('https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp_config/'
       '%(mc)s/mcp_config-%(mc)s.zip')
GSON_VERSION = '2.8.0'

SRC = ROOT / 'mod' / 'src'
ENTRY = SRC / 'forge_legacy' / 'java'

# 桩类：先给一份起手式（javac 走 Forge 的继承链一定会要这几个），
# 剩下缺什么由 javac 报错现补，见 autostub()。
SEED_STUBS = {
    'net.minecraftforge.eventbus.api.Event': 'class',
    'net.minecraftforge.eventbus.api.IEventBus': 'ibus',
    'net.minecraft.util.text.ITextComponent': 'interface',
}
# javac 说「找不到 X 的类文件」时，X 是接口还是类它不说。按已知的命名法判：
# Minecraft/Forge 那个年代，接口一律 I 开头。
IFACE = re.compile(r'\.I[A-Z]')


def get(url, timeout=300):
    return urllib.request.urlopen(urllib.request.Request(
        url, headers={'User-Agent': UA}), timeout=timeout).read()


def sha256(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def lock():
    """把各版本的 Forge 与 Gson 钉进 deps.lock.json。版本号不手写，现拉现记。"""
    import hashlib
    d = json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    targets = json.loads((ROOT / 'versions' / 'targets.json')
                         .read_text(encoding='utf-8'))
    mcs = sorted({t['minecraft'] for t in targets.values()
                  if t.get('toolchain') == 'javac'},
                 key=lambda s: [int(x) for x in s.split('.')])
    promos = json.loads(get(PROMOS))['promos']
    out = d.get('forge', {})
    for mc in mcs:
        v = promos.get(mc + '-recommended') or promos.get(mc + '-latest')
        if not v:
            sys.exit('❌ Forge 没有 %s 的版本' % mc)
        full = '%s-%s' % (mc, v)
        url = FORGE % {'v': full}
        if out.get(mc, {}).get('version') == full:
            continue
        print('拉 Forge %s …' % full)
        b = get(url)
        out[mc] = {'version': full, 'url': url,
                   'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    d['forge'] = out
    mcp = d.get('mcp_config', {})
    for mc in mcs:
        if mc in mcp:
            continue
        url = MCP % {'mc': mc}
        print('拉 MCPConfig %s …' % mc)
        b = get(url)
        mcp[mc] = {'version': mc, 'url': url,
                   'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    d['mcp_config'] = mcp
    moj = d.get('mojang_mappings', {})
    for mc in mcs:
        if mc in moj:
            continue
        url = mojang_url(mc)
        print('拉官方混淆表 %s …' % mc)
        b = get(url)
        moj[mc] = {'version': mc, 'url': url,
                   'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    d['mojang_mappings'] = moj
    if d.get('gson', {}).get('version') != GSON_VERSION:
        url = GSON % {'v': GSON_VERSION}
        b = get(url)
        d['gson'] = {'version': GSON_VERSION, 'url': url,
                     'sha256': hashlib.sha256(b).hexdigest(), 'size': len(b)}
    LOCK_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n',
                         encoding='utf-8')
    print('deps.lock.json 已更新：Forge %d 个版本 + Gson %s'
          % (len(out), d['gson']['version']))


def fetch_pinned(spec, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        print('下载 %s …' % path.name)
        path.write_bytes(get(spec['url']))
    got = sha256(path.read_bytes())
    if got != spec['sha256']:
        sys.exit('❌ %s 的 sha256 对不上\n   记录 %s\n   实得 %s'
                 % (path.name, spec['sha256'], got))
    return path


def deps(mc):
    d = json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    if mc not in d.get('forge', {}):
        sys.exit('❌ deps.lock.json 里没有 Minecraft %s 的 Forge。'
                 '先跑 `python3 scripts/legacy.py lock`。' % mc)
    f = d['forge'][mc]
    forge = fetch_pinned(f, BUILD / 'forge' / ('forge-%s-universal.jar' % f['version']))
    gson = fetch_pinned(d['gson'], BUILD / 'forge' / ('gson-%s.jar' % d['gson']['version']))
    return forge, gson, f['version']


def mappings(mc):
    """那一版的 SRG 映射表（MCPConfig 的 joined.tsrg），按 sha256 钉死。

    这是**游戏里运行时真正的名字**的权威出处：类名是人看得懂的，方法名被换成了
    `func_150261_e`。返回 {SRG 类名: [(SRG 方法名, SRG 描述符), …]}。

    tsrg 里的描述符是**混淆侧**的类型名，得先拿类名映射把它翻回 SRG 侧，
    不然「返回 Style 的方法」这种条件根本对不上。
    """
    d = json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    spec = d.get('mcp_config', {}).get(mc)
    if not spec:
        sys.exit('❌ deps.lock.json 里没有 %s 的 mcp_config。'
                 '先跑 `python3 scripts/legacy.py lock`。' % mc)
    p = fetch_pinned(spec, BUILD / 'forge' / ('mcp_config-%s.zip' % mc))
    with zipfile.ZipFile(p) as z:
        text = z.read('config/joined.tsrg').decode('utf-8')
    obf2srg, raw, cur = {}, {}, None
    for line in text.splitlines():
        if not line.startswith('\t'):
            parts = line.split()
            if len(parts) >= 2:
                cur = parts[1]
                obf2srg[parts[0]] = cur
                raw.setdefault(cur, [])
        elif cur is not None:
            parts = line.strip().split()
            if len(parts) == 3:                    # 方法：obf名 obf描述符 srg名
                raw[cur].append((parts[2], parts[1], parts[0]))
    sub = re.compile(r'L([^;]+);')

    def to_srg(d_):
        return sub.sub(lambda m: 'L%s;' % obf2srg.get(m.group(1), m.group(1)), d_)

    return obf2srg, {c: [(srg, to_srg(d_), obf, d_) for srg, d_, obf in ms]
                     for c, ms in raw.items()}


# Mojang 从 1.14.4 起公开自己的混淆表。它给的是 obf ↔ **官方名**，SRG 表给的是
# obf ↔ **游戏里运行时的名**；拿 obf 当桥一联结，就能从「我知道的官方名」
# 直接查到「运行期该反射哪个名字」。猜没了，剩下的全是查表。
MOJANG_MANIFEST = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'
PRIM = {'int': 'I', 'void': 'V', 'boolean': 'Z', 'byte': 'B', 'char': 'C',
        'short': 'S', 'long': 'J', 'float': 'F', 'double': 'D'}


def mojang_url(mc):
    man = json.loads(get(MOJANG_MANIFEST))
    for v in man['versions']:
        if v['id'] == mc:
            pkg = json.loads(get(v['url']))
            m = pkg.get('downloads', {}).get('client_mappings')
            if not m:
                sys.exit('❌ Minecraft %s 没有公开混淆表' % mc)
            return m['url']
    sys.exit('❌ 版本清单里没有 Minecraft %s' % mc)


def proguard(text):
    """解 Mojang 的混淆表：官方名 -> obf 名。"""
    moj2obf, members, cur = {}, {}, None
    num = re.compile(r'^\d+:\d+:')
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        if not line.startswith(' '):
            moj, obf = line.rstrip(':').split(' -> ')
            moj2obf[moj] = obf
            cur = moj
            members[cur] = []
        elif cur is not None and '(' in line:
            body, obf = line.strip().rsplit(' -> ', 1)
            body = num.sub('', body)
            head, args = body.split('(', 1)
            ret, name = head.rsplit(' ', 1)
            members[cur].append((name, ret, [a for a in args.rstrip(')').split(',') if a],
                                obf))
    return moj2obf, members


def jvm_type(t, moj2obf):
    arr = 0
    while t.endswith('[]'):
        t, arr = t[:-2], arr + 1
    base = PRIM.get(t) or ('L%s;' % moj2obf.get(t, t).replace('.', '/'))
    return '[' * arr + base


CHAT = 'net.minecraft.network.chat.'
# 要查的三个方法，按**官方名**写。`setStyle` 在 1.16 起挪到了 MutableComponent 上，
# 1.15.2 还在 Component 上——两个都试，哪个声明了算哪个，不写死版本。
WANTED = [
    ('getString', [CHAT + 'Component'], 'getString', []),
    ('getStyle', [CHAT + 'Component'], 'getStyle', []),
    ('setStyle', [CHAT + 'MutableComponent', CHAT + 'Component'], 'setStyle',
     [CHAT + 'Style']),
]


def runtime_names(mc):
    """算出**运行期该反射哪些名字**。

    官方混淆表给「官方名 ↔ obf 名」，SRG 表给「obf 名 ↔ 运行期名」，
    拿 obf 当桥一联结就得到「官方名 → 运行期名」。全程查表，没有一处是猜的。
    """
    d = json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    spec = d.get('mojang_mappings', {}).get(mc)
    if not spec:
        sys.exit('❌ deps.lock.json 里没有 %s 的官方混淆表。先跑 `legacy.py lock`。' % mc)
    txt = fetch_pinned(spec, BUILD / 'forge' / ('mojang-%s.txt' % mc)).read_text(
        encoding='utf-8')
    moj2obf, members = proguard(txt)
    obf2srg, srg = mappings(mc)

    def srg_class(moj):
        return obf2srg.get(moj2obf.get(moj, ''), '')

    def find(classes, meth, params):
        for cls in classes:
            if cls not in moj2obf:
                continue
            sc = srg_class(cls)
            want = '(%s)' % ''.join(jvm_type(p, moj2obf) for p in params)
            for name, _ret, ps, obf in members.get(cls, []):
                if name != meth or len(ps) != len(params):
                    continue
                for srg_name, _sd, obf_name, obf_desc in srg.get(sc, []):
                    if obf_name == obf and obf_desc.startswith(want):
                        return sc.replace('/', '.'), srg_name
        return None

    out = {}
    for alias, classes, meth, params in WANTED:
        hit = find(classes, meth, params)
        if not hit:
            sys.exit('❌ Minecraft %s 上查不到 %s(%s) 的运行期名字——'
                     '这一版的形状和预期不一样，先搞清楚再出包'
                     % (mc, meth, ', '.join(p.rsplit('.', 1)[-1] for p in params)))
        out[alias] = {'owner': hit[0], 'name': hit[1]}
    impl = srg_class(CHAT + 'TextComponent')
    if not impl:
        sys.exit('❌ Minecraft %s 上找不到纯文本组件的实现类' % mc)
    out['impl'] = {'owner': impl.replace('/', '.'), 'name': impl.replace('/', '.')}
    return out


def anchor(mc):
    """把源码里写死的 Minecraft 类名，对着**那一版的 SRG 映射**核一遍。

    这条闸挡的是「名字在某一版换了而我不知道」：桩类是我自己造的，我说它叫什么
    它就叫什么，所以编译一定过——错要到玩家进游戏才炸。
    """
    src = (ENTRY / 'cn' / 'hoshino' / 'pbzh' / 'LegacyEntry.java').read_text(
        encoding='utf-8')
    want = sorted(set(re.findall(r'"(net\.minecraft\.[A-Za-z0-9_.$]+)"', src))
                  | set(re.findall(r'import (net\.minecraft\.[A-Za-z0-9_.$]+);', src)))
    _obf2srg, mp = mappings(mc)
    missing = [w for w in want if w.replace('.', '/') not in mp]
    if missing:
        sys.exit('❌ 这些类名在 Minecraft %s 的 SRG 映射里不存在：\n   %s' %
                 (mc, '\n   '.join(missing)))
    names = runtime_names(mc)
    print('  名字锚定：%d 个类名对上 SRG 映射；运行期反射用 %s / %s / %s，'
          '实现类 %s ✅'
          % (len(want), names['getString']['name'], names['getStyle']['name'],
             names['setStyle']['name'], names['impl']['name'].rsplit('.', 1)[-1]))
    return names


def write_stub(root, fqn, kind):
    pkg, _, cls = fqn.rpartition('.')
    p = root / pkg.replace('.', '/') / (cls + '.java')
    p.parent.mkdir(parents=True, exist_ok=True)
    if kind == 'ibus':
        body = ('public interface IEventBus {\n'
                '    <T> void addListener(java.util.function.Consumer<T> c);\n'
                '    void register(Object target);\n}\n')
    elif kind == 'interface':
        body = 'public interface %s {\n}\n' % cls
    else:
        body = 'public class %s {\n}\n' % cls
    p.write_text('// 编译期桩，**不进 jar**：运行期用的是游戏里真的那个类。\n'
                 'package %s;\n\n%s' % (pkg, body), encoding='utf-8')
    return p


MISSING = re.compile(r'class file for ([\w.$]+) not found')
MISSING2 = re.compile(r'找不到 ([\w.$]+) 的类文件')
CANNOT = re.compile(r'cannot access ([\w.$]+)')


def autostub(out, cp, sources, stub_root, java_release):
    """编 → 看 javac 缺什么 → 补桩 → 再编。缺什么由它说，不由我猜。

    桩类编到**另一个目录**，只当 classpath 用：和本 mod 的类混在一起就会被打进
    jar，运行时顶掉游戏里真的那些类。
    """
    kinds = dict(SEED_STUBS)
    for fqn, kind in kinds.items():
        write_stub(stub_root, fqn, kind)
    stub_out = stub_root.parent / 'stubclasses'
    stub_out.mkdir(exist_ok=True)
    for _round in range(12):
        stubs = sorted(str(p) for p in stub_root.rglob('*.java'))
        subprocess.run(['javac', '-nowarn', '-encoding', 'UTF-8',
                        '-d', str(stub_out)] + java_release + stubs,
                       capture_output=True, text=True, check=True)
        cmd = ['javac', '-nowarn', '-encoding', 'UTF-8',
               '-cp', ':'.join([str(c) for c in cp] + [str(stub_out)]),
               '-d', str(out)] + java_release + sources
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return sorted(kinds)
        need = set(MISSING.findall(r.stderr)) | set(MISSING2.findall(r.stderr)) \
            | set(CANNOT.findall(r.stderr))
        need = {n for n in need if n not in kinds and '.' in n}
        if not need:
            sys.stderr.write(r.stderr)
            sys.exit('❌ javac 编不过，而且缺的不是类文件——见上面的报错')
        for fqn in sorted(need):
            kinds[fqn] = 'interface' if IFACE.search(fqn) else 'class'
            write_stub(stub_root, fqn, kinds[fqn])
        print('  javac 说还缺 %d 个类，已补桩：%s'
              % (len(need), ' '.join(sorted(n.rsplit('.', 1)[-1] for n in need))))
    sys.exit('❌ 补了 12 轮桩还编不过，别再自动兜了')


# 类文件主版本 = Java 版本 + 44
def bytecode_gate(classes, java):
    """逐个类文件核字节码版本。编高了玩家进游戏就是 UnsupportedClassVersionError，
    而编译本身一声不吭——这种错只能靠事后核字节抓。"""
    want = java + 44
    bad = []
    for p in sorted(classes.rglob('*.class')):
        major = int.from_bytes(p.read_bytes()[6:8], 'big')
        if major != want:
            bad.append('%s: 主版本 %d（要 %d）' % (p.name, major, want))
    if bad:
        sys.exit('❌ 字节码版本不对，装上去会 UnsupportedClassVersionError：\n   %s'
                 % '\n   '.join(bad))
    print('  字节码版本核对：%d 个类都是 Java %d（主版本 %d）✅'
          % (len(list(classes.rglob('*.class'))), java, want))


def jar_up(classes, res, out_jar):
    """自己封 jar：不许混进桩类。"""
    out_jar.parent.mkdir(parents=True, exist_ok=True)
    stray = [str(p.relative_to(classes)) for p in classes.rglob('*.class')
             if not str(p.relative_to(classes)).startswith('cn/')]
    if stray:
        sys.exit('❌ 编译产物里混进了非本 mod 的类（桩类漏出去会顶掉游戏的真类）：\n   %s'
                 % '\n   '.join(stray[:10]))
    with zipfile.ZipFile(out_jar, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
        for base in (classes, res):
            for p in sorted(base.rglob('*')):
                if p.is_file():
                    z.write(p, str(p.relative_to(base)))
    return out_jar


def build_one(ver, tag, t, man):
    import pack
    import build as B

    print('\n──── %s — Minecraft %s / %s / Java %d（javac 直编，不过 Gradle）────'
          % (tag, t['minecraft'], t['loader'], t['java']))
    forge, gson, forge_ver = deps(t['minecraft'])
    print('  Forge %s / Gson %s 逐字节与 deps.lock.json 一致 ✅'
          % (forge_ver, GSON_VERSION))

    pb = B.fetch_jar(t, BUILD / 'pbjars')
    names = anchor(t['minecraft'])
    res, stat = pack.build(man, pb, ver, t)
    # 运行期该反射哪些名字，**按目标版本现算现写**，mod 里一个都不写死
    (res / 'pbzh').mkdir(parents=True, exist_ok=True)
    (res / 'pbzh' / 'legacy.json').write_text(
        json.dumps(names, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    work = BUILD / 'legacy' / tag
    if work.exists():
        shutil.rmtree(work)
    classes, stub_root = work / 'classes', work / 'stubs'
    classes.mkdir(parents=True)
    stub_root.mkdir(parents=True)

    sources = sorted(str(p) for p in
                     list((SRC / 'main' / 'java').rglob('*.java'))
                     + list(ENTRY.rglob('*.java')))
    # **一律 `--release`**，不靠「手上正好是哪个 JDK」。上一次栽的就是这个：
    # 所有平台都编成了 Java 21 字节码，1.20.1 装上直接 UnsupportedClassVersionError。
    print('  编译（目标字节码 Java %d）…' % t['java'])
    stubbed = autostub(classes, [forge, gson], sources, stub_root,
                       ['--release', str(t['java'])])
    print('  桩类共 %d 个，一个都不进 jar' % len(stubbed))
    bytecode_gate(classes, t['java'])

    out = ROOT / 'dist'
    modjar = out / ('%s-%s-mc%s-%s.jar'
                    % (man['id'], ver, t['minecraft'], t['loader'].lower()))
    jar_up(classes, res, modjar)
    B.selftest(modjar, None)
    print('✅ %s  (%.1f KB)  lang %d / 导览书 %d / 类型行 %d'
          % (modjar.name, modjar.stat().st_size / 1024,
             stat['lang'], stat['book'], stat['types']))
    return modjar


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] not in ('lock', 'build'):
        sys.exit(__doc__)
    if a[0] == 'lock':
        lock()
    else:
        import build as B
        T = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
        MANIFEST = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        build_one(B.check_version(a[1]), a[2], T[a[2]], MANIFEST)
