#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""起真的专用服务器，逐个加载器验「装上去会不会崩」。

这个 mod 从 1.0.1 起在服务端也会加载（蜂笼里的名字是捕捉那一刻由服务端烤进物品的，
客户端够不着）。**服务端崩是 P0**，而出包闸和客户端 e2e 都验不到它：那两样只证明
jar 编得出来、译名逻辑对。

四套加载器胶水各起一台——源码集是按事件类的包名分的，一套一台才算都走过一遍：

    1.21.1-neoforge  src/neoforge
    1.20.1-forge     src/forge
    1.18.2-forge     src/forge_old
    1.15.2-forge     src/forge_legacy

判据（照抄服务端汉化包 README 里那条）：**能正常启动、无报错**。
再加两条机械的：mod 列表里有我们、退出码为 0。

用法:
    python3 scripts/server_test.py dist/            # 目录里按平台找 jar
    python3 scripts/server_test.py dist/ 1.20.1-forge
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B                                          # noqa: E402
import e2e                                                 # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'build' / 'servertest'
UA = 'ProductiveBees_zh-cn server smoke test'
SETS = {                     # 目标 → 它验的是哪一套加载器胶水
    '1.21.1-neoforge': 'src/neoforge',
    '1.20.1-forge': 'src/forge',
    '1.18.2-forge': 'src/forge_old',
    '1.15.2-forge': 'src/forge_legacy',
}
NEO = ('https://maven.neoforged.net/releases/net/neoforged/neoforge/'
       '%(v)s/neoforge-%(v)s-installer.jar')
FORGE = ('https://maven.minecraftforge.net/net/minecraftforge/forge/'
         '%(v)s/forge-%(v)s-installer.jar')


def get(url, into):
    into.parent.mkdir(parents=True, exist_ok=True)
    if into.is_file() and into.stat().st_size > 0:
        return into
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=900) as r:
        into.write_bytes(r.read())
    return into


def loader_version(tag, t, lock):
    """加载器版本：新平台记在 targets.json，走 javac 那几版记在 deps.lock.json。"""
    if t.get('loader_version'):
        return t['loader_version']
    for f in lock.get('forge', []) if isinstance(lock.get('forge'), list) \
            else lock.get('forge', {}).values():
        if isinstance(f, dict) and f.get('version', '').startswith(t['minecraft'] + '-'):
            return f['version']
    raise SystemExit('❌ %s 找不到加载器版本' % tag)


def launch_cmd(home, java, tag):
    """新版本走 @unix_args.txt，1.16 及更早 installServer 出的是一个可直接跑的 jar。"""
    args = list(home.glob('libraries/**/unix_args.txt'))
    if args:
        return [str(java), '-Xmx2G', '@' + str(args[0].relative_to(home)), 'nogui']
    jars = [p for p in home.glob('forge-*.jar') if 'installer' not in p.name]
    if not jars:
        raise SystemExit('❌ %s installServer 之后既没有 unix_args.txt 也没有 forge jar' % tag)
    return [str(java), '-Xmx2G', '-jar', jars[0].name, 'nogui']


def server_classpath(home):
    """照服务端**自己那份清单**拼 classpath。

    别拿 `libraries/**/*.jar` 一股脑塞：那底下同时躺着安装器留下的 guava-20.0 和
    服务端真正用的 guava-32.1.2，按名字排序先拿到老的那个，起 Bootstrap 时就是
    `NoSuchMethodError: ImmutableList.toImmutableList()`——看着像 MC 坏了，
    其实是我拼错了 classpath。

    `unix_args.txt` 里的 `-DlegacyClassPath=` 就是服务端启动时用的那一份，
    照抄它，再补上 Minecraft 自己的 jar（那个不在这份清单里，由加载器另外挂）。
    """
    cp = []
    args = list(home.glob('libraries/**/unix_args.txt'))
    if args:
        for line in args[0].read_text(encoding='utf-8').splitlines():
            if line.startswith('-DlegacyClassPath='):
                cp = [home / x for x in line.split('=', 1)[1].split(':') if x]
                break
    cp += sorted(home.glob('libraries/net/minecraft/server/**/*.jar'))
    return [x for x in cp if x.is_file()]


def cage_check(home, java, modjar, tag):
    """蜂笼改名的**真机验证**：不用进服，也不用世界。

    这段平时只在「玩家背包每 100 tick 扫一次」里走到，没有客户端连进来就永远不
    触发。但它其实只是纯组件读写——把服务端自己的 classpath 拼出来、起原版
    Bootstrap，就能造真的 ItemStack 走真的 CUSTOM_DATA 读写。
    """
    src = ROOT / 'mod' / 'test' / 'server' / 'TestCage.java'
    if not src.is_file():
        return True, '没有测试源码'
    cp = os.pathsep.join([str(x) for x in server_classpath(home)] + [str(modjar)])
    out = home / 'cagetest'
    out.mkdir(exist_ok=True)
    javac = java.parent / 'javac'
    r = subprocess.run([str(javac), '-nowarn', '-cp', cp, '-d', str(out), str(src)],
                       capture_output=True, text=True, cwd=home)
    if r.returncode != 0:
        return False, '测试编不过：' + (r.stderr.strip().splitlines() or [''])[0][:160]
    r = subprocess.run([str(java), '-cp', os.pathsep.join([str(out), cp]),
                        'cn.hoshino.pbzh.TestCage'],
                       capture_output=True, text=True, cwd=home, timeout=300)
    for ln in r.stdout.splitlines():
        if ln.strip():
            print('     ' + ln)
    return r.returncode == 0, '蜂笼改名没过'


def one(tag, modjar, targets, lock):
    t = targets[tag]
    home = WORK / tag
    print('\n──── %s（%s / %s，验 %s）────'
          % (tag, t['minecraft'], t['loader'], SETS[tag]))
    lv = loader_version(tag, t, lock)
    url = (NEO if t['loader'] == 'NeoForge' else FORGE) % {'v': lv}
    inst = get(url, WORK / 'installers' / url.rsplit('/', 1)[-1])
    java = e2e.jdk(t['java'])
    if not home.is_dir():
        home.mkdir(parents=True)
        print('   装服务端（%s %s，Java %d）…' % (t['loader'], lv, t['java']))
        r = subprocess.run([str(java), '-jar', str(inst), '--installServer', str(home)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-1500:], r.stderr[-1500:])
            return tag, False, '装不上'
    mods = home / 'mods'
    mods.mkdir(exist_ok=True)
    B.fetch_jar(t, mods)                       # 上游那一版，逐字节核过
    (mods / modjar.name).write_bytes(modjar.read_bytes())
    (home / 'eula.txt').write_text('eula=true\n')
    (home / 'server.properties').write_text(
        'online-mode=false\nlevel-type=flat\nmax-tick-time=-1\n'
        'server-port=0\nsync-chunk-writes=false\n')

    cmd = launch_cmd(home, java, tag)
    print('   起服 …')
    p = subprocess.run(cmd, cwd=home, input='stop\n', capture_output=True,
                       text=True, timeout=900)
    log = p.stdout + p.stderr
    (home / 'smoke.log').write_text(log)
    ok, why = True, []
    if p.returncode != 0:
        ok, _ = False, why.append('退出码 %d' % p.returncode)
    if 'Done (' not in log:
        ok, _ = False, why.append('没跑到 Done')
    # 判据是**我们自己喊的那一声**，不是 mod 列表：Forge 启动时根本不打印 mod 列表，
    # NeoForge 才打印。靠列表判，Forge 那几台永远是「没装上」。
    if '[productivebees_zh_cn] 已加载' not in log:
        ok, _ = False, why.append('mod 没报到（没看到「已加载」那一行）')
    # 报错：只认致命的那种，模组自己的配方警告不算
    fatal = [ln for ln in log.splitlines()
             if re.search(r'(Failed to start|A potential crash|Exception in thread|'
                          r'ERROR.*productivebees_zh_cn|cn\.hoshino\.pbzh)', ln)]
    if fatal:
        ok, _ = False, why.append('日志里有我们的报错：%s' % fatal[0][:120])
    print('   %s %s' % ('✅ 正常启动、无报错' if ok else '❌ ' + '；'.join(why),
                        '' if ok else '（日志见 %s）' % (home / 'smoke.log')))
    # 起得来只是第一关。蜂笼那条路还要真验一次——它是这个 mod 唯一会写玩家数据的地方
    if ok and tag == '1.21.1-neoforge':
        print('   验蜂笼改名（不进服，直接在服务端 classpath 上跑）…')
        cok, cwhy = cage_check(home, java, modjar, tag)
        if not cok:
            ok = False
            why.append(cwhy)
    return tag, ok, '；'.join(why)


def main(argv):
    # **必须取绝对路径**：下面 javac / java 是在服务端目录里跑的，相对路径
    # 指不到 jar，而 javac 对找不到的 classpath 项不报错——只会在后面
    # 报「找不到符号」，看着像代码错，其实是路径错。
    dist = (Path(argv[0]) if argv else ROOT / 'dist').resolve()
    only = argv[1] if len(argv) > 1 else None
    targets = json.loads((ROOT / 'versions' / 'targets.json').read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'deps.lock.json').read_text(encoding='utf-8'))
    rows = []
    for tag in SETS:
        if only and tag != only:
            continue
        cand = sorted(dist.rglob('*%s.jar' % tag)) or \
            sorted(dist.rglob('*mc%s-%s.jar' % (targets[tag]['minecraft'],
                                                targets[tag]['loader'].lower())))
        if not cand:
            print('❌ %s：在 %s 里找不到 jar' % (tag, dist))
            rows.append((tag, False, '没有 jar'))
            continue
        rows.append(one(tag, cand[0], targets, lock))
    print('\n' + '─' * 52)
    for tag, ok, why in rows:
        print('%-18s %-12s %s' % (tag, SETS[tag].split('/')[-1],
                                  '✅' if ok else '❌ ' + why))
    if any(not ok for _, ok, _ in rows):
        sys.exit(1)
    print('四套加载器胶水的服务端都能正常起')


if __name__ == '__main__':
    main(sys.argv[1:])
