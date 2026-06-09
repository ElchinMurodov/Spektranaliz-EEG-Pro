"""SVG dizayndan kafolatlangan raster fayllar (ikona .ico/.png va logo .png) yasaydi.

Nima uchun kerak:
  Windows'da SVG ni to'g'ridan-to'g'ri rasterlash ishonchsiz (cairosvg native
  kutubxona talab qiladi, svglib esa filter/gradient/letter-spacing da xato
  berishi mumkin). Natijada .exe yuzi, oyna ikonkasi va logo bo'sh qolardi.

  Bu skript quyidagilarni hosil qiladi:
    - spektranaliz-eeg-icon.ico   (.exe, oyna, yorliq ikonasi uchun)
    - spektranaliz-eeg-icon.png
    - spektranaliz-eeg-logo.png        (och fon uchun)
    - spektranaliz-eeg-logo-dark.png   (qora fon uchun)

  Tartib: avval SVG konverteri (cairosvg -> svglib) sinaladi; ishlamasa, aynan
  shu dizayn SOF PILLOW bilan chiziladi (har doim ishlaydi, bo'sh qolmaydi).

Ishga tushirish:
    python make_assets.py
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

ICON_SVG = os.path.join(HERE, "spektranaliz-eeg-icon.svg")
LOGO_LIGHT_SVG = os.path.join(HERE, "spektranaliz-eeg-logo.svg")
LOGO_DARK_SVG = os.path.join(HERE, "spektranaliz-eeg-logo-dark.svg")

OUT_ICO = os.path.join(HERE, "spektranaliz-eeg-icon.ico")
OUT_ICON_PNG = os.path.join(HERE, "spektranaliz-eeg-icon.png")
OUT_LOGO_LIGHT = os.path.join(HERE, "spektranaliz-eeg-logo.png")
OUT_LOGO_DARK = os.path.join(HERE, "spektranaliz-eeg-logo-dark.png")

ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]

# ----------------------------------------------------------------------------
#  Geometriya - spektranaliz-eeg-icon.svg dan olingan (512x512 koordinata fazo)
# ----------------------------------------------------------------------------
BARS = [
    (120, 300, 34, 84, "#1f6fd6"),
    (166, 270, 34, 114, "#19b3c6"),
    (212, 232, 34, 152, "#36c27e"),
    (258, 258, 34, 126, "#f0a000"),
    (304, 288, 34, 96, "#e8543f"),
    (350, 316, 34, 68, "#2f80d8"),
]
BRAIN_PATHS = [
    "M232 96 C181 92 145 120 138 158 C108 165 100 205 124 228 "
    "C112 252 128 286 162 286 C176 308 214 312 232 292",
    "M214 132 C188 134 178 152 190 168 C170 174 168 198 188 204",
    "M210 214 C190 220 188 240 206 248 C198 262 210 278 226 274",
]
STEM_PATH = "M232 96 L232 292"
WAVE_PATH = (
    "M232 200 H266 C282 200 282 168 298 168 C314 168 314 232 330 232 "
    "L344 120 L360 232 C372 232 372 200 392 200 H410"
)
ACCENT = [
    (0, 22, 12, 34, "#19b3c6"),
    (20, 6, 12, 50, "#36c27e"),
    (40, 30, 12, 26, "#f0a000"),
    (60, 14, 12, 42, "#e8543f"),
]


# ----------------------------------------------------------------------------
#  SVG -> PNG (eng yuqori sifat, faqat ISHONCHLI yo'l: cairosvg).
#  cairosvg bo'lmasa None qaytaradi -> sof Pillow chizishga o'tiladi.
#  (svglib ataylab ishlatilmaydi: u filtr/gradientlarda bo'sh yoki buzuq
#   natija berishi mumkin va ikona/logoni bo'sh qoldirib qo'yardi.)
# ----------------------------------------------------------------------------
def svg_to_image(svg_path, width, height):
    if not os.path.exists(svg_path):
        return None
    try:
        import cairosvg
        from PIL import Image
        png = cairosvg.svg2png(url=svg_path, output_width=width, output_height=height)
        image = Image.open(io.BytesIO(png)).convert("RGBA")
        # Bo'sh (butunlay shaffof) natijani rad etamiz.
        if image.getbbox() is None:
            return None
        return image
    except Exception:
        return None


# ----------------------------------------------------------------------------
#  Pillow bilan chizish yordamchilari
# ----------------------------------------------------------------------------
def cubic(p0, p1, p2, p3, steps=26):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0]
        y = mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def parse_path(d):
    """M, L, H, V, C (absolute) buyruqlaridan iborat yo'lni nuqtalar ro'yxatiga aylantiradi."""
    tokens = re.findall(r"[MLHVCmlhvc]|-?\d+\.?\d*", d)
    pts = []
    cur = (0.0, 0.0)
    i = 0
    cmd = None
    while i < len(tokens):
        token = tokens[i]
        if token.isalpha():
            cmd = token
            i += 1
        if cmd in ("M", "L"):
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            cur = (x, y)
            pts.append(cur)
        elif cmd == "H":
            x = float(tokens[i]); i += 1
            cur = (x, cur[1]); pts.append(cur)
        elif cmd == "V":
            y = float(tokens[i]); i += 1
            cur = (cur[0], y); pts.append(cur)
        elif cmd == "C":
            p1 = (float(tokens[i]), float(tokens[i + 1]))
            p2 = (float(tokens[i + 2]), float(tokens[i + 3]))
            p3 = (float(tokens[i + 4]), float(tokens[i + 5]))
            i += 6
            pts.extend(cubic(cur, p1, p2, p3)[1:])
            cur = p3
        else:
            i += 1
    return pts


def draw_stroke(draw, points, mapper, scale, color, width):
    w = max(2, int(round(width * scale)))
    mapped = [mapper(x, y) for (x, y) in points]
    if len(mapped) >= 2:
        draw.line(mapped, fill=color, width=w, joint="curve")
        r = w / 2.0
        for (cx, cy) in (mapped[0], mapped[-1]):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def draw_emblem(draw, ox, oy, scale):
    """spektranaliz-eeg-icon.svg emblemini berilgan joy/o'lchamda chizadi."""
    def M(x, y):
        return (ox + x * scale, oy + y * scale)

    def rect(x, y, w, h, color, r):
        draw.rounded_rectangle([M(x, y), M(x + w, y + h)], radius=max(1, r * scale), fill=color)

    cx, cy = 256, 256
    # Badge (tashqi halqa + ichki to'q fon)
    draw.ellipse([M(cx - 244, cy - 244), M(cx + 244, cy + 244)], fill="#2f80d8")
    draw.ellipse(
        [M(cx - 224, cy - 224), M(cx + 224, cy + 224)],
        fill="#0e2746", outline="#3f8fd8", width=max(1, int(2 * scale)),
    )
    # Spektr ustunlari
    for (x, y, w, h, color) in BARS:
        rect(x, y, w, h, color, 9)
    draw.line([M(108, 390), M(404, 390)], fill="#3f8fd8", width=max(1, int(3 * scale)))
    # Miya (brain) + poya
    for path_d in BRAIN_PATHS:
        draw_stroke(draw, parse_path(path_d), M, scale, "#43b6e6", 11)
    draw_stroke(draw, parse_path(STEM_PATH), M, scale, "#43b6e6", 11)
    # EEG to'lqini + nuqta
    draw_stroke(draw, parse_path(WAVE_PATH), M, scale, "#e6f6ff", 12)
    dot = 9
    draw.ellipse([M(410 - dot, 200 - dot), M(410 + dot, 200 + dot)], fill="#ffffff")


def draw_icon(size):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_emblem(draw, 0, 0, size / 512.0)
    return img


def load_font(size, bold=True):
    from PIL import ImageFont

    names = (
        ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    )
    search_dirs = ["", "C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/"]
    for name in names:
        for folder in search_dirs:
            try:
                return ImageFont.truetype(os.path.join(folder, name) if folder else name, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_text_baseline(draw, text, x, y, font, color, tracking=0):
    """Matnni tayanch chizig'i (baseline) bo'yicha, harflar oralig'i bilan chizadi."""
    try:
        if tracking:
            cursor = x
            for ch in text:
                draw.text((cursor, y), ch, font=font, fill=color, anchor="ls")
                cursor += font.getlength(ch) + tracking
        else:
            draw.text((x, y), text, font=font, fill=color, anchor="ls")
    except TypeError:
        # Eski Pillow: anchor yo'q -> taxminiy yuqori-chap koordinata
        ascent = font.getmetrics()[0] if hasattr(font, "getmetrics") else font.size
        draw.text((x, y - ascent), text, font=font, fill=color)


def draw_logo(dark=False):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (1320, 420), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Emblem (logo SVG dagi transform: translate(20,38) scale(0.672))
    draw_emblem(draw, 20, 38, 0.672)

    word_color = "#bfe0ff" if dark else "#2f80d8"
    eeg_color = "#f7b733" if dark else "#f0a000"
    sub_color = "#9fb6cc" if dark else "#5b7185"

    draw_text_baseline(draw, "Spektranaliz", 392, 208, load_font(118, True), word_color)
    draw_text_baseline(draw, "EEG", 396, 300, load_font(92, True), eeg_color, tracking=14)

    for (x, y, w, h, color) in ACCENT:
        draw.rounded_rectangle([(610 + x, 228 + y), (610 + x + w, 228 + y + h)], radius=4, fill=color)

    draw_text_baseline(
        draw, "Sportchi EEG signallarini spektral tahlil qilish",
        396, 356, load_font(33, False), sub_color,
    )
    return img


# ----------------------------------------------------------------------------
def save_ico(image):
    """Ikona .ico ni KLASSIK BMP formatida saqlaydi (PyInstaller/Explorer uchun
    eng ishonchli). bitmap_format Pillow'ning eski versiyasida bo'lmasligi
    mumkin, shunday holda oddiy usulga qaytamiz."""
    sizes = [(s, s) for s in ICON_SIZES]
    try:
        image.save(OUT_ICO, format="ICO", bitmap_format="bmp", sizes=sizes)
    except TypeError:
        image.save(OUT_ICO, format="ICO", sizes=sizes)


def build_icon(force):
    if os.path.exists(OUT_ICO) and os.path.exists(OUT_ICON_PNG) and not force:
        print(f"[SKIP] {os.path.basename(OUT_ICO)} mavjud (saqlandi). Qayta yasash: --force")
        return
    image = svg_to_image(ICON_SVG, 256, 256)
    source = "SVG"
    if image is None:
        image = draw_icon(256)
        source = "Pillow"
    save_ico(image)
    image.save(OUT_ICON_PNG, format="PNG")
    print(f"[OK] Ikona ({source}): {os.path.basename(OUT_ICO)} + .png")


def build_logo(svg_path, out_path, dark, force):
    if os.path.exists(out_path) and not force:
        print(f"[SKIP] {os.path.basename(out_path)} mavjud (saqlandi). Qayta yasash: --force")
        return
    image = svg_to_image(svg_path, 1320, 420)
    source = "SVG"
    if image is None:
        image = draw_logo(dark=dark)
        source = "Pillow"
    image.save(out_path, format="PNG")
    print(f"[OK] Logo ({source}): {os.path.basename(out_path)}")


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("[XATO] Pillow o'rnatilmagan. Bajaring: pip install pillow")

    force = "--force" in sys.argv[1:]
    build_icon(force)
    build_logo(LOGO_LIGHT_SVG, OUT_LOGO_LIGHT, False, force)
    build_logo(LOGO_DARK_SVG, OUT_LOGO_DARK, True, force)
    print("[TAYYOR] Raster fayllar tayyor.")


if __name__ == "__main__":
    sys.exit(main())
