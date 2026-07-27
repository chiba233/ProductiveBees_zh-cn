#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""按 SOURCE.lock 打出资源蜜蜂的独立汉化 mod。

这个仓库**一行译文都不存**。译文与生成器都在 atm10-zh-cn，SOURCE.lock 按 commit
钉死一个版本，构建时现拉现打。两边各存一份必然漂移，最后同一只蜂在整合包里叫一个名、
在这里叫另一个名。

它跟整合包版的关系：**互补，不是替代**。
  - ATM10 整合包走 KubeJS 显示层（那边本来就有 KubeJS，更合适）
  - 这个 mod 是给别的整合包用的——不想逐个适配 KubeJS 的时候丢进 mods/ 就完事

每一步都有字节锚点：

1. 上游仓库按 commit 取（不是分支——分支会动）
2. 模组 jar 按 sha256 核（导览书要拿映射现套到它自带那份 JSON 上）
3. Gradle 发行版按 sha256 核（不入库，也不用 wrapper jar——那是个二进制）
4. 出包前对着目标 jar 点名覆盖率，不到 100% 不出包

用法:
    python3 scripts/build.py <版本号>          # 例：python3 scripts/build.py r12
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
LOCK = json.loads((ROOT / 'SOURCE.lock').read_text(encoding='utf-8'))
MAN = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
UP = ROOT / 'upstream'
BUILD = ROOT / 'build'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def run(*cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fetch_source():
    src = LOCK['source']
    if not (UP / '.git').is_dir():
        UP.mkdir(parents=True, exist_ok=True)
        run('git', 'init', '-q', str(UP))
        run('git', '-C', str(UP), 'remote', 'add', 'origin', src['repo'])
    run('git', '-C', str(UP), 'fetch', '-q', '--depth', '1', 'origin', src['commit'])
    run('git', '-C', str(UP), 'checkout', '-q', src['commit'])
    got = subprocess.run(['git', '-C', str(UP), 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, check=True).stdout.strip()
    if got != src['commit']:
        sys.exit('❌ 上游 commit 对不上：想要 %s，实得 %s' % (src['commit'], got))
    print('上游 %s @ %s' % (src['repo'], got[:12]))


def fetch_mod():
    m = LOCK['mod']
    mods = BUILD / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    p = mods / m['name']
    if not p.is_file():
        url = ('https://www.curseforge.com/api/v1/mods/%d/files/%d/download'
               % (m['curseforge_project_id'], m['curseforge_file_id']))
        print('下载 %s …' % m['name'])
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180) as r:
            data = r.read()
            final = urllib.parse.unquote(str(r.url).rsplit('/', 1)[-1].split('?')[0])
        if final != m['name']:
            sys.exit('❌ 跳转后的文件名是 %s，不是 %s——CurseForge 给错文件了'
                     % (final, m['name']))
        p.write_bytes(data)
    got = sha256(p)
    if got != m['sha256']:
        sys.exit('❌ %s 的 sha256 与 SOURCE.lock 对不上\n   记录 %s\n   实得 %s'
                 % (m['name'], m['sha256'], got))
    print('模组 jar 逐字节与 SOURCE.lock 一致 ✅')
    return p, mods


def fetch_gradle():
    """按 sha256 取 Gradle 发行版。

    不用 wrapper：`gradle-wrapper.jar` 是个二进制，这个仓库不放二进制。
    发行版 zip 现下现核，效果一样，而且哈希摆在 SOURCE.lock 里能看见。
    """
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
    print('Gradle %s 逐字节与 SOURCE.lock 一致 ✅' % g['version'])
    return home / 'bin' / 'gradle'


def find_jdk21():
    """Gradle 与 NeoForge 的工具链要 Java 21。找不到就让 Gradle 自己解决。"""
    for c in (os.environ.get('JAVA_HOME_21_X64'), os.environ.get('JAVA_HOME_21_arm64'),
              '/opt/homebrew/opt/openjdk@21', '/usr/lib/jvm/temurin-21-jdk-amd64',
              '/usr/lib/jvm/java-21-openjdk-amd64'):
        if c and (Path(c) / 'bin' / 'java').is_file():
            return c
    try:
        out = subprocess.run(['/usr/libexec/java_home', '-v', '21'],
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return None


def selftest(modjar):
    """对着**打好的那个 jar** 跑一遍译名逻辑。

    测的是真字节码 + 真打进去的表，不是源码、也不是另一份表。
    纯逻辑那个类里没有任何 Minecraft 类型，所以不用起游戏就能验。
    """
    jdk = find_jdk21() or ''
    javac = str(Path(jdk) / 'bin' / 'javac') if jdk else 'javac'
    java = str(Path(jdk) / 'bin' / 'java') if jdk else 'java'
    gson = sorted((BUILD / 'gradle').rglob('gson-*.jar'))
    gson += sorted((Path.home() / '.gradle').rglob('gson-*.jar')) if not gson else []
    if not gson:
        print('ℹ️ 找不到 gson，跳过自测')
        return
    out = BUILD / 'test'
    out.mkdir(parents=True, exist_ok=True)
    run(javac, '-d', str(out), str(ROOT / 'mod' / 'test' / 'TestTranslate.java'))
    cp = os.pathsep.join([str(out), str(modjar), str(gson[0])])
    print('自测（真 jar + 真表）:')
    run(java, '-cp', cp, 'TestTranslate')


def main(ver):
    fetch_source()
    jar, mods = fetch_mod()
    gradle = fetch_gradle()

    # 上游的路径约定读的是环境变量，必须在 import 之前设好
    os.environ['ATM_BUILD'] = str(BUILD / 'atm')
    run(sys.executable, 'scripts/assemble.py', cwd=UP, env=dict(os.environ))
    sys.path.insert(0, str(UP / 'scripts'))
    import paths                                             # noqa: E402
    import gen_books                                         # noqa: E402
    import gen_pb_hanhua                                     # noqa: E402
    sys.path.insert(0, str(ROOT / 'scripts'))
    import pack                                              # noqa: E402

    res, stat = pack.build(MAN, jar, mods, ver, paths.COMMON, paths.PACK,
                           gen_books, gen_pb_hanhua)

    env = dict(os.environ)
    jdk = find_jdk21()
    if jdk:
        env['JAVA_HOME'] = jdk
        print('用 JDK 21: %s' % jdk)
    print('编译 mod …')
    run(str(gradle), '--no-daemon', '-q', 'build',
        '-PmodVersion=%s' % ver, '-PneoVersion=%s' % LOCK['neoforge']['version'],
        cwd=ROOT / 'mod', env=env)

    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    built = sorted((ROOT / 'mod' / 'build' / 'libs').glob('*.jar'))
    built = [b for b in built if not b.name.endswith(('-sources.jar', '-dev.jar'))]
    if not built:
        sys.exit('❌ Gradle 没产出 jar')
    modjar = out / ('%s-%s.jar' % (MAN['id'], ver))
    shutil.copy2(built[-1], modjar)

    # **只发 jar**：一个 jar 装完就是全部汉化，不额外要资源包、不额外要脚本。
    # 做不到就别做——让玩家装两三样东西才凑齐一份汉化，那是半成品。
    selftest(modjar)
    print('\n✅ %s  (%.1f KB)' % (modjar.name, modjar.stat().st_size / 1024))
    print('   lang %d 条 / 导览书 %d 个文件《%s》/ 基因类型行 %d 个蜂种'
          % (stat['lang'], stat['book'], stat['book_name'], stat['types']))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
