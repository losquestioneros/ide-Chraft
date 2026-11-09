"""Tassen-Motiv "FUHRIE" (E rot durchgestrichen) + kleines "MANN" rechts vom E,
auf der Linie des untersten E-Strichs.

Erzeugt:
  fuhrie-mann_transparent.png  – zum Hochladen beim Tassen-Druckservice
  fuhrie-mann_weiss.png        – gleiches Motiv auf weissem Hintergrund
  vorschau-tasse.png           – grobe Vorschau auf einer Tasse

Aufruf:  python3 tasse/generate.py
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT_BIG = os.path.join(FONT_DIR, "InterDisplay-Black.otf")
FONT_SMALL = os.path.join(FONT_DIR, "InterDisplay-Bold.otf")

BLACK = (17, 17, 17, 255)
RED = (214, 32, 26, 255)  # Marker-Rot

SS = 3                 # Supersampling
FINAL_WIDTH = 3000     # Breite des fertigen Motivs (px)
MARGIN = 0.06          # Rand rund ums Motiv (Anteil der Breite)

BIG_SIZE = 640 * SS
SMALL_TRACK = 0.12     # Laufweite MANN (em)
GAP_FACTOR = 1.0       # Abstand E -> MANN (x Lücke zwischen I und E)


def marker_stroke(draw, p0, p1, width, seed=7):
    """Feiner, leicht unregelmässiger Marker-Strich von p0 nach p1."""
    rnd = random.Random(seed)
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length          # Normale
    bow = 0.022 * length                         # leichte Krümmung
    phases = [rnd.uniform(0, 2 * math.pi) for _ in range(4)]

    steps = int(length / 1.2)
    for i in range(steps + 1):
        t = i / steps
        # Grundlinie (quadratische Bezier mit Bauch) + kleines Zittern
        bulge = 4 * t * (1 - t) * bow
        wob = length * (0.0016 * math.sin(2 * math.pi * 1.3 * t + phases[0])
                        + 0.0005 * math.sin(2 * math.pi * 3.1 * t + phases[1]))
        off = bulge + wob
        cx = x0 + dx * t + nx * off
        cy = y0 + dy * t + ny * off

        # Breitenverlauf: Ansatzpunkt etwas satter, Ende läuft dünn aus
        w = 1.0
        w *= 0.75 + 0.25 * min(1.0, t / 0.03)                    # weicher Start
        w *= 1.0 + 0.22 * math.exp(-((t - 0.025) / 0.03) ** 2)   # Tinten-Ansatz
        if t > 0.80:
            w *= 1.0 - 0.62 * ((t - 0.80) / 0.20) ** 1.6          # Auslaufen
        w *= 1.0 + 0.06 * math.sin(2 * math.pi * 6.1 * t + phases[2]) \
                 + 0.03 * math.sin(2 * math.pi * 13.7 * t + phases[3])
        r = width * w / 2
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED)


def draw_tracked(draw, x, y, text, font, track_px, fill):
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch) + track_px


def tracked_width(text, font, track_px):
    return sum(font.getlength(c) for c in text) + track_px * (len(text) - 1)


def glyph_mask(font, ch):
    """Maske eines Buchstabens + Ursprung (Grundlinie links) in der Maske."""
    size = font.size
    m = Image.new("L", (size * 2, size * 2), 0)
    origin = (size // 2, int(size * 1.4))
    ImageDraw.Draw(m).text(origin, ch, font=font, fill=255, anchor="ls")
    return m, origin


def ink_bbox(font, ch):
    """Tatsächliche Tinten-Box (l, t, r, b) relativ zum Ursprung auf der Grundlinie."""
    m, (ox, oy) = glyph_mask(font, ch)
    l, t, r, b = m.getbbox()
    return l - ox, t - oy, r - ox, b - oy


def bottom_bar_height(font):
    """Höhe des untersten Querstrichs vom E (in px)."""
    m, _ = glyph_mask(font, "E")
    a = np.array(m)
    l, t, r, b = m.getbbox()
    col = a[:, r - 6] > 127                   # Spalte ganz rechts im Strich
    rows = np.nonzero(col)[0]
    bottom = rows.max()
    top = bottom
    while top > 0 and col[top - 1]:
        top -= 1
    return bottom - top + 1


def build_motif():
    big = ImageFont.truetype(FONT_BIG, BIG_SIZE)
    cap_h = -ink_bbox(big, "H")[1]

    # Dicke des untersten E-Strichs messen -> Versalhöhe von MANN
    bar_h = bottom_bar_height(big)
    small_size = round(BIG_SIZE * bar_h / cap_h)
    small = ImageFont.truetype(FONT_SMALL, small_size)
    small_track = SMALL_TRACK * small_size

    W = int(BIG_SIZE * 6)
    H = int(BIG_SIZE * 3)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    ox, base = int(BIG_SIZE * 0.6), int(BIG_SIZE * 1.4)
    d.text((ox, base), "FUHRIE", font=big, fill=BLACK, anchor="ls")

    # Lage des E (Tinte)
    ex = ox + big.getlength("FUHRI")
    el, et, er, eb = ink_bbox(big, "E")
    e_left, e_right = ex + el, ex + er
    e_top, e_bot = base + et, base + eb
    e_w, e_h = e_right - e_left, e_bot - e_top

    # Lücke zwischen I und E (Tinte)
    i_right = ox + big.getlength("FUHR") + ink_bbox(big, "I")[2]
    gap = e_left - i_right

    # MANN klein, rechts vom E, auf der Grundlinie = unterster E-Strich
    m_left = e_right + GAP_FACTOR * gap - ink_bbox(small, "M")[0]
    draw_tracked(d, m_left, base, "MANN", small, small_track, BLACK)

    # Roter Strich: von unten links nach oben rechts, nur über das E
    # (Start in der Lücke zwischen I und E, damit das I unberührt bleibt)
    p0 = (e_left - 0.35 * gap, e_bot + 0.02 * e_h)
    p1 = (e_right + 0.16 * e_w, e_top - 0.07 * e_h)
    marker_stroke(d, p0, p1, width=0.042 * cap_h)

    # Zuschneiden + Rand + Herunterrechnen
    bbox = img.getbbox()
    img = img.crop(bbox)
    target_inner = FINAL_WIDTH * (1 - 2 * MARGIN)
    scale = target_inner / img.width
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    pad = round(FINAL_WIDTH * MARGIN)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.paste(img, (pad, pad), img)
    return out


def mug_preview(motif):
    """Einfache flache Tassen-Illustration zur Kontrolle."""
    S = 2
    W, H = 1600 * S, 1200 * S
    bg = Image.new("RGB", (W, H), (236, 233, 228))
    d = ImageDraw.Draw(bg)

    bx0, bx1 = 330 * S, 1150 * S
    by0, by1 = 230 * S, 1010 * S
    rim_h = 90 * S

    # Schatten
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse((bx0 + 20 * S, by1 - 30 * S, bx1 + 90 * S, by1 + 60 * S), fill=90)
    sh = sh.filter(ImageFilter.GaussianBlur(28 * S))
    bg.paste((200, 196, 190), (0, 0), sh)

    # Henkel
    hx0, hy0, hx1, hy1 = bx1 - 90 * S, 360 * S, bx1 + 230 * S, 820 * S
    d.rounded_rectangle((hx0, hy0, hx1, hy1), radius=150 * S, fill=(250, 250, 249))
    d.rounded_rectangle((hx0 + 70 * S, hy0 + 75 * S, hx1 - 75 * S, hy1 - 75 * S),
                        radius=90 * S, fill=(236, 233, 228))

    # Körper mit Zylinder-Schattierung
    body = Image.new("RGB", (bx1 - bx0, by1 - by0))
    xs = np.linspace(-1, 1, bx1 - bx0)
    shade = 252 - 38 * np.abs(xs) ** 2.6 + 4 * np.cos(xs * 2.2 - 0.9)
    arr = np.clip(np.tile(shade[None, :, None], (by1 - by0, 1, 3)), 0, 255).astype(np.uint8)
    body = Image.fromarray(arr)
    mask = Image.new("L", body.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, body.width, body.height), radius=70 * S, fill=255)
    md.rectangle((0, 0, body.width, 100 * S), fill=255)
    bg.paste(body, (bx0, by0), mask)

    # Rand oben
    d.ellipse((bx0, by0 - rim_h // 2, bx1, by0 + rim_h // 2), fill=(248, 247, 245))
    d.ellipse((bx0 + 22 * S, by0 - rim_h // 2 + 14 * S, bx1 - 22 * S, by0 + rim_h // 2 - 10 * S),
              fill=(205, 200, 194))

    # Motif auf den Körper
    mw = int((bx1 - bx0) * 0.78)
    m = motif.resize((mw, round(motif.height * mw / motif.width)), Image.LANCZOS)
    mx = bx0 + ((bx1 - bx0) - m.width) // 2
    my = by0 + ((by1 - by0) - m.height) // 2 + 10 * S
    bg.paste(m, (mx, my), m)

    return bg.resize((W // S, H // S), Image.LANCZOS)


if __name__ == "__main__":
    motif = build_motif()
    dpi = (300, 300)
    motif.save(os.path.join(HERE, "fuhrie-mann_transparent.png"), dpi=dpi)
    white = Image.new("RGB", motif.size, (255, 255, 255))
    white.paste(motif, (0, 0), motif)
    white.save(os.path.join(HERE, "fuhrie-mann_weiss.png"), dpi=dpi)
    mug_preview(motif).save(os.path.join(HERE, "vorschau-tasse.png"))
    print("Motiv:", motif.size)
