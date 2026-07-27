#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化（独立发布）
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""按 SOURCE.lock 把资源蜜蜂的独立汉化包打出来。

这个仓库**不存任何一份译文**。译文与生成器都在 atm10-zh-cn，按 commit 钉死。
两边各存一份的话必然漂移，最后同一只蜂在整合包里叫一个名、在这里叫另一个名。

干三件事，每一件都有字节锚点：

1. 取上游仓库到 `upstream/`（按 commit，不是分支——分支会动）
2. 取模组 jar 到 `build/mods/`（按 sha256 核；导览书的中文版是拿「原文 → 译文」
   映射现套到模组自带那份 JSON 上生成的，所以非有这个 jar 不可）
3. 跑上游的 `gen_standalone.py`，它自己会对着这个 jar 点名覆盖率，不到 100% 不出包

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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = json.loads((ROOT / 'SOURCE.lock').read_text(encoding='utf-8'))
UP = ROOT / 'upstream'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def run(*cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def fetch_source():
    """取上游仓库的那一个 commit。钉 commit 而不是分支：分支会动。"""
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
    """取模组 jar，逐字节核。下错版本当场失败，不是「凑合套一下」。"""
    m = LOCK['mod']
    mods = ROOT / 'build' / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    p = mods / m['name']
    if not p.is_file():
        url = ('https://www.curseforge.com/api/v1/mods/%d/files/%d/download'
               % (m['curseforge_project_id'], m['curseforge_file_id']))
        print('下载 %s …' % m['name'])
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
            final = urllib.parse.unquote(str(r.url).rsplit('/', 1)[-1].split('?')[0])
        if final != m['name']:
            sys.exit('❌ 跳转后的文件名是 %s，不是 %s——CurseForge 给错文件了'
                     % (final, m['name']))
        p.write_bytes(data)
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != m['sha256']:
        sys.exit('❌ %s 的 sha256 与 SOURCE.lock 对不上\n   记录 %s\n   实得 %s'
                 % (m['name'], m['sha256'], got))
    print('模组 jar 逐字节与 SOURCE.lock 一致 ✅')
    return mods


def main(ver):
    fetch_source()
    mods = fetch_mod()
    env = dict(os.environ, ATM_BUILD=str(ROOT / 'build' / 'atm'))
    run(sys.executable, 'scripts/assemble.py', cwd=UP, env=env)
    run(sys.executable, 'scripts/gen_standalone.py', 'productivebees',
        str(mods), ver, cwd=UP, env=env)
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    n = 0
    for f in sorted((UP / 'dist').glob('productivebees-zh_cn-%s*' % ver)):
        shutil.copy2(f, out / f.name)
        print('  → dist/%s  (%.1f KB)' % (f.name, f.stat().st_size / 1024))
        n += 1
    if not n:
        sys.exit('❌ 上游没产出任何包')
    print('✅ %d 个产物在 dist/' % n)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
