#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 jar 真装进游戏里跑一遍——**每个平台都跑**。

出包前的那些闸只验数据：覆盖率、占位符、元数据写法。它们验不了两件事，而这两件
恰恰是最要命的：

    装上去会不会崩          加载器读不读得懂我们的元数据、代码会不会抛
    运行期那套逻辑生不生效  反射找不找得到语言表、现学的蜂名有没有真补进去

这两件只有把游戏起起来才知道，而且**每个平台的答案可能不一样**：1.15–1.16 走的是
SRG 名字的反射、1.17–1.20 是 Forge、1.21 是 NeoForge，三条路的代码都不同。只测
一个平台就说「验过了」是敷衍。

脚本自己准备一切，不碰用户已有的实例：

    原版客户端 / 库 / 资源     从 Mojang 官方接口按 sha1 取
    加载器                     跑官方安装器的 --installClient
    JDK 8 / 17 / 21            从 Adoptium 取（老版本上不了新 JDK）
    探针资源包                 造一份「别的模组的中文材料 + 整合包自定义的蜂键」

判定看日志，不看人眼：

    崩没崩      进程退出码、有没有 crash-report、有没有我们的异常
    生不生效    那行「现学补上 N 条」有没有出现，N 对不对

用法:
    python3 scripts/e2e.py <jar 所在目录>            # 全部平台
    python3 scripts/e2e.py <jar 所在目录> 1.15.2-forge
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E2E = ROOT / 'build' / 'e2e'
MC = E2E / 'mc'                       # 当作一个干净的 .minecraft
UA = {'User-Agent': 'pbzh-e2e/1.0'}
MANIFEST = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'
RES = 'https://resources.download.minecraft.net'
FORGE = ('https://maven.minecraftforge.net/net/minecraftforge/forge/'
         '%s/forge-%s-installer.jar')
NEO = ('https://maven.neoforged.net/releases/net/neoforged/neoforge/'
       '%s/neoforge-%s-installer.jar')
# 1.20.1 的 NeoForge 是 47.x 那一支，targets.json 里记的是 Forge 版本号
NEO_FOR_MC = {'1.20.1': '47.1.106'}
OS_NAME, ARCH = 'osx', 'arm64'
# 探针：材料的中文放 zh_cn（冒充「玩家装了那个模组的汉化」），
# 蜂键放 en_us（冒充「整合包加了自己的蜂，没人译」）
PROBE_ZH = {
    'item.pbzhprobe.tiberium_ingot': '泰伯利亚锭',
    'block.pbzhprobe.tiberium_block': '泰伯利亚块',
    'item.pbzhprobe.uru_metal_ingot': '乌鲁金属锭',
    'block.pbzhprobe.uru_metal_block': '乌鲁金属块',
}
PROBE_EN = {
    'entity.productivebees.tiberium_bee': 'Tiberium Bee',
    'item.productivebees.honeycomb_tiberium': 'Tiberium Comb',
    'block.productivebees.comb_tiberium': 'Tiberium Comb Block',
    'entity.productivebees.uru_metal_bee': 'Uru Metal Bee',
    'item.productivebees.honeycomb_uru_metal': 'Uru Metal Comb',
    # 反面：没有任何模组给过它中文，必须学不出，保持英文
    'entity.productivebees.zzznosuchthing_bee': 'Zzznosuchthing Bee',
}
EXPECT = 5                            # 上面 6 条里应当学出来的条数


def get(url, timeout=300):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout).read()


def fetch(url, path, sha1=None):
    path = Path(path)
    if path.is_file() and (sha1 is None
                           or hashlib.sha1(path.read_bytes()).hexdigest() == sha1):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(get(url))
    return path


def java_major(exe):
    """问它自己是几版。`java_home -v 8` 在只有新 JDK 的机器上会把 26 当成
    「至少 8」返回，光看路径会被骗。"""
    try:
        out = subprocess.run([str(exe), '-version'], capture_output=True,
                             text=True, timeout=60)
        m = re.search(r'version "(\d+)(?:\.(\d+))?', (out.stderr or '') + (out.stdout or ''))
        if not m:
            return 0
        a = int(m.group(1))
        return int(m.group(2) or 0) if a == 1 else a       # "1.8.0_51" → 8
    except Exception:                                      # noqa: BLE001
        return 0


def jdk(major):
    """老版本上不了新 JDK：1.16 要 8，1.17–1.20 要 17。本机没有就现取。

    Apple Silicon 上没有 aarch64 的 JDK 8（那个年代还没这架构），取 x64 的走
    Rosetta——1.15/1.16 的 LWJGL 原生库本来也只有 x86_64，两边正好一致。
    """
    home = E2E / 'jdk' / str(major)
    for exe in list(home.glob('*/Contents/Home/bin/java')) + list(home.glob('*/bin/java')):
        if java_major(exe) == major:
            return exe
    try:
        out = subprocess.run(['/usr/libexec/java_home', '-v', str(major)],
                             capture_output=True, text=True, check=True).stdout.strip()
        cand = Path(out) / 'bin' / 'java'
        if out and java_major(cand) == major:
            return cand
    except Exception:                                      # noqa: BLE001
        pass
    arch = 'x64' if major <= 8 else 'aarch64'
    api = ('https://api.adoptium.net/v3/binary/latest/%d/ga/mac/%s/jdk/'
           'hotspot/normal/eclipse?project=jdk' % (major, arch))
    home.mkdir(parents=True, exist_ok=True)
    tar = home / 'jdk.tar.gz'
    print('   取 JDK %d（%s）…' % (major, arch))
    tar.write_bytes(get(api, timeout=1200))
    subprocess.run(['tar', 'xzf', str(tar), '-C', str(home)], check=True)
    tar.unlink()
    for exe in list(home.glob('*/Contents/Home/bin/java')) + list(home.glob('*/bin/java')):
        if java_major(exe) == major:
            return exe
    raise RuntimeError('取到的 JDK %d 版本对不上' % major)


def vanilla(mc):
    """原版客户端 + 库 + 资源。全部按官方 sha1 校验。"""
    vdir = MC / 'versions' / mc
    vjson = vdir / (mc + '.json')
    if not vjson.is_file():
        man = json.loads(get(MANIFEST))
        url = next(v['url'] for v in man['versions'] if v['id'] == mc)
        vdir.mkdir(parents=True, exist_ok=True)
        vjson.write_bytes(get(url))
    d = json.loads(vjson.read_text(encoding='utf-8'))
    cj = d['downloads']['client']
    fetch(cj['url'], vdir / (mc + '.jar'), cj['sha1'])
    for lib in d['libraries']:
        if not allowed(lib.get('rules')):
            continue
        arts = [(lib.get('downloads') or {}).get('artifact')]
        nk = native_key(lib)
        if nk:
            arts.append(((lib.get('downloads') or {}).get('classifiers') or {}).get(nk))
        for art in filter(None, arts):
            fetch(art['url'], MC / 'libraries' / art['path'], art.get('sha1'))
    ai = d['assetIndex']
    idx = fetch(ai['url'], MC / 'assets' / 'indexes' / (ai['id'] + '.json'), ai['sha1'])
    objs = json.loads(idx.read_text(encoding='utf-8'))['objects']
    todo = [(o['hash'], o['size']) for o in objs.values()]
    have = 0
    for h, _ in todo:
        p = MC / 'assets' / 'objects' / h[:2] / h
        if p.is_file():
            have += 1
    if have < len(todo):
        print('   资源文件 %d/%d，补齐中…' % (have, len(todo)))
        for i, (h, _) in enumerate(todo):
            p = MC / 'assets' / 'objects' / h[:2] / h
            if not p.is_file():
                fetch('%s/%s/%s' % (RES, h[:2], h), p)
            if i % 500 == 0 and i:
                print('      %d/%d' % (i, len(todo)))
    return d


def native_key(lib):
    """这一条库在 macOS 上该取哪个 classifier；不需要就返回 None。

    两代写法不一样：1.15/1.16 用 `natives` 映射（`{"osx": "natives-macos"}`），
    1.19 起把 natives 做成独立的库条目、直接进 classpath，由 LWJGL 自解压。
    只按 classifier 的名字里有没有 `osx` 去猜会漏掉 `natives-macos` 这个写法。
    """
    nat = lib.get('natives') or {}
    k = nat.get(OS_NAME) or nat.get('macos')
    if k:
        return k.replace('${arch}', '64')
    for k in ((lib.get('downloads') or {}).get('classifiers') or {}):
        if 'natives' in k and ('osx' in k or 'macos' in k) and 'arm' not in k \
                and 'x86' not in k and 'x64' not in k:
            return k
    return None


def allowed(rules):
    if not rules:
        return True
    ok = False
    for r in rules:
        o = r.get('os') or {}
        hit = True
        if o.get('name') and o['name'] not in (OS_NAME, 'universal'):
            hit = False
        if o.get('arch') and o['arch'] != ARCH:
            hit = False
        if 'features' in r:
            hit = False
        if hit:
            ok = r.get('action') == 'allow'
    return ok


def loader(tag, t):
    """跑官方安装器把加载器装进我们这个干净的 .minecraft。"""
    neo = t['loader'] == 'NeoForge' and '-' not in str(t.get('loader_version') or '-')
    mc = t['minecraft']
    if t['loader'] == 'NeoForge' and mc in NEO_FOR_MC:
        ver, neo = NEO_FOR_MC[mc], True
    elif neo:
        ver = t['loader_version']
    else:
        ver = t.get('loader_version') or json.loads(
            (ROOT / 'deps.lock.json').read_text(encoding='utf-8'))['forge'][mc]['version']
    url = (NEO if neo else FORGE) % (ver, ver)
    inst = fetch(url, E2E / 'installers' / url.rsplit('/', 1)[-1])
    (MC / 'launcher_profiles.json').parent.mkdir(parents=True, exist_ok=True)
    (MC / 'launcher_profiles.json').write_text('{"profiles":{}}', encoding='utf-8')
    before = {p.name for p in (MC / 'versions').iterdir()} if (MC / 'versions').is_dir() else set()
    java = jdk(t['java'])
    r = subprocess.run([str(java), '-jar', str(inst), '--installClient', str(MC)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, '加载器安装失败: %s' % (r.stderr or r.stdout)[-300:]
    after = {p.name for p in (MC / 'versions').iterdir()}
    new = sorted(after - before)
    if not new:
        # 装过一次了，按版本号找回来
        cand = [n for n in after if ver.split('-')[-1] in n and mc in n]
        if not cand:
            return None, '装完没找到加载器的版本目录'
        new = cand
    return new[-1], None


def merged(vid):
    """加载器的版本 JSON 继承自原版那份，两边合起来才是完整的启动定义。"""
    d = json.loads((MC / 'versions' / vid / (vid + '.json')).read_text(encoding='utf-8'))
    chain = [d]
    while d.get('inheritsFrom'):
        p = MC / 'versions' / d['inheritsFrom'] / (d['inheritsFrom'] + '.json')
        d = json.loads(p.read_text(encoding='utf-8'))
        chain.append(d)
    out = {}
    for d in reversed(chain):
        for k, v in d.items():
            if k == 'libraries':
                out.setdefault('libraries', [])
                out['libraries'] = v + out['libraries']    # 子在前，优先
            elif k == 'arguments':
                out.setdefault('arguments', {'jvm': [], 'game': []})
                for kk in ('jvm', 'game'):
                    out['arguments'][kk] = out['arguments'].get(kk, []) + v.get(kk, [])
            else:
                out[k] = v
    return out


def probe(mc, root):
    from importlib import import_module
    sys.path.insert(0, str(ROOT / 'scripts'))
    fmt = import_module('pack').pack_format(mc)
    p = root / 'resourcepacks' / 'pbzh-probe'
    (p / 'assets' / 'productivebees' / 'lang').mkdir(parents=True, exist_ok=True)
    (p / 'assets' / 'pbzhprobe' / 'lang').mkdir(parents=True, exist_ok=True)
    (p / 'pack.mcmeta').write_text(json.dumps(
        {'pack': {'pack_format': fmt, 'description': 'pbzh e2e probe'}}), encoding='utf-8')
    (p / 'assets' / 'productivebees' / 'lang' / 'en_us.json').write_text(
        json.dumps(PROBE_EN, ensure_ascii=False), encoding='utf-8')
    (p / 'assets' / 'pbzhprobe' / 'lang' / 'zh_cn.json').write_text(
        json.dumps(PROBE_ZH, ensure_ascii=False), encoding='utf-8')
    (root / 'options.txt').write_text(
        'lang:zh_cn\nresourcePacks:["vanilla","file/pbzh-probe"]\n', encoding='utf-8')


def run_one(tag, t, jar, timeout=420):
    print('\n──── %s（MC %s / %s / Java %d）' % (tag, t['minecraft'], t['loader'], t['java']))
    vanilla(t['minecraft'])
    vid, err = loader(tag, t)
    if err:
        return {'tag': tag, 'ok': False, 'why': err}
    d = merged(vid)
    root = E2E / 'run' / tag
    if root.exists():
        shutil.rmtree(root)
    (root / 'mods').mkdir(parents=True)
    pb = ROOT / 'build' / 'pbjars' / t['jar']
    if pb.is_file():
        shutil.copy2(pb, root / 'mods' / pb.name)
    shutil.copy2(jar, root / 'mods' / Path(jar).name)
    probe(t['minecraft'], root)

    cp = []
    for lib in d['libraries']:
        if not allowed(lib.get('rules')):
            continue
        art = (lib.get('downloads') or {}).get('artifact')
        if art and art.get('path'):
            q = MC / 'libraries' / art['path']
            if q.is_file():
                cp.append(q)
        elif lib.get('name'):
            g, a, v = lib['name'].split(':')[:3]
            q = MC / 'libraries' / Path(*g.split('.')) / a / v / ('%s-%s.jar' % (a, v))
            if q.is_file():
                cp.append(q)
    cp.append(MC / 'versions' / t['minecraft'] / (t['minecraft'] + '.jar'))
    nat = E2E / 'natives' / t['minecraft']
    nat.mkdir(parents=True, exist_ok=True)
    for lib in d['libraries']:
        if not allowed(lib.get('rules')):
            continue
        nk = native_key(lib)
        art = ((lib.get('downloads') or {}).get('classifiers') or {}).get(nk) if nk else None
        if not art:
            continue
        q = MC / 'libraries' / art['path']
        if not q.is_file():
            fetch(art['url'], q, art.get('sha1'))
        with zipfile.ZipFile(q) as z:
            for e in z.namelist():
                if e.endswith(('.dylib', '.jnilib')):
                    z.extract(e, nat)

    repl = {
        'natives_directory': str(nat), 'launcher_name': 'pbzh-e2e',
        'launcher_version': '1', 'classpath': ':'.join(str(x) for x in cp),
        'library_directory': str(MC / 'libraries'), 'classpath_separator': ':',
        'version_name': vid, 'primary_jar_name': t['minecraft'] + '.jar',
        'game_directory': str(root), 'assets_root': str(MC / 'assets'),
        'assets_index_name': d['assetIndex']['id'], 'auth_player_name': 'PbzhE2E',
        'auth_uuid': '00000000000040008000000000000001', 'auth_access_token': '0',
        'clientid': '0', 'auth_xuid': '0', 'user_type': 'legacy',
        'version_type': 'release', 'user_properties': '{}',
    }

    def expand(items):
        out = []
        for it in items:
            if isinstance(it, dict):
                if allowed(it.get('rules')):
                    v = it['value']
                    out.extend(v if isinstance(v, list) else [v])
            else:
                out.append(it)
        return [re.sub(r'\$\{(\w+)\}', lambda m: repl.get(m.group(1), m.group(0)), s)
                for s in out]

    java = jdk(t['java'])
    if 'arguments' in d:
        jvm = expand(d['arguments']['jvm'])
        game = expand(d['arguments']['game'])
    else:                              # 1.16 及更早：一个字符串 + 没有 jvm 段
        jvm = ['-Djava.library.path=' + str(nat), '-cp', repl['classpath']]
        game = expand(d['minecraftArguments'].split())
    cmd = [str(java), '-Xmx4G', '-XstartOnFirstThread'] + jvm + [d['mainClass']] + game
    (root / 'cmd.txt').write_text('\n'.join(cmd), encoding='utf-8')

    log = root / 'logs' / 'latest.log'
    proc = subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors='replace')
    out, marker, t0 = [], None, time.time()
    started = False
    while time.time() - t0 < timeout:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            continue
        out.append(line)
        if '现学补上' in line:
            marker = line.strip()
        if 'Sound engine started' in line or 'Created: 1024x512' in line \
                or 'OpenAL initialized' in line:
            started = True
        if started and marker:
            break
    time.sleep(2)
    proc.terminate()
    try:
        proc.wait(20)
    except Exception:                                      # noqa: BLE001
        proc.kill()
    text = ''.join(out)
    (root / 'e2e-stdout.log').write_text(text, encoding='utf-8')
    crash = list((root / 'crash-reports').glob('*.txt')) if (root / 'crash-reports').is_dir() else []
    ours = re.findall(r'at cn\.hoshino[^\n]*', text)
    n = int(re.search(r'现学补上 (\d+) 条', marker).group(1)) if marker else 0
    ok = started and not crash and not ours and n == EXPECT
    return {'tag': tag, 'ok': ok, 'started': started, 'learned': n,
            'crash': [c.name for c in crash], 'ours': ours[:2],
            'why': '' if ok else ('没起来' if not started else
                                  ('崩溃报告 %s' % crash) if crash else
                                  ('我们的异常 %s' % ours[:1]) if ours else
                                  '现学 %d 条，期望 %d' % (n, EXPECT))}


def main(jars, only=None):
    T = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
    jars = Path(jars)
    rows = []
    for tag in sorted(T, key=lambda x: [int(i) for i in T[x]['minecraft'].split('.')]):
        if only and tag != only:
            continue
        j = next(iter(jars.rglob('*mc%s-%s.jar' % (T[tag]['minecraft'],
                                                   T[tag]['loader'].lower()))), None)
        if not j:
            rows.append({'tag': tag, 'ok': False, 'why': '找不到这个平台的 jar'})
            continue
        try:
            rows.append(run_one(tag, T[tag], j))
        except Exception as e:                             # noqa: BLE001
            rows.append({'tag': tag, 'ok': False, 'why': '脚本自身出错: %r' % e})
        r = rows[-1]
        print('   %s %s' % ('✅' if r['ok'] else '❌', r.get('why') or
                            '起来了，现学 %d 条' % r.get('learned', 0)))
    print('\n================ 汇总 ================')
    for r in rows:
        print('%s %-18s %s' % ('✅' if r['ok'] else '❌', r['tag'],
                               r.get('why') or '现学 %d 条' % r.get('learned', 0)))
    bad = [r for r in rows if not r['ok']]
    (E2E / 'result.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                     encoding='utf-8')
    print('\n%d/%d 通过' % (len(rows) - len(bad), len(rows)))
    return len(bad)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    E2E.mkdir(parents=True, exist_ok=True)
    sys.exit(1 if main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None) else 0)
