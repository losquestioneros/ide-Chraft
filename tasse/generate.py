"""Tassen-Motiv "FUHRIE" (E rot durchgestrichen) + kleines "MANN" rechts vom E,
auf der Linie des untersten E-Strichs.

Erzeugt je Farbvariante (schwarz / babyblau):
  fuhrie-mann…_PDFX-1a.pdf     – Druckdatei: Vektor, CMYK, PDF/X-1a:2003,
                                 FOGRA51 (PSO Coated v3), 2 mm Beschnitt
  fuhrie-mann…_transparent.png – Pixelbild, transparenter Hintergrund
  fuhrie-mann…_weiss.png       – Pixelbild, weisser Hintergrund
  vorschau-tasse….png          – grobe Vorschau auf einer Tasse

Aufruf:  python3 tasse/generate.py      (braucht: pillow numpy fonttools pikepdf)
"""
import datetime
import math
import os
import random

import numpy as np
import pikepdf
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT_BIG = os.path.join(FONT_DIR, "InterDisplay-Black.otf")
FONT_SMALL = os.path.join(FONT_DIR, "InterDisplay-Bold.otf")

# Farben: RGB für PNG/Vorschau, CMYK (0–1) für das Druck-PDF
VARIANTS = {
    "schwarz":  {"suffix": "",          "rgb": (17, 17, 17),    "cmyk": (0, 0, 0, 1)},
    "babyblau": {"suffix": "_babyblau", "rgb": (126, 186, 232), "cmyk": (0.50, 0.15, 0, 0)},
}
RED_RGB = (214, 32, 26)
RED_CMYK = (0, 0.95, 1, 0)

SS = 3                 # Supersampling für PNG
FINAL_WIDTH = 3000     # Breite des PNG-Motivs (px)
MARGIN = 0.06          # Rand ums PNG-Motiv (Anteil der Breite)

BIG_SIZE = 640 * SS
SMALL_TRACK = 0.12     # Laufweite MANN (em)
GAP_FACTOR = 1.0       # Abstand E -> MANN (x Lücke zwischen I und E)

# PDF-Format
MM = 72 / 25.4
PDF_INK_WIDTH_MM = 90  # Breite des Motivs selbst
PDF_SAFE_MM = 5        # Abstand Motiv -> Endformat (Sicherheitsabstand)
PDF_BLEED_MM = 2       # Beschnittzugabe rundherum


# ---------------------------------------------------------------- Geometrie

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


def glyph_positions(font, text, x, track=0.0):
    """x-Ursprung jedes Buchstabens (inkl. Kerning) + Laufweite."""
    out = []
    for i, ch in enumerate(text):
        pos = font.getlength(text[: i + 1]) - font.getlength(ch)
        out.append((ch, x + pos + i * track))
    return out


def marker_outline(p0, p1, width, seed=7, steps=700):
    """Umriss (Polygon) eines feinen, leicht unregelmässigen Marker-Strichs."""
    rnd = random.Random(seed)
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    nx0, ny0 = -dy / length, dx / length
    bow = 0.022 * length
    ph = [rnd.uniform(0, 2 * math.pi) for _ in range(4)]

    t = np.linspace(0, 1, steps + 1)
    off = 4 * t * (1 - t) * bow + length * (
        0.0016 * np.sin(2 * np.pi * 1.3 * t + ph[0])
        + 0.0005 * np.sin(2 * np.pi * 3.1 * t + ph[1]))
    cx = x0 + dx * t + nx0 * off
    cy = y0 + dy * t + ny0 * off

    w = np.ones_like(t)
    w *= 0.75 + 0.25 * np.minimum(1.0, t / 0.03)                 # weicher Start
    w *= 1.0 + 0.22 * np.exp(-((t - 0.025) / 0.03) ** 2)         # Tinten-Ansatz
    tail = np.clip((t - 0.80) / 0.20, 0, 1)
    w *= 1.0 - 0.62 * tail ** 1.6                                 # Auslaufen
    w *= 1.0 + 0.06 * np.sin(2 * np.pi * 6.1 * t + ph[2]) \
             + 0.03 * np.sin(2 * np.pi * 13.7 * t + ph[3])
    r = width * w / 2

    tx, ty = np.gradient(cx), np.gradient(cy)
    tl = np.hypot(tx, ty)
    tx, ty = tx / tl, ty / tl
    nx, ny = -ty, tx

    left = list(zip(cx + nx * r, cy + ny * r))
    right = list(zip(cx - nx * r, cy - ny * r))

    def cap(i, sign):
        pts = []
        for a in np.linspace(0, math.pi, 24)[1:-1]:
            ux = sign * (math.cos(a) * nx[i] + math.sin(a) * tx[i])
            uy = sign * (math.cos(a) * ny[i] + math.sin(a) * ty[i])
            pts.append((cx[i] + r[i] * ux, cy[i] + r[i] * uy))
        return pts

    return left + cap(-1, 1) + right[::-1] + cap(0, -1)


def build_layout():
    """Alle Positionen in px (Supersampling-Raum, y nach unten)."""
    big = ImageFont.truetype(FONT_BIG, BIG_SIZE)
    cap_h = -ink_bbox(big, "H")[1]

    bar_h = bottom_bar_height(big)                 # -> Versalhöhe von MANN
    small_size = round(BIG_SIZE * bar_h / cap_h)
    small = ImageFont.truetype(FONT_SMALL, small_size)
    small_track = SMALL_TRACK * small_size

    ox, base = int(BIG_SIZE * 0.6), int(BIG_SIZE * 1.4)
    big_glyphs = glyph_positions(big, "FUHRIE", ox)

    i_x, e_x = big_glyphs[4][1], big_glyphs[5][1]
    el, et, er, eb = ink_bbox(big, "E")
    e_left, e_right, e_top, e_bot = e_x + el, e_x + er, base + et, base + eb
    e_w, e_h = e_right - e_left, e_bot - e_top
    gap = e_left - (i_x + ink_bbox(big, "I")[2])

    # MANN klein, rechts vom E, auf der Grundlinie = unterster E-Strich
    m_left = e_right + GAP_FACTOR * gap - ink_bbox(small, "M")[0]
    small_glyphs = glyph_positions(small, "MANN", m_left, small_track)

    # Roter Strich: unten links -> oben rechts, nur über das E
    p0 = (e_left - 0.35 * gap, e_bot + 0.02 * e_h)
    p1 = (e_right + 0.16 * e_w, e_top - 0.07 * e_h)
    stroke = marker_outline(p0, p1, width=0.042 * cap_h)

    return {
        "canvas": (int(BIG_SIZE * 6), int(BIG_SIZE * 3)),
        "base": base,
        "text": [(FONT_BIG, BIG_SIZE, ch, x) for ch, x in big_glyphs]
              + [(FONT_SMALL, small_size, ch, x) for ch, x in small_glyphs],
        "stroke": stroke,
    }


# ---------------------------------------------------------------- PNG

def render_png(L, rgb):
    img = Image.new("RGBA", L["canvas"], (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fonts = {}
    for path, size, ch, x in L["text"]:
        f = fonts.setdefault((path, size), ImageFont.truetype(path, size))
        d.text((x, L["base"]), ch, font=f, fill=rgb + (255,), anchor="ls")
    d.polygon(L["stroke"], fill=RED_RGB + (255,))

    bbox = img.getbbox()
    img = img.crop(bbox)
    target_inner = FINAL_WIDTH * (1 - 2 * MARGIN)
    scale = target_inner / img.width
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    pad = round(FINAL_WIDTH * MARGIN)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.paste(img, (pad, pad), img)
    return out, bbox


# ---------------------------------------------------------------- PDF/X-1a

class PdfPathPen(BasePen):
    """Schreibt Glyphen-Umrisse als PDF-Pfadoperatoren."""

    def __init__(self, glyphset, tf):
        super().__init__(glyphset)
        self.tf, self.ops = tf, []

    def _p(self, pt):
        x, y = self.tf(*pt)
        return f"{x:.3f} {y:.3f}"

    def _moveTo(self, pt):
        self.ops.append(f"{self._p(pt)} m")

    def _lineTo(self, pt):
        self.ops.append(f"{self._p(pt)} l")

    def _curveToOne(self, p1, p2, p3):
        self.ops.append(f"{self._p(p1)} {self._p(p2)} {self._p(p3)} c")

    def _closePath(self):
        self.ops.append("h")


def render_pdf(L, bbox, cmyk, path, title):
    bx0, by0, bx1, by1 = bbox
    s = PDF_INK_WIDTH_MM * MM / (bx1 - bx0)          # pt pro px
    off = (PDF_SAFE_MM + PDF_BLEED_MM) * MM
    trim_w = PDF_INK_WIDTH_MM * MM + 2 * PDF_SAFE_MM * MM
    trim_h = (by1 - by0) * s + 2 * PDF_SAFE_MM * MM
    bleed = PDF_BLEED_MM * MM
    media_w, media_h = trim_w + 2 * bleed, trim_h + 2 * bleed

    def px2pt(x, y):
        return off + (x - bx0) * s, media_h - (off + (y - by0) * s)

    def k(c):
        return " ".join(f"{v:.3f}" for v in c) + " k"

    ops = ["q", k(cmyk)]
    tt = {}
    for fpath, size, ch, x in L["text"]:
        font = tt.setdefault(fpath, TTFont(fpath))
        gs = font.getGlyphSet()
        u = size / font["head"].unitsPerEm
        base = L["base"]
        pen = PdfPathPen(gs, lambda gx, gy, x=x, u=u: px2pt(x + gx * u, base - gy * u))
        gs[font.getBestCmap()[ord(ch)]].draw(pen)
        ops += pen.ops
    ops.append("f")

    ops.append(k(RED_CMYK))
    pts = [px2pt(x, y) for x, y in L["stroke"]]
    ops.append(f"{pts[0][0]:.3f} {pts[0][1]:.3f} m")
    ops += [f"{x:.3f} {y:.3f} l" for x, y in pts[1:]]
    ops += ["h", "f", "Q"]

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(media_w, media_h))
    page = pdf.pages[0]
    page.obj.MediaBox = pikepdf.Array([0, 0, media_w, media_h])
    page.obj.BleedBox = pikepdf.Array([0, 0, media_w, media_h])
    page.obj.TrimBox = pikepdf.Array([bleed, bleed, bleed + trim_w, bleed + trim_h])
    page.obj.Contents = pdf.make_stream("\n".join(ops).encode())

    pdf.Root.OutputIntents = pikepdf.Array([pikepdf.Dictionary(
        Type=pikepdf.Name.OutputIntent,
        S=pikepdf.Name.GTS_PDFX,
        OutputConditionIdentifier="FOGRA51",
        OutputCondition="PSO Coated v3 (FOGRA51)",
        RegistryName="http://www.color.org",
        Info="PSO Coated v3, ISO 12647-2:2013, FOGRA51",
    )])
    now = datetime.datetime.now().astimezone()
    tz = now.strftime("%z")
    stamp = now.strftime("D:%Y%m%d%H%M%S") + f"{tz[0]}{tz[1:3]}'{tz[3:5]}'"
    pdf.docinfo.Title = title
    pdf.docinfo.Creator = "tasse/generate.py"
    pdf.docinfo.Producer = f"pikepdf {pikepdf.__version__}"
    pdf.docinfo.CreationDate = stamp
    pdf.docinfo.ModDate = stamp
    pdf.docinfo.Trapped = pikepdf.Name("/False")
    pdf.docinfo.GTS_PDFXVersion = "PDF/X-1a:2003"
    pdf.save(path, force_version="1.4",
             object_stream_mode=pikepdf.ObjectStreamMode.disable)
    return trim_w / MM, trim_h / MM


# ---------------------------------------------------------------- Vorschau

def mug_preview(motif):
    """Einfache flache Tassen-Illustration zur Kontrolle."""
    S = 2
    W, H = 1600 * S, 1200 * S
    bg = Image.new("RGB", (W, H), (236, 233, 228))
    d = ImageDraw.Draw(bg)

    bx0, bx1 = 330 * S, 1150 * S
    by0, by1 = 230 * S, 1010 * S
    rim_h = 90 * S

    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse((bx0 + 20 * S, by1 - 30 * S, bx1 + 90 * S, by1 + 60 * S), fill=90)
    sh = sh.filter(ImageFilter.GaussianBlur(28 * S))
    bg.paste((200, 196, 190), (0, 0), sh)

    hx0, hy0, hx1, hy1 = bx1 - 90 * S, 360 * S, bx1 + 230 * S, 820 * S
    d.rounded_rectangle((hx0, hy0, hx1, hy1), radius=150 * S, fill=(250, 250, 249))
    d.rounded_rectangle((hx0 + 70 * S, hy0 + 75 * S, hx1 - 75 * S, hy1 - 75 * S),
                        radius=90 * S, fill=(236, 233, 228))

    xs = np.linspace(-1, 1, bx1 - bx0)
    shade = 252 - 38 * np.abs(xs) ** 2.6 + 4 * np.cos(xs * 2.2 - 0.9)
    arr = np.clip(np.tile(shade[None, :, None], (by1 - by0, 1, 3)), 0, 255).astype(np.uint8)
    body = Image.fromarray(arr)
    mask = Image.new("L", body.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, body.width, body.height), radius=70 * S, fill=255)
    md.rectangle((0, 0, body.width, 100 * S), fill=255)
    bg.paste(body, (bx0, by0), mask)

    d.ellipse((bx0, by0 - rim_h // 2, bx1, by0 + rim_h // 2), fill=(248, 247, 245))
    d.ellipse((bx0 + 22 * S, by0 - rim_h // 2 + 14 * S, bx1 - 22 * S, by0 + rim_h // 2 - 10 * S),
              fill=(205, 200, 194))

    mw = int((bx1 - bx0) * 0.78)
    m = motif.resize((mw, round(motif.height * mw / motif.width)), Image.LANCZOS)
    mx = bx0 + ((bx1 - bx0) - m.width) // 2
    my = by0 + ((by1 - by0) - m.height) // 2 + 10 * S
    bg.paste(m, (mx, my), m)

    return bg.resize((W // S, H // S), Image.LANCZOS)


# ---------------------------------------------------------------- Export

def export(L, name, v):
    sfx = v["suffix"]
    motif, bbox = render_png(L, v["rgb"])
    dpi = (300, 300)
    motif.save(os.path.join(HERE, f"fuhrie-mann{sfx}_transparent.png"), dpi=dpi)
    white = Image.new("RGB", motif.size, (255, 255, 255))
    white.paste(motif, (0, 0), motif)
    white.save(os.path.join(HERE, f"fuhrie-mann{sfx}_weiss.png"), dpi=dpi)
    mug_preview(motif).save(os.path.join(HERE, f"vorschau-tasse{sfx}.png"))
    w, h = render_pdf(L, bbox, v["cmyk"],
                      os.path.join(HERE, f"fuhrie-mann_{name}_PDFX-1a.pdf"),
                      f"FUHRIE / MANN – Tassenmotiv {name}")
    print(f"{name}: PNG {motif.size}, PDF Endformat {w:.1f} × {h:.1f} mm "
          f"(+{PDF_BLEED_MM} mm Beschnitt)")


if __name__ == "__main__":
    layout = build_layout()
    for name, v in VARIANTS.items():
        export(layout, name, v)
