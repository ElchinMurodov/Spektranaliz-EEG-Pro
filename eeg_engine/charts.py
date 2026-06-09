"""
charts.py — Tahlil natijalarini CHIROYLI GRAFIK (rasm) ko'rinishida chizish.

Bu modul Pillow (PIL) yordamida quyidagi grafiklarni rasm sifatida chizadi
(matplotlib SHART EMAS):
  - PSD (quvvat spektral zichligi) egri chizig'i + ritm zonalari
  - Ritmlar bo'yicha nisbiy quvvat (ustun diagramma)
  - Topografik xarita (topomap) — bosh bo'ylab ritm taqsimoti
  - Funksional holatlar diagrammasi (8 holat, gorizontal ustunlar)
  - Belgilar jadvali (iAPF, FAA, FMT, dominant chastota, edge, ...)

`composite_report_image()` barchasini bitta chiroyli "poster" rasmga jamlaydi.
Bu rasm:
  - GUI "Natijalar oynasi" da ko'rsatiladi (varaqlanadigan),
  - PDF hisobot sifatida saqlanadi (PIL orqali).
"""

import os
import math

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Ranglar
# ---------------------------------------------------------------------------
BG = (238, 241, 245)
CARD = (255, 255, 255)
CARD_BORDER = (214, 222, 230)
INK = (33, 37, 41)
MUTED = (110, 120, 130)
ACCENT = (21, 101, 192)
ACCENT2 = (30, 136, 229)

BAND_COLORS = {
    "delta": (59, 111, 182),
    "theta": (76, 175, 154),
    "alpha": (124, 179, 66),
    "beta":  (249, 168, 37),
    "gamma": (224, 83, 61),
}

STATE_COLOR = (38, 116, 191)
STATE_TOP_COLOR = (224, 83, 61)

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

# Importni sikldan saqlash uchun config bu yerda import qilinadi
from . import config


# ---------------------------------------------------------------------------
# Shrift yuklash (turli OS uchun)
# ---------------------------------------------------------------------------
_FONT_CACHE = {}


def _font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = []
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
    w = _text_w(draw, text, font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def _heat_color(v):
    v = max(0.0, min(1.0, v))
    if v < 0.25:
        t = v / 0.25; r, g, b = 0, int(255 * t), 255
    elif v < 0.5:
        t = (v - 0.25) / 0.25; r, g, b = 0, 255, int(255 * (1 - t))
    elif v < 0.75:
        t = (v - 0.5) / 0.25; r, g, b = int(255 * t), 255, 0
    else:
        t = (v - 0.75) / 0.25; r, g, b = 255, int(255 * (1 - t)), 0
    return (r, g, b)


def _round_rect(draw, box, radius, fill=None, outline=None, width=1):
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        draw.rectangle(box, fill=fill, outline=outline, width=width)


def _card(draw, x, y, w, h, title=None):
    _round_rect(draw, [x, y, x + w, y + h], 14, fill=CARD, outline=CARD_BORDER, width=1)
    inner_top = y + 14
    if title:
        draw.text((x + 18, y + 14), title, font=_font(17, bold=True), fill=INK)
        draw.line([x + 18, y + 40, x + w - 18, y + 40], fill=(235, 239, 243), width=1)
        inner_top = y + 52
    return inner_top


# ---------------------------------------------------------------------------
# Alohida grafiklar
# ---------------------------------------------------------------------------
def _draw_psd(draw, x, y, w, h, freqs, psd, fmax=45.0):
    pad_l, pad_b, pad_r, pad_t = 52, 34, 16, 6
    px, py = x + pad_l, y + pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    pts = [(freqs[k], psd[k]) for k in range(len(freqs)) if freqs[k] <= fmax]
    if not pts:
        return
    pmax = max(p for _, p in pts) or 1e-12
    X = lambda fr: px + (fr / fmax) * pw
    Y = lambda p: py + ph - (p / pmax) * ph

    # ritm zonalari fon (och rangda)
    for name, (lo, hi) in config.BANDS.items():
        if lo > fmax:
            continue
        x0, x1 = X(lo), X(min(hi, fmax))
        c = BAND_COLORS[name]
        light = tuple(int(ci + (255 - ci) * 0.82) for ci in c)
        draw.rectangle([x0, py, x1, py + ph], fill=light)
        _center(draw, (x0 + x1) / 2, py + 3, name, _font(11), MUTED)

    # to'r va o'qlar
    for fr in range(0, int(fmax) + 1, 5):
        gx = X(fr)
        draw.line([gx, py, gx, py + ph], fill=(232, 236, 240), width=1)
        draw.line([gx, py + ph, gx, py + ph + 4], fill=(120, 130, 140), width=1)
        _center(draw, gx, py + ph + 8, str(fr), _font(11), INK)
    draw.line([px, py, px, py + ph], fill=(120, 130, 140), width=1)
    draw.line([px, py + ph, px + pw, py + ph], fill=(120, 130, 140), width=1)
    _center(draw, px + pw / 2, py + ph + 20, "Chastota (Hz)", _font(12, bold=True), INK)

    # PSD egri chizig'i
    line_pts = [(int(X(fr)), int(Y(p))) for fr, p in pts]
    if len(line_pts) >= 2:
        draw.line(line_pts, fill=ACCENT, width=2, joint="curve")


def _draw_band_bars(draw, x, y, w, h, rp):
    pad_l, pad_b, pad_t = 16, 40, 6
    px, py = x + pad_l, y + pad_t
    pw, ph = w - pad_l - 16, h - pad_t - pad_b
    bands = list(config.BANDS.keys())
    n = len(bands)
    gap = pw / n
    bw = gap * 0.58
    vmax = max(rp[b] for b in bands) or 1e-9
    draw.line([px, py + ph, px + pw, py + ph], fill=(120, 130, 140), width=1)
    for i, b in enumerate(bands):
        v = rp[b]
        bx = px + i * gap + (gap - bw) / 2
        bh = (v / vmax) * ph
        by = py + ph - bh
        _round_rect(draw, [bx, by, bx + bw, py + ph], 5, fill=BAND_COLORS[b])
        _center(draw, bx + bw / 2, by - 18, "%.1f%%" % (v * 100), _font(12, bold=True), INK)
        _center(draw, bx + bw / 2, py + ph + 6, config.BAND_LABELS[b], _font(12), INK)


def _draw_topomap(img, draw, x, y, w, h, channel_vals, caption=""):
    size = min(w, h) - 24
    cx = x + w / 2
    cy = y + 6 + size / 2
    R = size / 2
    draw.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(250, 250, 250), outline=(60, 64, 68), width=2)
    draw.polygon([(cx - 12, cy - R + 2), (cx + 12, cy - R + 2), (cx, cy - R - 16)],
                 fill=(250, 250, 250), outline=(60, 64, 68))
    draw.ellipse([cx - R - 7, cy - 16, cx - R + 5, cy + 16], fill=(250, 250, 250), outline=(60, 64, 68))
    draw.ellipse([cx + R - 5, cy - 16, cx + R + 7, cy + 16], fill=(250, 250, 250), outline=(60, 64, 68))
    vmax = max(channel_vals.values()) or 1e-9
    for ch, v in channel_vals.items():
        if ch not in SCALP_POS:
            continue
        ppx, ppy = SCALP_POS[ch]
        ex = cx + ppx * R * 0.9
        ey = cy - ppy * R * 0.9
        col = _heat_color(v / vmax)
        draw.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=col, outline=(50, 54, 58), width=1)
        _center(draw, ex, ey - 6, ch, _font(10, bold=True), (20, 20, 20))
    if caption:
        _center(draw, cx, y + h - 16, caption, _font(11), MUTED)


def _draw_state_bars(draw, x, y, w, h, scores, probs, top_state):
    px = x + 16
    py = y + 6
    label_w = 168
    bar_x = px + label_w
    bar_w = w - label_w - 84
    states = config.STATES
    row_h = (h - 12) / len(states)
    bh = min(20, row_h * 0.6)
    for i, st in enumerate(states):
        ry = py + i * row_h + (row_h - bh) / 2
        sc = scores.get(st, 0.0)
        pr = probs.get(st, 0.0)
        is_top = (st == top_state)
        draw.text((px, ry + bh / 2 - 8), st, font=_font(12, bold=is_top), fill=(INK if is_top else (70, 78, 86)))
        # fon trek
        _round_rect(draw, [bar_x, ry, bar_x + bar_w, ry + bh], bh / 2, fill=(235, 239, 243))
        fill_w = max(2, (sc / 100.0) * bar_w)
        col = STATE_TOP_COLOR if is_top else STATE_COLOR
        _round_rect(draw, [bar_x, ry, bar_x + fill_w, ry + bh], bh / 2, fill=col)
        draw.text((bar_x + bar_w + 8, ry + bh / 2 - 8),
                  "%.0f%%" % (pr * 100), font=_font(12, bold=is_top), fill=INK)


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
    col_w = w / 2
    per_col = (len(rows) + 1) // 2
    rh = 26
    for idx, (name, val) in enumerate(rows):
        col = idx // per_col
        row = idx % per_col
        cx0 = x + 16 + col * col_w
        cy0 = y + 6 + row * rh
        if row % 2 == 0:
            draw.rectangle([cx0 - 6, cy0 - 2, cx0 + col_w - 22, cy0 + rh - 4], fill=(247, 250, 252))
        draw.text((cx0, cy0), name, font=_font(12), fill=(70, 78, 86))
        vw = _text_w(draw, val, _font(12, bold=True))
        draw.text((cx0 + col_w - 34 - vw, cy0), val, font=_font(12, bold=True), fill=INK)


def _wrap(text, font, draw, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if _text_w(draw, trial, font) > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Asosiy: barcha grafiklarni bitta posterga jamlash
# ---------------------------------------------------------------------------
def composite_report_image(rec, spec, features, classification, topo_band="alpha"):
    """Barcha natijalarni chiroyli bitta rasmda (PIL Image, RGB) jamlaydi."""
    W = 960
    M = 26
    GAP = 18
    cw = W - 2 * M

    h_header = 104
    h_psd = 286
    h_mid = 300
    h_state = 70 + len(config.STATES) * 30
    h_feat = 64 + ((len(_FEATURE_ROWS_DUMMY) + 1) // 2) * 26
    h_foot = 96

    H = (M + h_header + GAP + h_psd + GAP + h_mid + GAP + h_state
         + GAP + h_feat + GAP + h_foot + M)

    img = Image.new("RGB", (W, int(H)), BG)
    draw = ImageDraw.Draw(img)

    summ = rec.summary()
    cls = classification
    f = features
    y = M

    # ---- Header ----
    _round_rect(draw, [M, y, M + cw, y + h_header], 14, fill=ACCENT)
    _round_rect(draw, [M, y, M + 8, y + h_header], 0, fill=(13, 71, 161))
    draw.text((M + 24, y + 16), "EEG Spektral Tahlil Hisoboti", font=_font(22, bold=True), fill=(255, 255, 255))
    fs_txt = ("%.0f Hz" % summ["fs"]) if summ["fs"] else "turlicha"
    sub = "Fayl: %s   •   Format: %s   •   %d kanal   •   %s   •   %.0f s" % (
        rec.meta.get("source_file", "?"), summ["format"], summ["channels"], fs_txt, summ["duration_sec"])
    draw.text((M + 24, y + 50), sub, font=_font(13), fill=(214, 230, 248))
    # holat + ishonch (o'ng tomonda)
    state_txt = cls["state"]
    conf_txt = "Ishonch: %.1f%%" % (cls["confidence"] * 100)
    sw = _text_w(draw, state_txt, _font(20, bold=True))
    draw.text((M + cw - sw - 24, y + 30), state_txt, font=_font(20, bold=True), fill=(255, 255, 255))
    cwid = _text_w(draw, conf_txt, _font(13))
    draw.text((M + cw - cwid - 24, y + 62), conf_txt, font=_font(13), fill=(214, 230, 248))
    y += h_header + GAP

    # ---- PSD ----
    rep_ch = None
    for pref in ("O1", "O2", "Oz", "Pz", "P3", "P4"):
        if pref in spec:
            rep_ch = pref
            break
    if rep_ch is None:
        rep_ch = list(spec.keys())[0]
    top = _card(draw, M, y, cw, h_psd, "Quvvat spektral zichligi (PSD) — kanal %s, Welch usuli" % rep_ch)
    _draw_psd(draw, M + 8, top, cw - 16, y + h_psd - top - 8, spec[rep_ch]["freqs"], spec[rep_ch]["psd"])
    y += h_psd + GAP

    # ---- O'rta qator: band bars (chap) + topomap (o'ng) ----
    half = (cw - GAP) / 2
    top1 = _card(draw, M, y, half, h_mid, "Ritmlar bo'yicha nisbiy quvvat")
    rp = {b: f["rp_%s" % b] for b in config.BANDS}
    _draw_band_bars(draw, M, top1, half, y + h_mid - top1 - 6, rp)

    tx = M + half + GAP
    top2 = _card(draw, tx, y, half, h_mid, "Topografik xarita (topomap)")
    topo_vals = {ch: spec[ch]["relative"][topo_band] for ch in spec}
    _draw_topomap(img, draw, tx, top2, half, y + h_mid - top2 - 6, topo_vals,
                  caption=config.BAND_LABELS[topo_band] + " nisbiy quvvati")
    y += h_mid + GAP

    # ---- Holatlar diagrammasi ----
    top3 = _card(draw, M, y, cw, h_state, "Funksional holatlar (ball 0-100 / ishonch %)")
    _draw_state_bars(draw, M, top3, cw, y + h_state - top3 - 8,
                     cls["scores"], cls["probabilities"], cls["state"])
    y += h_state + GAP

    # ---- Belgilar jadvali ----
    top4 = _card(draw, M, y, cw, h_feat, "Diagnostik belgilar (features)")
    _draw_features_table(draw, M, top4, cw, y + h_feat - top4 - 8, f)
    y += h_feat + GAP

    # ---- Footer (atipik + disclaimer) ----
    _round_rect(draw, [M, y, M + cw, y + h_foot], 14, fill=(255, 248, 240), outline=(245, 222, 190), width=1)
    fy = y + 12
    if cls["atypical"]:
        draw.text((M + 18, fy), "⚠ Atipik naqsh: " + "; ".join(cls["atypical"]),
                  font=_font(12, bold=True), fill=(180, 95, 10))
        fy += 22
    for line in _wrap(config.DISCLAIMER, _font(11), draw, cw - 36):
        draw.text((M + 18, fy), line, font=_font(11), fill=(120, 100, 70))
        fy += 16
    draw.text((M + 18, y + h_foot - 18), "© " + config.AUTHOR, font=_font(11, bold=True), fill=MUTED)

    return img


# Belgilar jadvali balandligini oldindan hisoblash uchun yordamchi ro'yxat
_FEATURE_ROWS_DUMMY = list(range(11))


# ---------------------------------------------------------------------------
# 2-sahifa: batafsil zonaviy va kanal tahlili (har bir ritm uchun topomap)
# ---------------------------------------------------------------------------
def composite_detail_image(rec, spec, features, classification):
    """Batafsil tahlil posteri: ritmlar bo'yicha topomaplar + zona/kanal jadvallari."""
    W = 960
    M = 26
    GAP = 18
    cw = W - 2 * M

    bands = list(config.BANDS.keys())
    regions = features.get("_regions") or {}
    channels = [c for c in rec.channels if c in spec]

    h_header = 60
    h_topo = 232
    h_reg = 52 + (len(regions) + 1) * 28 + 12 if regions else 0
    h_chan = 52 + (len(channels) + 1) * 22 + 12
    H = M + h_header + GAP + h_topo + GAP + (h_reg + GAP if h_reg else 0) + h_chan + M

    img = Image.new("RGB", (W, int(H)), BG)
    draw = ImageDraw.Draw(img)
    y = M

    # Header
    _round_rect(draw, [M, y, M + cw, y + h_header], 14, fill=(38, 50, 70))
    draw.text((M + 22, y + 16), "Batafsil zonaviy va kanal tahlili",
              font=_font(20, bold=True), fill=(255, 255, 255))
    src = rec.meta.get("source_file", "?")
    sw = _text_w(draw, src, _font(13))
    draw.text((M + cw - sw - 22, y + 22), src, font=_font(13), fill=(200, 214, 230))
    y += h_header + GAP

    # Ritmlar bo'yicha topomaplar (5 ta)
    top = _card(draw, M, y, cw, h_topo, "Ritmlar bo'yicha topografik xaritalar (nisbiy quvvat)")
    n = len(bands)
    cell_w = (cw - 24) / n
    for i, b in enumerate(bands):
        cx0 = M + 12 + i * cell_w
        vals = {ch: spec[ch]["relative"][b] for ch in spec}
        _draw_topomap(img, draw, cx0, top, cell_w, y + h_topo - top - 8, vals,
                      caption=config.BAND_LABELS[b])
    y += h_topo + GAP

    # Zonaviy jadval (zona x ritm, issiqlik-rangli kataklar)
    if regions:
        top = _card(draw, M, y, cw, h_reg, "Zonalar bo'yicha nisbiy quvvat (10-20 tizimi)")
        col0 = M + 18
        label_w = 150
        grid_x = col0 + label_w
        grid_w = cw - label_w - 36
        col_w = grid_w / len(bands)
        rh = 28
        # ustun sarlavhalari
        for j, b in enumerate(bands):
            _center(draw, grid_x + j * col_w + col_w / 2, top, config.BAND_LABELS[b], _font(12, bold=True), INK)
        # har ritm uchun maksimal (rang normallashtirish)
        col_max = {b: max((regions[r][b] or 0) for r in regions) or 1e-9 for b in bands}
        ry = top + 24
        for r in regions:
            draw.text((col0, ry + 4), r, font=_font(12, bold=True), fill=INK)
            for j, b in enumerate(bands):
                v = regions[r][b] or 0.0
                cellx = grid_x + j * col_w
                col = _heat_color(v / col_max[b])
                _round_rect(draw, [cellx + 2, ry, cellx + col_w - 4, ry + rh - 4], 4, fill=col)
                _center(draw, cellx + col_w / 2, ry + 4, "%.0f%%" % (v * 100), _font(11, bold=True), (25, 25, 25))
            ry += rh
        y += h_reg + GAP

    # Kanallar jadvali
    top = _card(draw, M, y, cw, h_chan, "Kanallar bo'yicha nisbiy quvvat va dominant chastota")
    col0 = M + 18
    name_w = 90
    domw = 80
    grid_x = col0 + name_w
    grid_w = cw - name_w - domw - 36
    col_w = grid_w / len(bands)
    # sarlavha
    draw.text((col0, top), "Kanal", font=_font(11, bold=True), fill=INK)
    for j, b in enumerate(bands):
        _center(draw, grid_x + j * col_w + col_w / 2, top, config.BAND_LABELS[b], _font(11, bold=True), INK)
    _center(draw, grid_x + grid_w + domw / 2, top, "Dom (Hz)", _font(11, bold=True), INK)
    ry = top + 22
    for idx, ch in enumerate(channels):
        if idx % 2 == 0:
            draw.rectangle([col0 - 6, ry - 1, M + cw - 18, ry + 20], fill=(247, 250, 252))
        draw.text((col0, ry + 2), ch, font=_font(11, bold=True), fill=(50, 58, 66))
        rel = spec[ch]["relative"]
        # eng kuchli ritmni ajratib ko'rsatamiz
        top_band = max(bands, key=lambda bb: rel[bb])
        for j, b in enumerate(bands):
            v = rel[b]
            bold = (b == top_band)
            _center(draw, grid_x + j * col_w + col_w / 2, ry + 2, "%.0f%%" % (v * 100),
                    _font(11, bold=bold), (BAND_COLORS[b] if bold else (70, 78, 86)))
        _center(draw, grid_x + grid_w + domw / 2, ry + 2, "%.1f" % spec[ch]["dominant"], _font(11), INK)
        ry += 22

    return img


# ---------------------------------------------------------------------------
# Rasmlarni birlashtirish va A4 PDF sahifalashtirish
# ---------------------------------------------------------------------------
def _stack_vertical(images, gap=16, bg=BG):
    """Bir nechta rasmni vertikal (ustma-ust) bitta rasmga birlashtiradi."""
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
    """Asosiy + batafsil posterlarni bitta (uzun) rasmda — GUI ko'rsatuvi uchun."""
    main = composite_report_image(rec, spec, features, classification, topo_band=topo_band)
    detail = composite_detail_image(rec, spec, features, classification)
    return _stack_vertical([main, detail], gap=18, bg=BG)


def _paginate_a4(poster, page_w=960, margin=24):
    """Bir posterni A4 nisbatidagi sahifalarga bo'ladi (RGB sahifalar ro'yxati)."""
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
        crop = scaled.crop((0, top, scaled.width, top + slice_h))
        page.paste(crop, (margin, margin))
        pages.append(page)
        top += usable_h
    return pages


def save_pdf(rec, spec, features, classification, path, topo_band="alpha"):
    """Ko'p sahifali PDF: 1-bo'lim asosiy hisobot, 2-bo'lim batafsil zonaviy tahlil."""
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
