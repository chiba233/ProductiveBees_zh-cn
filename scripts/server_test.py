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
    if 'productivebees_zh_cn' not in log:
        ok, _ = False, why.append('mod 列表里没有我们')
    # 报错：只认致命的那种，模组自己的配方警告不算
    fatal = [ln for ln in log.splitlines()
             if re.search(r'(Failed to start|A potential crash|Exception in thread|'
                          r'ERROR.*productivebees_zh_cn|cn\.hoshino\.pbzh)', ln)]
    if fatal:
        ok, _ = False, why.append('日志里有我们的报错：%s' % fatal[0][:120])
    print('   %s %s' % ('✅ 正常启动、无报错' if ok else '❌ ' + '；'.join(why),
                        '' if ok else '（日志见 %s）' % (home / 'smoke.log')))
    return tag, ok, '；'.join(why)


def main(argv):
    dist = Path(argv[0]) if argv else ROOT / 'dist'
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
