#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ProductiveBees_zh-cn — 资源蜜蜂简体中文汉化
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
"""把 logo 原图的黑底抠掉、缩到出包用的尺寸。

原图是不透明的 RGB，底色纯黑。直接拿去当 `logoFile`，模组列表里就是一个黑方块。

**不能简单地"把黑色变透明"**：蜜蜂的轮廓、眼睛、蜜蜂身上的深色条纹本来就是黑的，
一刀切会把它们一起抠成洞。所以从**图像四边往里泛洪**，只抠与边框连通的那片黑——
被主体包住的黑保留。

缩放用盒式平均，并且**在预乘 alpha 的空间里做**：不预乘的话，边缘半透明像素会把
底下那圈纯黑平均进来，缩完一圈发灰。

纯标准库（只用 zlib），不引第三方依赖：这台机器上没有 Pillow，而为了一张图给构建
链加一个依赖不值得。

用法:
    python3 scripts/logo.py assets-src/logo-source.png src/logo.png [边长]
"""
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

# 底色是纯黑 (0,0,0)；主体外圈那层辉光最暗处是 (0,56,142)，亮度 49。
# 阈值必须卡在两者之间**并且贴着黑那一侧**：一旦够到辉光，泛洪就会顺着辉光
# 走进主体，再从蜜蜂那圈同样是纯黑的轮廓里穿出去，把轮廓和眼睛一起吃掉。
DARK = 10            # 亮度不超过这个数才算「底」
EDGE = 0             # 不给容差，见到有颜色就停


def read_png(path):
    """读 8 位、非隔行的 PNG，返回 (宽, 高, 每像素通道数, 像素字节串)。"""
    raw = Path(path).read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n':
        sys.exit('❌ %s 不是 PNG' % path)
    pos, idat, meta = 8, [], None
    while pos < len(raw):
        ln = struct.unpack('>I', raw[pos:pos + 4])[0]
        typ = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, depth, color, _comp, _filt, inter = struct.unpack('>IIBBBBB', body)
            if depth != 8 or inter != 0 or color not in (2, 6):
                sys.exit('❌ 只支持 8 位、非隔行的 RGB/RGBA，实得 depth=%d color=%d '
                         'interlace=%d' % (depth, color, inter))
            meta = (w, h, 3 if color == 2 else 4)
        elif typ == b'IDAT':
            idat.append(body)
        elif typ == b'IEND':
            break
        pos += 12 + ln
    w, h, ch = meta
    data = zlib.decompress(b''.join(idat))
    out = bytearray(w * h * ch)
    stride = w * ch
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = data[p]
        p += 1
        line = bytearray(data[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ft != 0:
            sys.exit('❌ 不认识的行过滤器 %d' % ft)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, ch, out


def write_png(path, w, h, rgba):
    """写 8 位 RGBA。逐行 filter 0——图不大，压缩率不值得为它写四种过滤器。"""
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(typ, body):
        return (struct.pack('>I', len(body)) + typ + body
                + struct.pack('>I', zlib.crc32(typ + body) & 0xFFFFFFFF))

    Path(path).write_bytes(
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
        + chunk(b'IEND', b''))


def cut_background(w, h, ch, px):
    """从四边泛洪，把与边框连通的暗色抠成透明；返回 RGBA 与抠掉的像素数。"""
    def lum(i):
        return (px[i * ch] * 299 + px[i * ch + 1] * 587 + px[i * ch + 2] * 114) // 1000

    bg = bytearray(w * h)
    q = deque()
    for x in range(w):
        for i in (x, (h - 1) * w + x):
            if not bg[i] and lum(i) <= DARK:
                bg[i] = 1
                q.append(i)
    for y in range(h):
        for i in (y * w, y * w + w - 1):
            if not bg[i] and lum(i) <= DARK:
                bg[i] = 1
                q.append(i)
    while q:
        i = q.popleft()
        y, x = divmod(i, w)
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w:
                j = ny * w + nx
                if not bg[j] and lum(j) <= DARK + EDGE:
                    bg[j] = 1
                    q.append(j)
    rgba = bytearray(w * h * 4)
    cut = 0
    for i in range(w * h):
        rgba[i * 4:i * 4 + 3] = px[i * ch:i * ch + 3]
        if bg[i]:
            rgba[i * 4 + 3] = 0
            cut += 1
        else:
            rgba[i * 4 + 3] = px[i * ch + 3] if ch == 4 else 255
    return rgba, cut


def box_resize(w, h, rgba, side):
    """盒式平均缩放。**在预乘 alpha 的空间里做**，否则边缘会把透明处的黑平均进来。"""
    out = bytearray(side * side * 4)
    for oy in range(side):
        y0, y1 = oy * h // side, max(oy * h // side + 1, (oy + 1) * h // side)
        for ox in range(side):
            x0, x1 = ox * w // side, max(ox * w // side + 1, (ox + 1) * w // side)
            r = g = b = a = n = 0
            for y in range(y0, y1):
                base = y * w
                for x in range(x0, x1):
                    i = (base + x) * 4
                    av = rgba[i + 3]
                    r += rgba[i] * av
                    g += rgba[i + 1] * av
                    b += rgba[i + 2] * av
                    a += av
                    n += 1
            o = (oy * side + ox) * 4
            if a:
                out[o] = min(255, r // a)
                out[o + 1] = min(255, g // a)
                out[o + 2] = min(255, b // a)
            out[o + 3] = a // n
    return out


def main(src, dst, side=512):
    w, h, ch, px = read_png(src)
    rgba, cut = cut_background(w, h, ch, px)
    print('原图 %dx%d（%d 通道），抠掉与边框连通的暗色 %d 像素（%.1f%%）'
          % (w, h, ch, cut, cut / (w * h) * 100))
    if side and side != w:
        rgba = box_resize(w, h, rgba, side)
        w = h = side
    write_png(dst, w, h, rgba)
    print('写出 %s：%dx%d RGBA，%.0f KB' % (dst, w, h, Path(dst).stat().st_size / 1024))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2],
         int(sys.argv[3]) if len(sys.argv) > 3 else 512)
