"""
charts.py — Tahlil natijalarini CHIROYLI, ZAMONAVIY GRAFIK ko'rinishida chizish.

Pillow (PIL) yordamida (matplotlib SHART EMAS):
  - Gradiyentli sarlavha + ishonch darajasi halqa-diagrammasi (donut gauge)
  - Soyali, yumaloq kartalar (modern "card" dizayni)
  - To'ldirilgan (area) PSD grafigi, yumaloq ustunlar, topomaplar
  - Funksional holatlar va belgilar jadvallari

TEMA TIZIMI: ranglar `THEMES` lug'atida saqlanadi. `apply_theme(nom)` orqali
almashtiriladi. Standart — "akademik" (dissertatsiya uchun tinch, bosma-do'st
rang sxemasi). "zamonaviy" temasi ham mavjud.

TAB (bo'lim) RASMLARI: `tab_images()` natijani 4 bo'limga ajratadi
(Umumiy / Spektr / Topografiya / Kanallar) — GUI'dagi tablar uchun.
To'liq poster (`composite_*`) va `save_pdf` ham mavjud.
"""

from PIL import Image, ImageDraw, ImageFont

from . import config


# ---------------------------------------------------------------------------
# TEMALAR
# ---------------------------------------------------------------------------
THEMES = {
    # Dissertatsiya uchun: tinch, ilmiy, bosma-do'st (navy + teal)
    "akademik": {
        "BG": (245, 247, 250), "CARD": (255, 255, 255), "BORDER": (222, 228, 236),
        "INK": (28, 37, 54), "MUTED": (90, 100, 116), "FAINT": (150, 162, 178),
        "HEAD1": (27, 54, 93), "HEAD2": (44, 95, 130), "ACCENT": (38, 110, 140),
        "GOOD": (46, 139, 87), "WARN": (191, 139, 30), "BAD": (176, 58, 50),
        "ROW_TINT": (246, 248, 251),
        "BANDS": {"delta": (40, 72, 120), "theta": (33, 118, 141),
                  "alpha": (56, 142, 90), "beta": (191, 139, 30), "gamma": (168, 58, 50)},
    },
    # Zamonaviy: yorqin (indigo + tailwind ranglari)
    "zamonaviy": {
        "BG": (243, 246, 250), "CARD": (255, 255, 255), "BORDER": (228, 233, 240),
        "INK": (17, 24, 39), "MUTED": (107, 114, 128), "FAINT": (148, 163, 184),
        "HEAD1": (79, 70, 229), "HEAD2": (37, 99, 235), "ACCENT": (37, 99, 235),
        "GOOD": (34, 197, 94), "WARN": (245, 158, 11), "BAD": (239, 68, 68),
        "ROW_TINT": (247, 249, 252),
        "BANDS": {"delta": (99, 102, 241), "theta": (14, 165, 233),
                  "alpha": (16, 185, 129), "beta": (245, 158, 11), "gamma": (239, 68, 68)},
    },
}

# Joriy tema qiymatlari (apply_theme ularni o'rnatadi)
BG = CARD = BORDER = INK = MUTED = FAINT = None
HEAD1 = HEAD2 = ACCENT = GOOD = WARN = BAD = ROW_TINT = None
BAND_COLORS = {}


def apply_theme(name="akademik"):
    """Rang temasini o'rnatadi (global ranglarni yangilaydi)."""
    global BG, CARD, BORDER, INK, MUTED, FAINT
    global HEAD1, HEAD2, ACCENT, GOOD, WARN, BAD, ROW_TINT, BAND_COLORS
    t = THEMES.get(name, THEMES["akademik"])
    BG, CARD, BORDER = t["BG"], t["CARD"], t["BORDER"]
    INK, MUTED, FAINT = t["INK"], t["MUTED"], t["FAINT"]
    HEAD1, HEAD2, ACCENT = t["HEAD1"], t["HEAD2"], t["ACCENT"]
    GOOD, WARN, BAD = t["GOOD"], t["WARN"], t["BAD"]
    ROW_TINT = t["ROW_TINT"]
    BAND_COLORS = dict(t["BANDS"])


apply_theme("akademik")


SCALP_POS = {
    "Fp1": (-0.30, 0.90), "Fp2": (0.30, 0.90),
    "F7": (-0.80, 0.45), "F3": (-0.40, 0.50), "Fz": (0.0, 0.50),
    "F4": (0.40, 0.50), "F8": (0.80, 0.45),
    "T3": (-1.00, 0.0), "C3": (-0.50, 0.0), "Cz": (0.0, 0.0),
    "C4": (0.50, 0.0), "T4": (1.00, 0.0),
    "T7": (-1.00, 0.0), "T8": (1.00, 0.0),
    "T5": (-0.80, -0.45), "P3": (-0.40, -0.50), "Pz": (0.0, -0.50),
    "P4": (0.40, -0.50), "T6": (0.80, -0.45),
    "O1": (-0.30, -0.90), "O2": (0.30, -0.90),
}


# ---------------------------------------------------------------------------
# Shrift
# ---------------------------------------------------------------------------
_FONT_CACHE = {}


def _font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if bold:
        names = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
                 "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"]
    else:
        names = ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
                 "/usr/share/fonts/google-noto/NotoSans-Regular.ttf"]
    font = None
    for n in names:
        try:
            font = ImageFont.truetype(n, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _text_w(draw, text, font):
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l
    except Exception:
        return draw.textlength(text, font=font)


def _center(draw, cx, y, text, font, fill):
    draw.text((cx - _text_w(draw, text, font) / 2, y), text, font=font, fill=fill)


def _right(draw, rx, y, text, font, fill):
    draw.text((rx - _text_w(draw, text, font), y), text, font=font, fill=fill)


# ---------------------------------------------------------------------------
# Rang yordamchilari
# ---------------------------------------------------------------------------
def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _tint(c, t):
    return _lerp(c, (255, 255, 255), t)


def _heat_color(v):
    v = max(0.0, min(1.0, v))
    stops = [(0.0, (49, 102, 150)), (0.35, (46, 139, 120)),
             (0.65, (210, 180, 70)), (1.0, (176, 58, 50))]
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]
        v1, c1 = stops[i + 1]
        if v <= v1:
            t = (v - v0) / (v1 - v0) if v1 > v0 else 0
            return _lerp(c0, c1, t)
    return stops[-1][1]


# ---------------------------------------------------------------------------
# Shakl yordamchilari
# ---------------------------------------------------------------------------
def _round_rect(draw, box, radius, fill=None, outline=None, width=1):
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        draw.rectangle(box, fill=fill, outline=outline, width=width)


def _v_gradient(w, h, c1, c2):
    w = max(1, int(w)); h = max(1, int(h))
    g = Image.new("RGB", (w, h), c1)
    gd = ImageDraw.Draw(g)
    for i in range(h):
        gd.line([(0, i), (w, i)], fill=_lerp(c1, c2, i / max(1, h - 1)))
    return g


def _gradient_card(base, box, radius, c1, c2):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    grad = _v_gradient(w, h, c1, c2)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    base.paste(grad, (x0, y0), mask)


def _shadow(draw, box, radius):
    x0, y0, x1, y1 = box
    for off, col in ((9, (229, 233, 240)), (6, (219, 224, 233)), (3, (209, 215, 226))):
        _round_rect(draw, [x0, y0 + off, x1, y1 + off], radius, fill=col)


def _card(base, draw, x, y, w, h, title=None, accent=None):
    box = [x, y, x + w, y + h]
    _shadow(draw, box, 16)
    _round_rect(draw, box, 16, fill=CARD, outline=BORDER, width=1)
    inner = y + 16
    if title:
        draw.ellipse([x + 18, y + 19, x + 27, y + 28], fill=accent or ACCENT)
        draw.text((x + 36, y + 15), title, font=_font(16, bold=True), fill=INK)
        inner = y + 48
    return inner


def _donut(draw, cx, cy, r, thickness, frac, color, track):
    box = [cx - r, cy - r, cx + r, cy + r]
    try:
        draw.arc(box, 0, 360, fill=track, width=thickness)
        if frac > 0:
            draw.arc(box, -90, -90 + 360 * frac, fill=color, width=thickness)
    except Exception:
        draw.ellipse(box, outline=track, width=thickness)


# ---------------------------------------------------------------------------
# Qism-grafiklar
# ---------------------------------------------------------------------------
def _draw_header(img, draw, x, y, w, h, rec, cls, summ):
    _shadow(draw, [x, y, x + w, y + h], 18)
    _gradient_card(img, [x, y, x + w, y + h], 18, HEAD1, HEAD2)
    draw.text((x + 26, y + 20), "EEG Spektral Tahlil Hisoboti", font=_font(23, bold=True), fill=(255, 255, 255))
    fs_txt = ("%.0f Hz" % summ["fs"]) if summ["fs"] else "turlicha"
    sub = "%s   •   %s   •   %d kanal   •   %s   •   %.0f s" % (
        rec.meta.get("source_file", "?"), summ["format"], summ["channels"], fs_txt, summ["duration_sec"])
    draw.text((x + 26, y + 54), sub, font=_font(13), fill=_tint(HEAD2, 0.62))
    draw.text((x + 26, y + h - 46), "ANIQLANGAN HOLAT", font=_font(11, bold=True), fill=_tint(HEAD2, 0.55))
    draw.text((x + 26, y + h - 33), cls["state"], font=_font(24, bold=True), fill=(255, 255, 255))
    dcx, dcy = x + w - 72, y + h / 2
    conf = cls["confidence"]
    _donut(draw, dcx, dcy, 44, 13, conf, (255, 255, 255), _tint(HEAD2, 0.42))
    _center(draw, dcx, dcy - 14, "%.0f%%" % (conf * 100), _font(22, bold=True), (255, 255, 255))
    _center(draw, dcx, dcy + 11, "ishonch", _font(11), _tint(HEAD2, 0.5))


def _section_title(img, draw, x, y, w, text):
    h = 48
    _shadow(draw, [x, y, x + w, y + h], 14)
    _gradient_card(img, [x, y, x + w, y + h], 14, HEAD1, HEAD2)
    draw.text((x + 22, y + 13), text, font=_font(18, bold=True), fill=(255, 255, 255))
    return y + h


def _draw_psd(draw, x, y, w, h, freqs, psd, fmax=45.0):
    pad_l, pad_b, pad_r, pad_t = 50, 32, 14, 8
    px, py = x + pad_l, y + pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    pts = [(freqs[k], psd[k]) for k in range(len(freqs)) if freqs[k] <= fmax]
    if not pts:
        return
    pmax = max(p for _, p in pts) or 1e-12
    X = lambda fr: px + (fr / fmax) * pw
    Y = lambda p: py + ph - (p / pmax) * ph
    for name, (lo, hi) in config.BANDS.items():
        if lo > fmax:
            continue
        x0, x1 = X(lo), X(min(hi, fmax))
        draw.rectangle([x0, py, x1, py + ph], fill=_tint(BAND_COLORS[name], 0.86))
        _center(draw, (x0 + x1) / 2, py + 4, config.BAND_LABELS[name], _font(11, bold=True), MUTED)
    for fr in range(0, int(fmax) + 1, 5):
        gx = X(fr)
        draw.line([gx, py, gx, py + ph], fill=(236, 239, 244), width=1)
        _center(draw, gx, py + ph + 7, str(fr), _font(11), MUTED)
    draw.line([px, py + ph, px + pw, py + ph], fill=(203, 213, 225), width=1)
    _center(draw, px + pw / 2, py + ph + 19, "Chastota (Hz)", _font(12, bold=True), INK)
    curve = [(int(X(fr)), int(Y(p))) for fr, p in pts]
    area = [(curve[0][0], int(py + ph))] + curve + [(curve[-1][0], int(py + ph))]
    if len(area) >= 3:
        draw.polygon(area, fill=_tint(ACCENT, 0.80))
    if len(curve) >= 2:
        draw.line(curve, fill=ACCENT, width=3, joint="curve")


def _draw_band_bars(draw, x, y, w, h, rp):
    pad_l, pad_b, pad_t = 14, 40, 18
    px, py = x + pad_l, y + pad_t
    pw, ph = w - pad_l - 14, h - pad_t - pad_b
    bands = list(config.BANDS.keys())
    gap = pw / len(bands)
    bw = gap * 0.56
    vmax = max(rp[b] for b in bands) or 1e-9
    draw.line([px, py + ph, px + pw, py + ph], fill=(203, 213, 225), width=1)
    for i, b in enumerate(bands):
        v = rp[b]
        bx = px + i * gap + (gap - bw) / 2
        bh = max(3, (v / vmax) * ph)
        by = py + ph - bh
        _round_rect(draw, [bx, by, bx + bw, py + ph + 1], 7, fill=BAND_COLORS[b])
        _round_rect(draw, [bx, by, bx + bw, by + min(bh, 12)], 7, fill=_tint(BAND_COLORS[b], 0.28))
        label = "%.1f%%" % (v * 100)
        lw = _text_w(draw, label, _font(11, bold=True))
        _round_rect(draw, [bx + bw / 2 - lw / 2 - 6, by - 23, bx + bw / 2 + lw / 2 + 6, by - 5],
                    9, fill=_tint(BAND_COLORS[b], 0.85))
        _center(draw, bx + bw / 2, by - 21, label, _font(11, bold=True), _lerp(BAND_COLORS[b], INK, 0.3))
        _center(draw, bx + bw / 2, py + ph + 9, config.BAND_LABELS[b], _font(12, bold=True), INK)


def _draw_topomap(img, draw, x, y, w, h, channel_vals, caption=""):
    size = min(w, h) - 22
    cx = x + w / 2
    cy = y + 4 + size / 2
    R = size / 2
    draw.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(249, 250, 252), outline=(150, 162, 178), width=2)
    draw.polygon([(cx - 11, cy - R + 2), (cx + 11, cy - R + 2), (cx, cy - R - 15)],
                 fill=(249, 250, 252), outline=(150, 162, 178))
    draw.ellipse([cx - R - 6, cy - 14, cx - R + 5, cy + 14], fill=(249, 250, 252), outline=(150, 162, 178))
    draw.ellipse([cx + R - 5, cy - 14, cx + R + 6, cy + 14], fill=(249, 250, 252), outline=(150, 162, 178))
    vmax = max(channel_vals.values()) or 1e-9
    rad = max(9, int(R * 0.16))
    for ch, v in channel_vals.items():
        if ch not in SCALP_POS:
            continue
        ppx, ppy = SCALP_POS[ch]
        ex = cx + ppx * R * 0.86
        ey = cy - ppy * R * 0.86
        draw.ellipse([ex - rad, ey - rad, ex + rad, ey + rad], fill=_heat_color(v / vmax),
                     outline=(255, 255, 255), width=1)
        _center(draw, ex, ey - 5, ch, _font(9, bold=True), (17, 24, 39))
    if caption:
        _center(draw, cx, y + h - 15, caption, _font(11, bold=True), MUTED)


def _draw_state_bars(draw, x, y, w, h, scores, probs, top_state):
    px = x + 18
    py = y + 4
    label_w = 176
    bar_x = px + label_w
    bar_w = w - label_w - 96
    states = config.STATES
    row_h = (h - 8) / len(states)
    bh = min(18, row_h * 0.56)
    for i, st in enumerate(states):
        ry = py + i * row_h + (row_h - bh) / 2
        sc = scores.get(st, 0.0)
        pr = probs.get(st, 0.0)
        is_top = (st == top_state)
        draw.text((px, ry + bh / 2 - 8), st, font=_font(12, bold=is_top),
                  fill=(INK if is_top else (75, 85, 99)))
        _round_rect(draw, [bar_x, ry, bar_x + bar_w, ry + bh], bh / 2, fill=(236, 240, 245))
        fill_w = max(bh, (sc / 100.0) * bar_w)
        col = ACCENT if is_top else _tint(ACCENT, 0.5)
        _round_rect(draw, [bar_x, ry, bar_x + fill_w, ry + bh], bh / 2, fill=col)
        _right(draw, bar_x + bar_w + 82, ry + bh / 2 - 8, "%.0f%%" % (pr * 100),
               _font(12, bold=is_top), (INK if is_top else MUTED))


def _draw_features_table(draw, x, y, w, h, f):
    rows = [
        ("iAPF (alfa cho'qqisi)", "%.2f Hz" % f["iapf"]),
        ("Dominant (PSD)", "%.2f Hz" % f["dominant_frequency"]),
        ("Dominant (FFT)", "%.2f Hz" % f["fft_dominant_frequency"]),
        ("Spektral edge 95%", "%.2f Hz" % f["spectral_edge_95"]),
        ("Spektral entropiya", "%.3f" % f["spectral_entropy"]),
        ("Alpha / Beta", "%.3f" % f["ratio_alpha_beta"]),
        ("Theta / Beta", "%.3f" % f["ratio_theta_beta"]),
        ("Beta / Alpha", "%.3f" % f["ratio_beta_alpha"]),
        ("Engagement", "%.3f" % f["engagement"]),
        ("FAA (asimmetriya)", ("%.3f" % f["faa"]) if f.get("faa") is not None else "—"),
        ("FMT (frontal teta)", ("%.3f" % f["fmt"]) if f.get("fmt") is not None else "—"),
    ]
    col_w = (w - 24) / 2
    per_col = (len(rows) + 1) // 2
    rh = 28
    for idx, (name, val) in enumerate(rows):
        col = idx // per_col
        row = idx % per_col
        cx0 = x + 18 + col * col_w
        cy0 = y + 4 + row * rh
        _round_rect(draw, [cx0, cy0, cx0 + col_w - 16, cy0 + rh - 5], 7, fill=ROW_TINT)
        draw.text((cx0 + 10, cy0 + 4), name, font=_font(12), fill=(75, 85, 99))
        _right(draw, cx0 + col_w - 28, cy0 + 4, val, _font(12, bold=True), INK)


def _draw_regional_table(draw, x, y, w, regions, bands):
    col0 = x + 18
    label_w = 150
    grid_x = col0 + label_w
    grid_w = w - label_w - 36
    col_w = grid_w / len(bands)
    rh = 28
    for j, b in enumerate(bands):
        _center(draw, grid_x + j * col_w + col_w / 2, y, config.BAND_LABELS[b], _font(12, bold=True), INK)
    col_max = {b: max((regions[r][b] or 0) for r in regions) or 1e-9 for b in bands}
    ry = y + 24
    for r in regions:
        draw.text((col0, ry + 5), r, font=_font(12, bold=True), fill=INK)
        for j, b in enumerate(bands):
            v = regions[r][b] or 0.0
            cellx = grid_x + j * col_w
            _round_rect(draw, [cellx + 2, ry, cellx + col_w - 4, ry + rh - 5], 6, fill=_heat_color(v / col_max[b]))
            _center(draw, cellx + col_w / 2, ry + 5, "%.0f%%" % (v * 100), _font(11, bold=True), (255, 255, 255))
        ry += rh


def _draw_channel_table(draw, x, y, w, spec, channels, bands):
    col0 = x + 18
    name_w, domw = 88, 78
    grid_x = col0 + name_w
    grid_w = w - name_w - domw - 36
    col_w = grid_w / len(bands)
    draw.text((col0, y), "Kanal", font=_font(11, bold=True), fill=INK)
    for j, b in enumerate(bands):
        _center(draw, grid_x + j * col_w + col_w / 2, y, config.BAND_LABELS[b], _font(11, bold=True), INK)
    _center(draw, grid_x + grid_w + domw / 2, y, "Dom (Hz)", _font(11, bold=True), INK)
    ry = y + 22
    for idx, ch in enumerate(channels):
        if idx % 2 == 0:
            _round_rect(draw, [col0 - 6, ry - 1, x + w - 18, ry + 20], 6, fill=ROW_TINT)
        draw.text((col0, ry + 3), ch, font=_font(11, bold=True), fill=(55, 65, 81))
        rel = spec[ch]["relative"]
        top_band = max(bands, key=lambda bb: rel[bb])
        for j, b in enumerate(bands):
            bold = (b == top_band)
            _center(draw, grid_x + j * col_w + col_w / 2, ry + 3, "%.0f%%" % (rel[b] * 100),
                    _font(11, bold=bold), (BAND_COLORS[b] if bold else (75, 85, 99)))
        _center(draw, grid_x + grid_w + domw / 2, ry + 3, "%.1f" % spec[ch]["dominant"], _font(11), INK)
        ry += 22


def _draw_footer(draw, x, y, w, h, cls):
    _shadow(draw, [x, y, x + w, y + h], 16)
    _round_rect(draw, [x, y, x + w, y + h], 16, fill=(255, 251, 244), outline=(252, 230, 195), width=1)
    fy = y + 14
    if cls["atypical"]:
        draw.text((x + 18, fy), "!  Atipik naqsh: " + "; ".join(cls["atypical"]),
                  font=_font(12, bold=True), fill=(180, 95, 10))
        fy += 22
    for line in _wrap(config.DISCLAIMER, _font(11), draw, w - 36):
        draw.text((x + 18, fy), line, font=_font(11), fill=(133, 110, 75))
        fy += 16
    _right(draw, x + w - 18, y + h - 20, "© " + config.AUTHOR, _font(11, bold=True), MUTED)


def _wrap(text, font, draw, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if _text_w(draw, trial, font) > max_w and cur:
            lines.append(cur); cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ===========================================================================
# TAB (bo'lim) RASMLARI — GUI tablar uchun
# ===========================================================================
_W, _M, _GAP = 980, 28, 20
_CW = _W - 2 * _M


def _new_canvas(h):
    img = Image.new("RGB", (_W, int(h)), BG)
    return img, ImageDraw.Draw(img)


def build_overview_image(rec, spec, features, classification, topo_band="alpha"):
    h_header, h_state, h_feat, h_foot = 132, 64 + len(config.STATES) * 34, 64 + 6 * 28, 112
    H = _M + h_header + _GAP + h_state + _GAP + h_feat + _GAP + h_foot + _M
    img, draw = _new_canvas(H)
    summ = rec.summary(); cls = classification
    y = _M
    _draw_header(img, draw, _M, y, _CW, h_header, rec, cls, summ); y += h_header + _GAP
    top = _card(img, draw, _M, y, _CW, h_state, "Funksional holatlar (ball 0-100 / ishonch %)")
    _draw_state_bars(draw, _M, top, _CW, y + h_state - top - 8, cls["scores"], cls["probabilities"], cls["state"])
    y += h_state + _GAP
    top = _card(img, draw, _M, y, _CW, h_feat, "Diagnostik belgilar (features)")
    _draw_features_table(draw, _M, top, _CW, y + h_feat - top - 8, features); y += h_feat + _GAP
    _draw_footer(draw, _M, y, _CW, h_foot, cls)
    return img


def build_spectrum_image(rec, spec, features, classification, topo_band="alpha"):
    h_psd, h_bars = 392, 300
    H = _M + 48 + _GAP + h_psd + _GAP + h_bars + _M
    img, draw = _new_canvas(H)
    y = _section_title(img, draw, _M, _M, _CW, "Spektral tahlil") + _GAP
    rep_ch = next((c for c in ("O1", "O2", "Oz", "Pz", "P3", "P4") if c in spec), None) or list(spec.keys())[0]
    top = _card(img, draw, _M, y, _CW, h_psd, "Quvvat spektral zichligi (PSD) — kanal %s, Welch usuli" % rep_ch)
    _draw_psd(draw, _M + 8, top, _CW - 16, y + h_psd - top - 8, spec[rep_ch]["freqs"], spec[rep_ch]["psd"])
    y += h_psd + _GAP
    top = _card(img, draw, _M, y, _CW, h_bars, "Ritmlar bo'yicha nisbiy quvvat (global o'rtacha)")
    rp = {b: features["rp_%s" % b] for b in config.BANDS}
    _draw_band_bars(draw, _M, top, _CW, y + h_bars - top - 6, rp)
    return img


def build_topography_image(rec, spec, features, classification, topo_band="alpha"):
    regions = features.get("_regions") or {}
    bands = list(config.BANDS.keys())
    h_topo = 244
    h_reg = 56 + (len(regions) + 1) * 28 + 12 if regions else 0
    H = _M + 48 + _GAP + h_topo + _GAP + (h_reg + _GAP if h_reg else 0) + _M
    img, draw = _new_canvas(H)
    y = _section_title(img, draw, _M, _M, _CW, "Topografik tahlil (10-20 tizimi)") + _GAP
    top = _card(img, draw, _M, y, _CW, h_topo, "Ritmlar bo'yicha topografik xaritalar (nisbiy quvvat)")
    cell_w = (_CW - 24) / len(bands)
    for i, b in enumerate(bands):
        vals = {ch: spec[ch]["relative"][b] for ch in spec}
        _draw_topomap(img, draw, _M + 12 + i * cell_w, top, cell_w, y + h_topo - top - 8, vals,
                      caption=config.BAND_LABELS[b])
    y += h_topo + _GAP
    if regions:
        top = _card(img, draw, _M, y, _CW, h_reg, "Zonalar bo'yicha nisbiy quvvat")
        _draw_regional_table(draw, _M, top, _CW, regions, bands)
    return img


def build_channels_image(rec, spec, features, classification, topo_band="alpha"):
    bands = list(config.BANDS.keys())
    channels = [c for c in rec.channels if c in spec]
    h_chan = 56 + (len(channels) + 1) * 22 + 12
    H = _M + 48 + _GAP + h_chan + _M
    img, draw = _new_canvas(H)
    y = _section_title(img, draw, _M, _M, _CW, "Kanallar bo'yicha tahlil") + _GAP
    top = _card(img, draw, _M, y, _CW, h_chan, "Nisbiy quvvat va dominant chastota (eng kuchli ritm ajratilgan)")
    _draw_channel_table(draw, _M, top, _CW, spec, channels, bands)
    return img


def tab_images(rec, spec, features, classification, topo_band="alpha"):
    """GUI tablari uchun (nom, rasm) ro'yxatini qaytaradi."""
    return [
        ("Umumiy", build_overview_image(rec, spec, features, classification, topo_band)),
        ("Spektr (PSD)", build_spectrum_image(rec, spec, features, classification, topo_band)),
        ("Topografiya", build_topography_image(rec, spec, features, classification, topo_band)),
        ("Kanallar", build_channels_image(rec, spec, features, classification, topo_band)),
    ]


# ===========================================================================
# TO'LIQ POSTERLAR (PDF / HTML / yagona rasm uchun)
# ===========================================================================
def composite_report_image(rec, spec, features, classification, topo_band="alpha"):
    """Asosiy natijalarni bitta zamonaviy posterda jamlaydi (PDF 1-bo'lim)."""
    h_header, h_psd, h_mid = 132, 300, 322
    h_state = 64 + len(config.STATES) * 34
    h_feat = 64 + 6 * 28
    h_foot = 112
    H = (_M + h_header + _GAP + h_psd + _GAP + h_mid + _GAP + h_state
         + _GAP + h_feat + _GAP + h_foot + _M)
    img, draw = _new_canvas(H)
    summ = rec.summary(); cls = classification; f = features
    y = _M
    _draw_header(img, draw, _M, y, _CW, h_header, rec, cls, summ); y += h_header + _GAP
    rep_ch = next((c for c in ("O1", "O2", "Oz", "Pz", "P3", "P4") if c in spec), None) or list(spec.keys())[0]
    top = _card(img, draw, _M, y, _CW, h_psd, "Quvvat spektral zichligi (PSD) — kanal %s, Welch usuli" % rep_ch)
    _draw_psd(draw, _M + 8, top, _CW - 16, y + h_psd - top - 8, spec[rep_ch]["freqs"], spec[rep_ch]["psd"])
    y += h_psd + _GAP
    half = (_CW - _GAP) / 2
    top1 = _card(img, draw, _M, y, half, h_mid, "Ritmlar bo'yicha nisbiy quvvat")
    rp = {b: f["rp_%s" % b] for b in config.BANDS}
    _draw_band_bars(draw, _M, top1, half, y + h_mid - top1 - 6, rp)
    tx = _M + half + _GAP
    top2 = _card(img, draw, tx, y, half, h_mid, "Topografik xarita (%s)" % config.BAND_LABELS[topo_band])
    _draw_topomap(img, draw, tx, top2, half, y + h_mid - top2 - 6,
                  {ch: spec[ch]["relative"][topo_band] for ch in spec},
                  caption=config.BAND_LABELS[topo_band] + " nisbiy quvvati")
    y += h_mid + _GAP
    top3 = _card(img, draw, _M, y, _CW, h_state, "Funksional holatlar (ball 0-100 / ishonch %)")
    _draw_state_bars(draw, _M, top3, _CW, y + h_state - top3 - 8, cls["scores"], cls["probabilities"], cls["state"])
    y += h_state + _GAP
    top4 = _card(img, draw, _M, y, _CW, h_feat, "Diagnostik belgilar (features)")
    _draw_features_table(draw, _M, top4, _CW, y + h_feat - top4 - 8, f); y += h_feat + _GAP
    _draw_footer(draw, _M, y, _CW, h_foot, cls)
    return img


def composite_detail_image(rec, spec, features, classification):
    """Batafsil: ritmlar bo'yicha topomaplar + zona/kanal jadvallari (PDF 2-bo'lim)."""
    bands = list(config.BANDS.keys())
    regions = features.get("_regions") or {}
    channels = [c for c in rec.channels if c in spec]
    h_header, h_topo = 64, 236
    h_reg = 56 + (len(regions) + 1) * 28 + 12 if regions else 0
    h_chan = 56 + (len(channels) + 1) * 22 + 12
    H = _M + h_header + _GAP + h_topo + _GAP + (h_reg + _GAP if h_reg else 0) + h_chan + _M
    img, draw = _new_canvas(H)
    y = _M
    _shadow(draw, [_M, y, _M + _CW, y + h_header], 16)
    _gradient_card(img, [_M, y, _M + _CW, y + h_header], 16, (30, 41, 59), (51, 65, 85))
    draw.text((_M + 24, y + 19), "Batafsil zonaviy va kanal tahlili", font=_font(20, bold=True), fill=(255, 255, 255))
    _right(draw, _M + _CW - 22, y + 24, rec.meta.get("source_file", "?"), _font(13), (203, 213, 225))
    y += h_header + _GAP
    top = _card(img, draw, _M, y, _CW, h_topo, "Ritmlar bo'yicha topografik xaritalar (nisbiy quvvat)")
    cell_w = (_CW - 24) / len(bands)
    for i, b in enumerate(bands):
        _draw_topomap(img, draw, _M + 12 + i * cell_w, top, cell_w, y + h_topo - top - 8,
                      {ch: spec[ch]["relative"][b] for ch in spec}, caption=config.BAND_LABELS[b])
    y += h_topo + _GAP
    if regions:
        top = _card(img, draw, _M, y, _CW, h_reg, "Zonalar bo'yicha nisbiy quvvat (10-20 tizimi)")
        _draw_regional_table(draw, _M, top, _CW, regions, bands); y += h_reg + _GAP
    top = _card(img, draw, _M, y, _CW, h_chan, "Kanallar bo'yicha nisbiy quvvat va dominant chastota")
    _draw_channel_table(draw, _M, top, _CW, spec, channels, bands)
    return img


# ---------------------------------------------------------------------------
# Birlashtirish va A4 PDF
# ---------------------------------------------------------------------------
def _stack_vertical(images, gap=18, bg=None):
    bg = bg if bg is not None else BG
    if not images:
        return Image.new("RGB", (10, 10), bg)
    w = max(im.width for im in images)
    h = sum(im.height for im in images) + gap * (len(images) - 1)
    out = Image.new("RGB", (w, h), bg)
    yy = 0
    for im in images:
        out.paste(im, ((w - im.width) // 2, yy))
        yy += im.height + gap
    return out


def composite_full_image(rec, spec, features, classification, topo_band="alpha"):
    main = composite_report_image(rec, spec, features, classification, topo_band=topo_band)
    detail = composite_detail_image(rec, spec, features, classification)
    return _stack_vertical([main, detail], gap=18)


def _paginate_a4(poster, page_w=980, margin=26):
    page_h = int(page_w * 297.0 / 210.0)
    content_w = page_w - 2 * margin
    scale = content_w / poster.width
    scaled = poster.resize((content_w, max(1, int(poster.height * scale))), Image.LANCZOS)
    usable_h = page_h - 2 * margin
    pages = []
    top = 0
    while top < scaled.height:
        page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        slice_h = min(usable_h, scaled.height - top)
        page.paste(scaled.crop((0, top, scaled.width, top + slice_h)), (margin, margin))
        pages.append(page)
        top += usable_h
    return pages


def save_pdf(rec, spec, features, classification, path, topo_band="alpha"):
    """Ko'p sahifali PDF: 1-bo'lim asosiy hisobot, 2-bo'lim batafsil tahlil."""
    posters = [
        composite_report_image(rec, spec, features, classification, topo_band=topo_band),
        composite_detail_image(rec, spec, features, classification),
    ]
    pages = []
    for poster in posters:
        pages.extend(_paginate_a4(poster))
    if not pages:
        pages = [posters[0].convert("RGB")]
    first, rest = pages[0], pages[1:]
    first.save(path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    return path
