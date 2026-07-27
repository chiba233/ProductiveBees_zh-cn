#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""打出资源蜜蜂的汉化 mod。

这个仓库**自给自足**：译文、导览书映射、生成逻辑全在 `src/` 与 `scripts/` 里，
不依赖任何别的仓库。

外部输入只有两样，都按字节钉死在 `deps.lock.json` 里：

1. 目标那一版的**资源蜜蜂 jar**（按 sha256 + 不可变的 CurseForge fileID）。
   导览书的中文版是拿「原文 → 译文」映射现套到它自带那份 JSON 上生成的——
   仓库里不存任何一份上游副本，所以非有它不可。
2. **Gradle 发行版**（按 sha256）。不用 wrapper：`gradle-wrapper.jar` 是二进制，
   这个仓库不放二进制。

**只发 jar**：一个 jar 装完就是全部汉化，不额外要资源包、不额外要脚本。
做不到就别做——让玩家装两三样东西才凑齐一份汉化，那是半成品。

用法:
    python3 scripts/build.py <版本号> [目标]      # 例：python3 scripts/build.py r1
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
LOCK = json.loads((ROOT / 'deps.lock.json').read_text(encoding='utf-8'))
MAN = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
TARGETS = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
BUILD = ROOT / 'build'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
CF = 'https://www.curseforge.com/api/v1/mods/%d/files/%d/download'


def run(*cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fetch_jar(spec, into):
    """取一个资源蜜蜂 jar，逐字节核。下错版本当场失败，不是「凑合套一下」。"""
    into.mkdir(parents=True, exist_ok=True)
    p = into / spec['jar']
    if not p.is_file():
        url = CF % (spec['curseforge_project_id'], spec['curseforge_file_id'])
        print('下载 %s …' % spec['jar'])
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180) as r:
            data = r.read()
            final = urllib.parse.unquote(str(r.url).rsplit('/', 1)[-1].split('?')[0])
        if final != spec['jar']:
            sys.exit('❌ 跳转后的文件名是 %s，不是 %s——CurseForge 给错文件了'
                     % (final, spec['jar']))
        p.write_bytes(data)
    got = sha256(p)
    if got != spec['sha256']:
        sys.exit('❌ %s 的 sha256 对不上\n   记录 %s\n   实得 %s'
                 % (spec['jar'], spec['sha256'], got))
    return p


def fetch_gradle():
    g = LOCK['gradle']
    home = BUILD / 'gradle' / ('gradle-%s' % g['version'])
    if not (home / 'bin' / 'gradle').is_file():
        z = BUILD / 'gradle' / ('gradle-%s-bin.zip' % g['version'])
        z.parent.mkdir(parents=True, exist_ok=True)
        if not z.is_file():
            print('下载 Gradle %s …' % g['version'])
            with urllib.request.urlopen(urllib.request.Request(
                    g['url'], headers={'User-Agent': UA}), timeout=600) as r:
                z.write_bytes(r.read())
        got = sha256(z)
        if got != g['sha256']:
            sys.exit('❌ Gradle 发行版 sha256 对不上\n   记录 %s\n   实得 %s'
                     % (g['sha256'], got))
        with zipfile.ZipFile(z) as zf:
            zf.extractall(z.parent)
        (home / 'bin' / 'gradle').chmod(0o755)
    return home / 'bin' / 'gradle'


def find_jdk(ver):
    for c in (os.environ.get('JAVA_HOME_%s_X64' % ver),
              os.environ.get('JAVA_HOME_%s_arm64' % ver),
              '/opt/homebrew/opt/openjdk@%s' % ver,
              '/usr/lib/jvm/temurin-%s-jdk-amd64' % ver,
              '/usr/lib/jvm/java-%s-openjdk-amd64' % ver):
        if c and (Path(c) / 'bin' / 'java').is_file():
            return c
    try:
        out = subprocess.run(['/usr/libexec/java_home', '-v', str(ver)],
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return None


def selftest(modjar, jdk):
    """对着**打好的那个 jar** 跑一遍译名逻辑。

    测的是真字节码 + 真打进去的表 + 真 tooltip 文本，不是源码、也不是另一份表。
    纯逻辑那个类里没有任何 Minecraft 类型，所以不用起游戏就能验。
    """
    javac = str(Path(jdk) / 'bin' / 'javac') if jdk else 'javac'
    java = str(Path(jdk) / 'bin' / 'java') if jdk else 'java'
    gson = sorted((BUILD / 'gradle').rglob('gson-*.jar'))
    if not gson:
        print('ℹ️ 找不到 gson，跳过自测')
        return
    out = BUILD / 'test'
    out.mkdir(parents=True, exist_ok=True)
    run(javac, '-d', str(out), str(ROOT / 'mod' / 'test' / 'TestTranslate.java'))
    print('自测（真 jar + 真表）:')
    run(java, '-cp', os.pathsep.join([str(out), str(modjar), str(gson[0])]),
        'TestTranslate')


def build_one(ver, tag, t, gradle):
    """出一个平台的 jar。**数据源只有 src/ 那一份**，各平台不分叉。"""
    print('\n──── %s — Minecraft %s / %s / Java %d ────'
          % (tag, t['minecraft'], t['loader'], t['java']))
    import pack
    jar = fetch_jar(t, BUILD / 'pbjars')
    res, stat = pack.build(MAN, jar, ver, t)

    env = dict(os.environ)
    jdk = find_jdk(t['java'])
    if jdk:
        env['JAVA_HOME'] = jdk
    print('编译 …')
    run(str(gradle), '--no-daemon', '-q', 'clean', 'build',
        '-PmodVersion=%s' % ver, '-PjavaVersion=%s' % t['java'],
        '-Ploader=%s' % t['loader'].lower(), '-PmcVersion=%s' % t['minecraft'],
        cwd=ROOT / 'mod', env=env)

    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    built = [b for b in sorted((ROOT / 'mod' / 'build' / 'libs').glob('*.jar'))
             if not b.name.endswith(('-sources.jar', '-dev.jar'))]
    if not built:
        sys.exit('❌ %s: Gradle 没产出 jar' % tag)
    modjar = out / ('%s-%s-mc%s-%s.jar'
                    % (MAN['id'], ver, t['minecraft'], t['loader'].lower()))
    shutil.copy2(built[-1], modjar)
    selftest(modjar, jdk)
    print('✅ %s  (%.1f KB)  lang %d / 导览书 %d / 类型行 %d'
          % (modjar.name, modjar.stat().st_size / 1024,
             stat['lang'], stat['book'], stat['types']))
    return modjar


def main(ver, only=None):
    """**一次 build 出全部平台**，全部共用 src/ 里同一份数据源。"""
    todo = {k: v for k, v in TARGETS.items()
            if v.get('buildable') and (only is None or k == only)}
    skipped = sorted(k for k, v in TARGETS.items() if not v.get('buildable'))
    if not todo:
        sys.exit('❌ 没有可构建的目标（--only 写错了？）')
    gradle = fetch_gradle()
    print('Gradle %s 逐字节与 deps.lock.json 一致 ✅' % LOCK['gradle']['version'])
    print('本次要出 %d 个平台的 jar' % len(todo))
    if skipped:
        # 说出来，别让矩阵看着很宽实际出不来
        print('跳过 %d 个：%s（当前工具链覆盖不到，ModDevGradle 建立在 NeoForm 上，'
              '够不着 1.16 及更早）' % (len(skipped), ' '.join(skipped)))
    made = []
    for tag in sorted(todo, key=lambda x: ([int(y) for y in
                      todo[x]['minecraft'].split('.')], todo[x]['loader']), reverse=True):
        made.append(build_one(ver, tag, todo[tag], gradle))
    print('\n✅ 共 %d 个 jar 在 dist/' % len(made))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
