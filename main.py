#!/usr/bin/env python3
"""The Meridian - Tuesday, 24 November 2026.

Draws a dense, illustrated newspaper front page summing up the world
news of Tuesday 24 November 2026 and writes it to /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png).  Pure Python 3 standard library:
the page is rendered pixel by pixel with a built-in bitmap typeface
and hand-drawn pictograms, then encoded as an indexed-colour PNG.
The output is fully deterministic: same bytes on every run.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import struct
import zlib

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 231)
INK = (24, 22, 18)
RED = (176, 32, 30)
BLUE = (28, 66, 138)
SKY = (168, 205, 232)
SEA = (46, 110, 164)
GOLD = (196, 148, 32)
TEAL = (24, 128, 116)
GREEN = (52, 128, 52)
GREY = (110, 106, 98)
LIGHT = (238, 232, 214)
WHITE = (255, 255, 255)
BROWN = (140, 96, 48)
ORANGE = (224, 122, 32)
PURPLE = (104, 60, 148)
PINK = (216, 120, 150)
DARKBLUE = (16, 40, 84)

PALETTE = [PAPER, INK, RED, BLUE, SKY, SEA, GOLD, TEAL, GREEN, GREY,
           LIGHT, WHITE, BROWN, ORANGE, PURPLE, PINK, DARKBLUE]
CIDX = {c: i for i, c in enumerate(PALETTE)}


def ci(colour):
    return CIDX[colour]


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = [bytearray([CIDX[bg]]) * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x, y, w, h, colour):
        c = ci(colour)
        x0, x1 = max(0, x), min(self.w, x + w)
        y0, y1 = max(0, y), min(self.h, y + h)
        for yy in range(y0, y1):
            row = self.px[yy]
            for xx in range(x0, x1):
                row[xx] = c

    def hline(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.rect(x, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        c = ci(colour)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = thick // 2
        while True:
            for yy in range(y0 - r, y0 - r + thick):
                for xx in range(x0 - r, x0 - r + thick):
                    if 0 <= xx < self.w and 0 <= yy < self.h:
                        self.px[yy][xx] = c
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, colour, fill=True):
        c = ci(colour)
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if fill:
                    inside = d2 <= r * r
                else:
                    inside = (r - 1) * (r - 1) < d2 <= r * r
                if inside and 0 <= xx < self.w and 0 <= yy < self.h:
                    self.px[yy][xx] = c

    def ellipse(self, cx, cy, rx, ry, colour):
        c = ci(colour)
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                v = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
                if v <= 1.0 and 0 <= xx < self.w and 0 <= yy < self.h:
                    self.px[yy][xx] = c

    def poly(self, pts, colour):
        c = ci(colour)
        ys = [p[1] for p in pts]
        for yy in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    nodes.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                xa, xb = int(nodes[i]), int(nodes[i + 1])
                for xx in range(max(0, xa), min(self.w, xb + 1)):
                    if 0 <= yy < self.h:
                        self.px[yy][xx] = c


# ---------------------------------------------------------------- typeface
# 5x7 bitmap glyphs.  Lowercase letters are set as small capitals, in the
# manner of a newspaper nameplate.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': (".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    '%': ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#.##."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '*': (".....", "#.#.#", ".###.", "#.#.#", ".....", ".....", "....."),
}


def text_width(s, scale, spacing=1):
    if not s:
        return 0
    return len(s) * (5 + spacing) * scale - spacing * scale


def draw_text(cv, x, y, s, scale, colour, bold=False, spacing=1):
    c = ci(colour)
    cx = x
    for ch in s.upper():
        glyph = FONT.get(ch, FONT[' '])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == '#':
                    px = cx + gx * scale
                    py = y + gy * scale
                    wdt = scale + (1 if bold else 0)
                    for yy in range(py, py + scale):
                        for xx in range(px, px + wdt):
                            if 0 <= xx < cv.w and 0 <= yy < cv.h:
                                cv.px[yy][xx] = c
        cx += (5 + spacing) * scale
    return cx


def draw_text_centered(cv, cx, y, s, scale, colour, bold=False, spacing=1):
    w = text_width(s, scale, spacing)
    return draw_text(cv, cx - w // 2, y, s, scale, colour, bold, spacing)


def wrap(s, maxchars):
    words = s.split()
    lines = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= maxchars:
            cur = cur + " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- pictograms
# Each icon draws inside the box (x, y, s, s) in its own colours.

def icon_ship(cv, x, y, s):
    cv.rect(x, y + int(s * 0.62), s, int(s * 0.38), SEA)
    for i in range(3):
        cv.hline(x + i * 5, y + int(s * 0.70) + i * 4, 8, SKY, 2)
    cv.poly([(x + 6, y + int(s * 0.60)), (x + s - 4, y + int(s * 0.60)),
             (x + s - 12, y + int(s * 0.76)), (x + 12, y + int(s * 0.76))], INK)
    cv.rect(x + int(s * 0.42), y + int(s * 0.30), 3, int(s * 0.30), INK)
    cv.poly([(x + int(s * 0.46), y + int(s * 0.30)),
             (x + int(s * 0.46), y + int(s * 0.58)),
             (x + int(s * 0.78), y + int(s * 0.58))], RED)
    cv.rect(x + int(s * 0.18), y + int(s * 0.48), int(s * 0.5), 5, GREY)


def icon_globe(cv, x, y, s):
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 2
    cv.circle(cx, cy, r, BLUE)
    cv.ellipse(cx, cy, r // 2, r, TEAL)
    cv.hline(cx - r, cy, 2 * r, TEAL, 2)
    cv.hline(cx - r, cy - r // 2, 2 * r, TEAL, 1)
    cv.hline(cx - r, cy + r // 2, 2 * r, TEAL, 1)


def icon_flame(cv, x, y, s):
    cx = x + s // 2
    cv.poly([(cx, y + 2), (x + s - 6, y + int(s * 0.62)),
             (x + s - 12, y + s - 2), (x + 12, y + s - 2),
             (x + 6, y + int(s * 0.62))], ORANGE)
    cv.poly([(cx, y + int(s * 0.34)), (x + int(s * 0.68), y + int(s * 0.72)),
             (x + int(s * 0.62), y + s - 2), (x + int(s * 0.38), y + s - 2),
             (x + int(s * 0.32), y + int(s * 0.72))], GOLD)


def icon_burst(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1),
                   (-1, 0), (-1, -1)):
        cv.line(cx, cy, cx + dx * (s // 2 - 2), cy + dy * (s // 2 - 2),
                ORANGE, 3)
    cv.circle(cx, cy, 5, RED)


def icon_bubble(cv, x, y, s):
    cv.rect(x + 3, y + 4, s - 6, int(s * 0.58), BLUE)
    cv.poly([(x + 10, y + int(s * 0.62)), (x + 20, y + int(s * 0.62)),
             (x + 10, y + s - 3)], BLUE)
    for i in range(3):
        cv.hline(x + 9, y + 12 + i * 7, s - 18, WHITE, 3)


def icon_chart(cv, x, y, s):
    cv.vline(x + 5, y + 3, s - 6, INK, 2)
    cv.hline(x + 5, y + s - 5, s - 8, INK, 2)
    pts = [(x + 8, y + s - 12), (x + int(s * 0.38), y + int(s * 0.55)),
           (x + int(s * 0.58), y + int(s * 0.66)), (x + s - 6, y + 8)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], TEAL, 3)


def icon_plane(cv, x, y, s):
    cv.poly([(x + 2, y + int(s * 0.55)), (x + s - 3, y + int(s * 0.30)),
             (x + s - 3, y + int(s * 0.42)), (x + 2, y + int(s * 0.66))], GREY)
    cv.poly([(x + int(s * 0.42), y + int(s * 0.44)),
             (x + int(s * 0.62), y + int(s * 0.10)),
             (x + int(s * 0.72), y + int(s * 0.10)),
             (x + int(s * 0.62), y + int(s * 0.48))], BLUE)
    cv.poly([(x + int(s * 0.42), y + int(s * 0.60)),
             (x + int(s * 0.60), y + s - 3),
             (x + int(s * 0.70), y + s - 3),
             (x + int(s * 0.60), y + int(s * 0.58))], BLUE)
    cv.poly([(x + 2, y + int(s * 0.55)), (x + 9, y + int(s * 0.34)),
             (x + 13, y + int(s * 0.36)), (x + 8, y + int(s * 0.62))], RED)


def icon_cross(cv, x, y, s):
    cv.circle(x + s // 2, y + s // 2, s // 2 - 2, WHITE)
    cv.circle(x + s // 2, y + s // 2, s // 2 - 2, RED, fill=False)
    cv.rect(x + s // 2 - 3, y + 10, 7, s - 20, RED)
    cv.rect(x + 10, y + s // 2 - 3, s - 20, 7, RED)


def icon_bank(cv, x, y, s):
    cv.poly([(x + 3, y + int(s * 0.30)), (x + s // 2, y + 4),
             (x + s - 3, y + int(s * 0.30))], GOLD)
    for i in range(4):
        cv.rect(x + 7 + i * int(s * 0.22), y + int(s * 0.36), 5,
                int(s * 0.42), GOLD)
    cv.rect(x + 3, y + int(s * 0.82), s - 6, 4, GOLD)


def icon_factory(cv, x, y, s):
    cv.rect(x + 3, y + int(s * 0.52), s - 6, int(s * 0.44), GREY)
    cv.rect(x + 8, y + int(s * 0.24), 7, int(s * 0.30), GREY)
    cv.rect(x + 20, y + int(s * 0.16), 7, int(s * 0.38), GREY)
    cv.circle(x + 24, y + 8, 5, LIGHT)
    cv.circle(x + 33, y + 5, 6, LIGHT)
    cv.circle(x + 13, y + 12, 4, LIGHT)


def icon_rain(cv, x, y, s):
    cv.ellipse(x + int(s * 0.38), y + int(s * 0.34), int(s * 0.26),
               int(s * 0.17), GREY)
    cv.ellipse(x + int(s * 0.62), y + int(s * 0.30), int(s * 0.24),
               int(s * 0.19), GREY)
    for i in range(3):
        bx = x + 10 + i * int(s * 0.26)
        cv.line(bx, y + int(s * 0.60), bx - 4, y + s - 4, SEA, 3)


def icon_bird(cv, x, y, s):
    cv.ellipse(x + int(s * 0.44), y + int(s * 0.56), int(s * 0.30),
               int(s * 0.20), TEAL)
    cv.circle(x + int(s * 0.72), y + int(s * 0.38), 7, TEAL)
    cv.poly([(x + int(s * 0.78), y + int(s * 0.38)),
             (x + s - 1, y + int(s * 0.44)),
             (x + int(s * 0.76), y + int(s * 0.46))], GOLD)
    cv.poly([(x + int(s * 0.30), y + int(s * 0.50)),
             (x + int(s * 0.52), y + int(s * 0.22)),
             (x + int(s * 0.58), y + int(s * 0.48))], BLUE)
    cv.set(x + int(s * 0.74), y + int(s * 0.36), ci(INK))


def icon_mountain(cv, x, y, s):
    cv.poly([(x + 2, y + s - 3), (x + int(s * 0.38), y + 8),
             (x + int(s * 0.66), y + s - 3)], GREY)
    cv.poly([(x + int(s * 0.40), y + s - 3), (x + int(s * 0.72), y + 3),
             (x + s - 2, y + s - 3)], INK)
    cv.poly([(x + int(s * 0.65), y + 10), (x + int(s * 0.72), y + 3),
             (x + int(s * 0.79), y + 10), (x + int(s * 0.72), y + 14)],
            WHITE)
    for i in range(3):
        cv.line(x + 10 + i * 9, y + int(s * 0.66), x + 6 + i * 9,
                y + s - 6, SEA, 2)


def icon_capitol(cv, x, y, s):
    cx = x + s // 2
    cv.ellipse(cx, y + int(s * 0.36), int(s * 0.30), int(s * 0.20), BLUE)
    cv.rect(cx - 2, y + 4, 4, 8, BLUE)
    cv.rect(x + 6, y + int(s * 0.40), s - 12, 4, BLUE)
    for i in range(4):
        cv.rect(x + 9 + i * int(s * 0.21), y + int(s * 0.48), 4,
                int(s * 0.34), GREY)
    cv.rect(x + 4, y + int(s * 0.86), s - 8, 4, INK)


def icon_chip(cv, x, y, s):
    m = int(s * 0.22)
    cv.rect(x + m, y + m, s - 2 * m, s - 2 * m, INK)
    cv.rect(x + m + 6, y + m + 6, s - 2 * m - 12, s - 2 * m - 12, TEAL)
    for i in range(3):
        px = x + m + 4 + i * int(s * 0.19)
        cv.rect(px, y + 2, 4, m - 2, GOLD)
        cv.rect(px, y + s - m, 4, m - 2, GOLD)
        cv.rect(x + 2, y + m + 4 + i * int(s * 0.19), m - 2, 4, GOLD)
        cv.rect(x + s - m, y + m + 4 + i * int(s * 0.19), m - 2, 4, GOLD)


def icon_gear(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    for i in range(8):
        import math
        a = i * math.pi / 4
        tx, ty = cx + int(15 * math.cos(a)), cy + int(15 * math.sin(a))
        cv.rect(tx - 3, ty - 3, 7, 7, GREY)
    cv.circle(cx, cy, 13, GREY)
    cv.circle(cx, cy, 6, PAPER)


def icon_scroll(cv, x, y, s):
    cv.rect(x + 8, y + 6, s - 16, s - 12, WHITE)
    cv.hline(x + 8, y + 6, s - 16, INK, 2)
    cv.hline(x + 8, y + s - 8, s - 16, INK, 2)
    cv.circle(x + 8, y + s // 2, 6, BROWN)
    cv.circle(x + s - 8, y + s // 2, 6, BROWN)
    for i in range(3):
        cv.hline(x + 14, y + 13 + i * 8, s - 28, GREY, 2)


def icon_ballot(cv, x, y, s):
    cv.rect(x + 6, y + int(s * 0.36), s - 12, int(s * 0.56), BLUE)
    cv.hline(x + 12, y + int(s * 0.46), s - 24, INK, 3)
    cv.rect(x + int(s * 0.34), y + 4, int(s * 0.32), int(s * 0.36), WHITE)
    cv.line(x + int(s * 0.40), y + int(s * 0.24), x + int(s * 0.47),
            y + int(s * 0.31), GREEN, 3)
    cv.line(x + int(s * 0.47), y + int(s * 0.31), x + int(s * 0.60),
            y + int(s * 0.12), GREEN, 3)


def icon_flask(cv, x, y, s):
    cv.rect(x + int(s * 0.42), y + 3, int(s * 0.16), int(s * 0.24), TEAL)
    cv.poly([(x + int(s * 0.42), y + int(s * 0.27)),
             (x + int(s * 0.58), y + int(s * 0.27)),
             (x + int(s * 0.82), y + s - 4), (x + int(s * 0.18), y + s - 4)],
            TEAL)
    cv.poly([(x + int(s * 0.34), y + int(s * 0.62)),
             (x + int(s * 0.66), y + int(s * 0.62)),
             (x + int(s * 0.78), y + s - 5), (x + int(s * 0.22), y + s - 5)],
            GREEN)


def icon_syringe(cv, x, y, s):
    cv.line(x + 10, y + s - 10, x + int(s * 0.62), y + int(s * 0.38),
            BLUE, 7)
    cv.line(x + int(s * 0.62), y + int(s * 0.38), x + s - 4, y + 6, GREY, 2)
    cv.line(x + int(s * 0.66), y + int(s * 0.30), x + int(s * 0.76),
            y + int(s * 0.40), INK, 3)
    cv.line(x + int(s * 0.24), y + int(s * 0.62), x + int(s * 0.34),
            y + int(s * 0.72), INK, 3)
    cv.rect(x + 4, y + s - 14, 10, 4, INK)


def icon_gavel(cv, x, y, s):
    cv.line(x + int(s * 0.30), y + int(s * 0.62), x + s - 6, y + 6, BROWN, 5)
    cv.line(x + int(s * 0.52), y + int(s * 0.16), x + int(s * 0.78),
            y + int(s * 0.42), BROWN, 9)
    cv.hline(x + 8, y + s - 8, s - 16, INK, 4)


def icon_rocket(cv, x, y, s):
    cx = x + s // 2
    cv.ellipse(cx, y + int(s * 0.40), 9, int(s * 0.30), GREY)
    cv.poly([(cx - 9, y + int(s * 0.58)), (cx - 17, y + int(s * 0.82)),
             (cx - 4, y + int(s * 0.78))], RED)
    cv.poly([(cx + 9, y + int(s * 0.58)), (cx + 17, y + int(s * 0.82)),
             (cx + 4, y + int(s * 0.78))], RED)
    cv.circle(cx, y + int(s * 0.32), 4, SKY)
    cv.poly([(cx - 4, y + int(s * 0.80)), (cx + 4, y + int(s * 0.80)),
             (cx, y + s - 2)], ORANGE)


def icon_asteroid(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    cv.circle(cx, cy, s // 2 - 3, BROWN)
    cv.circle(cx - 7, cy - 5, 5, GREY)
    cv.circle(cx + 8, cy + 7, 4, GREY)
    cv.circle(cx + 9, cy - 10, 3, GREY)
    cv.circle(x + int(s * 0.80), y + int(s * 0.72), 8, ORANGE)
    cv.circle(x + int(s * 0.80), y + int(s * 0.72), 4, GOLD)


def icon_planet(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    cv.ellipse(cx, cy, int(s * 0.44), 7, GOLD)
    cv.circle(cx, cy, int(s * 0.30), PURPLE)
    cv.ellipse(cx, cy, int(s * 0.44), 7, GOLD)
    cv.circle(cx - 6, cy - 6, 4, PINK)


def icon_star(cv, x, y, s):
    cx, cy = x + s // 2, y + s // 2
    cv.poly([(cx, y + 2), (cx + 4, cy - 4), (x + s - 2, cy),
             (cx + 4, cy + 4), (cx, y + s - 2), (cx - 4, cy + 4),
             (x + 2, cy), (cx - 4, cy - 4)], GOLD)


def icon_ball(cv, x, y, s):
    cx, cy, r = x + s // 2, y + s // 2, s // 2 - 2
    cv.circle(cx, cy, r, WHITE)
    cv.circle(cx, cy, r, INK, fill=False)
    cv.circle(cx, cy, 6, INK)
    for dx, dy in ((0, -13), (12, -4), (8, 11), (-8, 11), (-12, -4)):
        cv.circle(cx + dx, cy + dy, 4, INK)


def icon_trophy(cv, x, y, s):
    cv.poly([(x + 10, y + 4), (x + s - 10, y + 4), (x + s - 13, y + int(s * 0.52)),
             (x + 13, y + int(s * 0.52))], GOLD)
    cv.poly([(x + 10, y + 8), (x + 2, y + 10), (x + 4, y + int(s * 0.40)),
             (x + 12, y + int(s * 0.36))], GOLD)
    cv.poly([(x + s - 10, y + 8), (x + s - 2, y + 10),
             (x + s - 4, y + int(s * 0.40)), (x + s - 12, y + int(s * 0.36))],
            GOLD)
    cv.rect(x + s // 2 - 3, y + int(s * 0.52), 7, int(s * 0.22), GOLD)
    cv.rect(x + int(s * 0.28), y + int(s * 0.78), int(s * 0.44), 6, BROWN)


def icon_oval(cv, x, y, s):
    cv.ellipse(x + s // 2, y + s // 2, int(s * 0.30), int(s * 0.44), BROWN)
    cv.vline(x + s // 2 - 1, y + int(s * 0.36), int(s * 0.28), WHITE, 3)
    for i in range(3):
        cv.hline(x + s // 2 - 4, y + int(s * 0.42) + i * 5, 8, WHITE, 2)


def icon_music(cv, x, y, s):
    cv.rect(x + int(s * 0.58), y + 6, 4, int(s * 0.56), PURPLE)
    cv.poly([(x + int(s * 0.58), y + 6), (x + s - 4, y + 11),
             (x + s - 4, y + 20), (x + int(s * 0.58), y + 15)], PURPLE)
    cv.ellipse(x + int(s * 0.46), y + int(s * 0.68), 8, 6, PURPLE)
    cv.ellipse(x + int(s * 0.24), y + int(s * 0.78), 7, 5, PINK)


def icon_mic(cv, x, y, s):
    cx = x + s // 2
    cv.rect(cx - 6, y + 3, 12, int(s * 0.44), GREY)
    cv.circle(cx, y + int(s * 0.50), 13, INK, fill=False)
    cv.vline(cx - 1, y + int(s * 0.64), int(s * 0.20), INK, 3)
    cv.hline(cx - 9, y + s - 5, 18, INK, 3)


def icon_scales(cv, x, y, s):
    cx = x + s // 2
    cv.vline(cx - 1, y + 6, int(s * 0.66), INK, 3)
    cv.hline(x + 7, y + 10, s - 14, INK, 3)
    for bx in (x + 11, x + s - 11):
        cv.line(bx, y + 10, bx - 6, y + int(s * 0.52), INK, 2)
        cv.line(bx, y + 10, bx + 6, y + int(s * 0.52), INK, 2)
        cv.ellipse(bx, y + int(s * 0.56), 9, 4, GOLD)
    cv.rect(x + int(s * 0.30), y + int(s * 0.76), int(s * 0.40), 5, INK)


ICONS = {
    'ship': icon_ship, 'globe': icon_globe, 'flame': icon_flame,
    'burst': icon_burst, 'bubble': icon_bubble, 'chart': icon_chart,
    'plane': icon_plane, 'cross': icon_cross, 'bank': icon_bank,
    'factory': icon_factory, 'rain': icon_rain, 'bird': icon_bird,
    'mountain': icon_mountain, 'capitol': icon_capitol, 'chip': icon_chip,
    'gear': icon_gear, 'scroll': icon_scroll, 'ballot': icon_ballot,
    'flask': icon_flask, 'syringe': icon_syringe, 'gavel': icon_gavel,
    'rocket': icon_rocket, 'asteroid': icon_asteroid, 'planet': icon_planet,
    'star': icon_star, 'ball': icon_ball, 'trophy': icon_trophy,
    'oval': icon_oval, 'music': icon_music, 'mic': icon_mic,
    'scales': icon_scales,
}

# ---------------------------------------------------------------- the news
# Every story below happened, or was first reported, on Tuesday
# 24 November 2026.  Headlines are kept short and factual.

LEAD_HEAD = "UKRAINE SAYS ITS DRONES SANK A RUSSIAN WARSHIP OFF LIBYA"
LEAD_DEK = ("ZELENSKYY ANNOUNCES THE STRIKE FAR FROM THE FRONT "
            "LINE. THE UN WARNS LIBYA MUST NOT BECOME A "
            "BATTLEGROUND FOR FOREIGN POWERS.")

SECTIONS_A = [
    ("WORLD & WAR", RED, [
        ('globe', "UN: LIBYA MUST NOT BECOME A FOREIGN BATTLEGROUND"),
        ('scales', "EASTERN LIBYA SEEKS UN PROBE OF UKRAINIAN TROOPS"),
        ('flame', "DRONE DEBRIS SETS FIRE IN CENTRAL KYIV, 3 HURT"),
        ('burst', "MERZ WARNS KREMLIN AFTER MISSILES LAND IN POLAND"),
        ('bubble', "ZELENSKYY URGES EU TO JOIN RUSSIA TALKS SOON"),
        ('chart', "REPORT: RUSSIAN WAR DEATHS LIKELY NEAR 700,000"),
        ('plane', "SEOUL SCRAMBLES JETS AFTER RUSSIAN AIR BREACH"),
    ]),
    ("MIDDLE EAST", TEAL, [
        ('cross', "ISRAELI AIRSTRIKE KILLS UN STAFF MEMBER IN GAZA"),
        ('burst', "ISRAELI DRONE STRIKE KILLS 3 AT GAZA POLICE POST"),
        ('cross', "REPORT DETAILS COLLAPSE OF GAZA'S HEALTH SECTOR"),
        ('bank', "US SANCTIONS TARGET IRAN'S SHADOW BANKING NETWORK"),
    ]),
    ("SCIENCE & SPACE", PURPLE, [
        ('rocket', "CHINA TO LAUNCH SHENZHOU-24 WITH FIRST FOREIGN ASTRONAUT"),
        ('asteroid', "ESA'S HERA SENDS FIRST THERMAL VIEWS OF BINARY ASTEROID"),
        ('planet', "DWARF PLANET CANDIDATE FOUND ON A 281-YEAR ORBIT"),
        ('star', "ALMA IMAGES SHOW RED GIANT MIRA'S RECORD ERUPTION"),
    ]),
]

SECTIONS_B = [
    ("POLITICS", BLUE, [
        ('capitol', "REP. GOMEZ TO QUIT CONGRESS AFTER ETHICS REPORT"),
        ('chip', "TRUMP TAKES CREDIT FOR HUANG'S RETURN AS NVIDIA CEO"),
        ('scales', "US LAWMAKERS UNITE TO PRESS FOR CHINA CHIP CONTROLS"),
        ('gear', "UN CHIEF: AGREE GLOBAL AI RULES WITHIN ONE YEAR"),
        ('globe', "AUSTRALIA MAKES AI A CORE FOREIGN POLICY ISSUE"),
        ('plane', "ICE ARRESTS AT SEATTLE AIRPORT SPARK OUTRAGE"),
        ('plane', "FAA LIFTS O'HARE GROUND STOP AFTER STAFFING SNARL"),
        ('scroll', "ARMENIA DRAFTS NEW CONSTITUTION TO REOPEN TURKEY BORDER"),
        ('ballot', "MOLDOVA POLL: PUBLIC BACKS CLOSER EU INTEGRATION"),
    ]),
    ("CLIMATE & DISASTERS", GREEN, [
        ('factory', "COP31 CLIMATE TALKS END WITHOUT AN AGREEMENT"),
        ('rain', "DEADLY STORM DISPLACES THOUSANDS IN BRAZIL TOWN"),
        ('bird', "FRANCE CONFIRMS FATAL BIRD FLU AT A POULTRY FARM"),
        ('mountain', "ARMY SEARCHES FOR SCORES MISSING AFTER HIMALAYAN FLOOD"),
    ]),
    ("AMERICAS", BROWN, [
        ('gavel', "MEXICO TO TRY 'EL CHAPO ISIDRO' DESPITE US BID"),
        ('flask', "US SAYS CHINA SUPPLIED METH INGREDIENTS TO CARTELS"),
    ]),
]

SECTIONS_C = [
    ("ASIA & HEALTH", ORANGE, [
        ('syringe', "BANGLADESH BEGINS TYPHOID VACCINATION OF 50M CHILDREN"),
        ('gavel', "INDIA EX-MP REVANNA SENTENCED TO LIFE FOR RAPE"),
        ('ship', "SEOUL SEEKS PRIORITY QATAR LNG AS HORMUZ SHIPPING NORMALISES"),
    ]),
    ("BUSINESS & TECH", DARKBLUE, [
        ('chart', "SK HYNIX SHARES LEAP 20% AFTER HUANG'S NVIDIA RETURN"),
        ('chip', "SOFTBANK TO INVEST $2 BILLION IN INTEL"),
    ]),
    ("SPORT", GREEN, [
        ('ball', "PREMIER LEAGUE: BRENTFORD ROUT 10-MAN EVERTON 4-0"),
        ('ball', "SERIE A: MONZA STUN FIORENTINA 3-0; LEVANTE 1-1 ELCHE"),
        ('trophy', "U-17 WORLD CUP: SPAIN BEAT FIJI 15-0, SENEGAL 9-0 CUBA"),
        ('trophy', "CHAMPIONS LEAGUE: ARSENAL-DORTMUND, MAN CITY-NAPOLI"),
        ('ball', "DAVIS CUP FINAL 8 OPENS IN BOLOGNA: CZECHIA V CANADA"),
        ('oval', "NFL: COMMANDERS EDGE BENGALS 22-20 ON MONDAY NIGHT"),
        ('trophy', "ALCARAZ BEATS ZVEREV TO WIN THE ATP FINALS"),
    ]),
    ("CULTURE", PINK, [
        ('music', "CHEMICAL SCARE EMPTIES DON TOLIVER CONCERT CROWD"),
        ('mic', "COMEDIAN SKEWERS TRUMP AT TORONTO JOURNALISTS' DINNER"),
    ]),
]

# ---------------------------------------------------------------- layout
W, H = 1024, 1024
MARGIN = 16
COLW = (W - 2 * MARGIN - 2 * 12) // 3
ICONBOX = 30
HEAD_SCALE = 2
HEAD_CHARS = (COLW - ICONBOX - 8) // (5 * HEAD_SCALE)


def draw_lead_art(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    cv.circle(x + w - 52, y + 34, 20, GOLD)
    cv.rect(x, y + int(h * 0.58), w, int(h * 0.42), SEA)
    for i in range(6):
        cv.hline(x + 12 + (i % 3) * 40, y + int(h * 0.66) + i * 9, 26, SKY, 3)
    # warship
    bx, by = x + 52, y + int(h * 0.52)
    cv.poly([(bx, by), (bx + 190, by), (bx + 168, by + 22), (bx + 18, by + 22)],
            INK)
    cv.rect(bx + 30, by - 16, 90, 16, GREY)
    cv.rect(bx + 120, by - 30, 14, 30, GREY)
    cv.rect(bx + 56, by - 26, 30, 10, INK)
    cv.line(bx + 150, by - 28, bx + 196, by - 40, INK, 3)
    # drone overhead
    dx, dy = x + 96, y + 30
    cv.rect(dx - 16, dy - 4, 32, 8, INK)
    cv.line(dx - 30, dy - 12, dx + 30, dy + 12, INK, 3)
    cv.line(dx - 30, dy + 12, dx + 30, dy - 12, INK, 3)
    for px, py in ((dx - 30, dy - 12), (dx + 30, dy + 12), (dx - 30, dy + 12),
                   (dx + 30, dy - 12)):
        cv.circle(px, py, 5, INK, fill=False)
    # splash where the strike lands
    for i in range(5):
        cv.line(bx + 176 + i * 3, by + 20, bx + 186 + i * 5, by - 8 - i * 3,
                WHITE, 2)


def draw_story(cv, x, y, icon, head):
    cv.rect(x, y, ICONBOX, ICONBOX, LIGHT)
    ICONS[icon](cv, x + 2, y + 2, ICONBOX - 4)
    lines = wrap(head, HEAD_CHARS)
    ty = y + 1
    for ln in lines[:3]:
        draw_text(cv, x + ICONBOX + 8, ty, ln, HEAD_SCALE, INK, bold=True,
                  spacing=0)
        ty += 15
    return max(ICONBOX, ty - y - 15 + 14) + 3


def draw_section(cv, x, y, title, colour, stories):
    cv.rect(x, y, COLW, 22, colour)
    draw_text(cv, x + 8, y + 4, title, 2, WHITE, bold=True)
    y += 27
    for icon, head in stories:
        y += draw_story(cv, x, y, icon, head)
    return y


def draw_page():
    cv = Canvas(W, H, PAPER)
    # masthead
    cv.hline(MARGIN, 10, W - 2 * MARGIN, INK, 3)
    draw_text_centered(cv, W // 2, 20, "THE MERIDIAN", 11, INK, bold=True)
    cv.hline(MARGIN, 104, W - 2 * MARGIN, RED, 4)
    draw_text_centered(cv, W // 2, 114, "TUESDAY, 24 NOVEMBER 2026", 4,
                       RED, bold=True)
    draw_text_centered(cv, W // 2, 150,
                       "THE WORLD'S NEWS OF THE DAY, ON ONE PAGE", 2, GREY)
    cv.hline(MARGIN, 172, W - 2 * MARGIN, INK, 2)
    # lead story
    ly = 180
    draw_lead_art(cv, MARGIN, ly, 400, 150)
    lx = MARGIN + 416
    draw_text(cv, lx, ly, "TOP STORY", 2, RED, bold=True)
    ty = ly + 24
    for ln in wrap(LEAD_HEAD, 30):
        draw_text(cv, lx, ty, ln, 3, INK, bold=True)
        ty += 27
    ty += 6
    for ln in wrap(LEAD_DEK, 48):
        draw_text(cv, lx, ty, ln, 2, INK)
        ty += 19
    cv.hline(MARGIN, 344, W - 2 * MARGIN, INK, 2)
    # three columns of sections
    tops = 354
    for ci_, sections in enumerate((SECTIONS_A, SECTIONS_B, SECTIONS_C)):
        x = MARGIN + ci_ * (COLW + 12)
        y = tops
        for title, colour, stories in sections:
            y = draw_section(cv, x, y, title, colour, stories) + 8
    # footer
    cv.hline(MARGIN, H - 34, W - 2 * MARGIN, INK, 2)
    draw_text_centered(cv, W // 2, H - 26,
                       "COMPILED FROM THE DAY'S REPORTS - TUESDAY 24 NOVEMBER 2026",
                       2, GREY)
    return cv


# ---------------------------------------------------------------- PNG out
def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    plte = b"".join(struct.pack("BBB", *c) for c in PALETTE)
    raw = b"".join(b"\x00" + bytes(row) for row in cv.px)
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 3, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
           chunk(b"PLTE", plte) +
           chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    return png


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    for name in os.listdir(outdir):
        path = os.path.join(outdir, name)
        if os.path.isfile(path):
            os.remove(path)
    data = encode_png(draw_page())
    with open(os.path.join(outdir, "entry.png"), "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
