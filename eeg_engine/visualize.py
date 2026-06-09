"""
visualize.py — Tahlil natijalarini vizual (HTML + SVG) hisobotga aylantirish.

EEG-signal-edf-bdf dasturidan olingan va kengaytirilgan: barcha grafiklar
toza Python orqali SVG (vektor grafika) ko'rinishida yaratiladi (matplotlib
shart emas) va HTML faylga joylanadi — istalgan brauzerda ochiladi.

Grafiklar:
  - PSD chizig'i (quvvat spektral zichligi) + ritm zonalari
  - Ritmlar bo'yicha nisbiy quvvat (ustun diagramma)
  - Topografik xarita (topomap) — bosh bo'ylab tanlangan ritm taqsimoti
  - Holat ehtimolliklari (8 holat) diagrammasi
  - To'liq belgilar jadvali (iAPF, FAA, FMT, dominant, edge, engagement, ...)
"""

from . import config


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

BAND_COLORS = {
    "delta": "#3b6fb6", "theta": "#4caf9a", "alpha": "#7cb342",
    "beta": "#f9a825", "gamma": "#e0533d",
}


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
    return "#%02x%02x%02x" % (r, g, b)


def _psd_svg(freqs, psd, width=560, height=240, fmax=45.0):
    pad_l, pad_b, pad_t, pad_r = 50, 30, 20, 15
    pw, ph = width - pad_l - pad_r, height - pad_b - pad_t
    pts = [(freqs[k], psd[k]) for k in range(len(freqs)) if freqs[k] <= fmax]
    if not pts:
        return ""
    pmax = max(p for _, p in pts) or 1e-12
    X = lambda fr: pad_l + (fr / fmax) * pw
    Y = lambda p: pad_t + ph - (p / pmax) * ph
    el = ['<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg">' % (width, height)]
    for name, (lo, hi) in config.BANDS.items():
        if lo > fmax:
            continue
        x0, x1 = X(lo), X(min(hi, fmax))
        el.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" opacity="0.10"/>'
                  % (x0, pad_t, x1 - x0, ph, BAND_COLORS[name]))
        el.append('<text x="%.1f" y="%d" font-size="9" fill="#666" text-anchor="middle">%s</text>'
                  % ((x0 + x1) / 2, pad_t + 11, name))
    el.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (pad_l, pad_t + ph, pad_l + pw, pad_t + ph))
    el.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>' % (pad_l, pad_t, pad_l, pad_t + ph))
    for fr in range(0, int(fmax) + 1, 5):
        x = X(fr)
        el.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#aaa"/>' % (x, pad_t + ph, x, pad_t + ph + 4))
        el.append('<text x="%.1f" y="%d" font-size="9" fill="#333" text-anchor="middle">%d</text>' % (x, pad_t + ph + 16, fr))
    el.append('<text x="%d" y="%d" font-size="10" fill="#333" text-anchor="middle">Chastota (Hz)</text>' % (pad_l + pw / 2, height - 2))
    path = " ".join("%.1f,%.1f" % (X(fr), Y(p)) for fr, p in pts)
    el.append('<polyline points="%s" fill="none" stroke="#1565c0" stroke-width="1.8"/>' % path)
    el.append('</svg>')
    return "".join(el)


def _bars_svg(values, colors=None, width=560, height=200, fmt="{:.0f}%", scale=100):
    pad_l, pad_b, pad_t = 20, 46, 20
    n = len(values) or 1
    pw, ph = width - pad_l - 20, height - pad_b - pad_t
    gap = pw / n
    bw = gap * 0.6
    vmax = max(values.values()) or 1.0
    el = ['<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg">' % (width, height)]
    for i, (name, v) in enumerate(values.items()):
        x = pad_l + i * gap + (gap - bw) / 2
        h = (v / vmax) * ph
        y = pad_t + ph - h
        c = (colors or {}).get(name, "#1565c0")
        el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="2"/>' % (x, y, bw, h, c))
        el.append('<text x="%.1f" y="%.1f" font-size="10" fill="#222" text-anchor="middle">%s</text>'
                  % (x + bw / 2, y - 4, fmt.format(v * scale)))
        label = name if len(name) <= 12 else name[:11] + "."
        el.append('<text x="%.1f" y="%d" font-size="8.5" fill="#444" text-anchor="middle">%s</text>'
                  % (x + bw / 2, pad_t + ph + 14, label))
    el.append('</svg>')
    return "".join(el)


def _topomap_svg(channel_values, size=300):
    R = size / 2 - 24
    cx = cy = size / 2
    el = ['<svg viewBox="0 0 %d %d" width="%d" xmlns="http://www.w3.org/2000/svg">' % (size, size, size)]
    el.append('<circle cx="%d" cy="%d" r="%d" fill="#fafafa" stroke="#333" stroke-width="1.5"/>' % (cx, cy, R))
    el.append('<polygon points="%d,%d %d,%d %d,%d" fill="#fafafa" stroke="#333" stroke-width="1.5"/>'
              % (cx - 10, cy - R, cx + 10, cy - R, cx, cy - R - 16))
    el.append('<ellipse cx="%d" cy="%d" rx="6" ry="14" fill="#fafafa" stroke="#333"/>' % (cx - R, cy))
    el.append('<ellipse cx="%d" cy="%d" rx="6" ry="14" fill="#fafafa" stroke="#333"/>' % (cx + R, cy))
    for ch, v in channel_values.items():
        if ch not in SCALP_POS:
            continue
        px, py = SCALP_POS[ch]
        ex = cx + px * R * 0.92
        ey = cy - py * R * 0.92
        el.append('<circle cx="%.1f" cy="%.1f" r="13" fill="%s" stroke="#333" stroke-width="0.8"/>'
                  % (ex, ey, _heat_color(v)))
        el.append('<text x="%.1f" y="%.1f" font-size="8" fill="#000" text-anchor="middle">%s</text>'
                  % (ex, ey + 3, ch))
    el.append('</svg>')
    return "".join(el)


def build_html(rec, spec, features, classification, topo_band="alpha"):
    """To'liq HTML hisobotni (str) qaytaradi."""
    summ = rec.summary()
    cls = classification
    f = features

    rep_ch = None
    for pref in ("O1", "Oz", "Pz", "O2"):
        if pref in spec:
            rep_ch = pref
            break
    if rep_ch is None:
        rep_ch = list(spec.keys())[0]
    psd_svg = _psd_svg(spec[rep_ch]["freqs"], spec[rep_ch]["psd"])

    band_vals = {b: f["rp_%s" % b] for b in config.BANDS}
    bars_svg = _bars_svg(band_vals, colors=BAND_COLORS)

    topo_vals = {ch: spec[ch]["relative"][topo_band] for ch in spec}
    tmax = max(topo_vals.values()) or 1.0
    topo_svg = _topomap_svg({ch: topo_vals[ch] / tmax for ch in topo_vals})

    prob_bars = _bars_svg(cls["probabilities"], fmt="{:.0f}%")

    atypical_html = ""
    if cls["atypical"]:
        items = "".join("<li>%s</li>" % r for r in cls["atypical"])
        atypical_html = ('<div class="warn"><b>&#9888; Atipik naqsh belgilari:</b><ul>%s</ul>'
                         '<i>Mutaxassis (nevrolog) ko\'rigi tavsiya etiladi.</i></div>' % items)

    faa = f.get("faa")
    fmt_v = f.get("fmt")
    harm = ""
    if rec.meta.get("harmonized_fs"):
        harm = " &bull; harmonizatsiya: %.0f Hz" % rec.meta["harmonized_fs"]

    html = """<!DOCTYPE html>
<html lang="uz"><head><meta charset="utf-8">
<title>EEG Tahlil Hisoboti - {state}</title>
<style>
  body {{ font-family: Segoe UI, Roboto, Arial, sans-serif; margin:0; background:#eef1f5; color:#222; }}
  .wrap {{ max-width: 920px; margin:0 auto; padding:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:#666; font-size:13px; margin-bottom:18px; }}
  .card {{ background:#fff; border-radius:10px; padding:18px 20px; margin-bottom:18px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .result {{ background:linear-gradient(135deg,#1565c0,#1e88e5); color:#fff; }}
  .result .big {{ font-size:30px; font-weight:700; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  td,th {{ padding:5px 8px; border-bottom:1px solid #eee; text-align:left; }}
  .warn {{ background:#fff3e0; border-left:4px solid #f9a825; padding:10px 14px; border-radius:6px; margin-bottom:18px; }}
  .disc {{ font-size:12px; color:#777; border-top:1px solid #ddd; padding-top:10px; }}
  h3 {{ font-size:14px; margin:0 0 8px; color:#444; }}
  @media(max-width:720px){{ .grid{{grid-template-columns:1fr;}} }}
</style></head><body><div class="wrap">

<h1>EEG Spektral Tahlil Hisoboti</h1>
<div class="sub">Manba: {src} &bull; Format: {fmt} &bull; {nch} kanal &bull; {fs} Hz &bull; {dur} s{harm}</div>

<div class="card result">
  <div>Aniqlangan funksional holat:</div>
  <div class="big">{state}</div>
  <div>Ishonch darajasi: {conf:.1f}%</div>
</div>

{atypical}

<div class="grid">
  <div class="card"><h3>Holat ehtimolliklari (8 holat)</h3>{prob_bars}</div>
  <div class="card"><h3>Topografik xarita ({topo_band} nisbiy quvvati)</h3>{topo}</div>
</div>

<div class="card"><h3>Quvvat spektral zichligi - kanal {rep_ch} (Welch)</h3>{psd}</div>

<div class="card"><h3>Ritmlar bo'yicha nisbiy quvvat (global o'rtacha)</h3>{bars}</div>

<div class="card"><h3>Diagnostik belgilar</h3>
<table>
  <tr><th>Belgi</th><th>Qiymat</th></tr>
  <tr><td>iAPF (individual alfa cho'qqisi)</td><td>{iapf:.2f} Hz</td></tr>
  <tr><td>Dominant chastota (PSD)</td><td>{dom:.2f} Hz</td></tr>
  <tr><td>Dominant chastota (FFT)</td><td>{fdom:.2f} Hz</td></tr>
  <tr><td>Spektral chegara (edge 95%)</td><td>{edge:.2f} Hz</td></tr>
  <tr><td>Alpha / Beta nisbati</td><td>{ab:.3f}</td></tr>
  <tr><td>Theta / Beta nisbati</td><td>{tb:.3f}</td></tr>
  <tr><td>Beta / Alpha nisbati</td><td>{ba:.3f}</td></tr>
  <tr><td>Engagement (jalb) indeksi</td><td>{eng:.3f}</td></tr>
  <tr><td>Frontal alfa asimmetriyasi (FAA)</td><td>{faa}</td></tr>
  <tr><td>Frontal-median teta (FMT)</td><td>{fmtval}</td></tr>
  <tr><td>Spektral entropiya</td><td>{ent:.3f}</td></tr>
</table></div>

<div class="card disc">{disclaimer}<br><br>(c) {author}</div>

</div></body></html>"""

    return html.format(
        state=cls["state"], conf=cls["confidence"] * 100,
        src=rec.meta.get("source_file", "?"), fmt=summ["format"],
        nch=summ["channels"], fs=summ["fs"] or "turlicha", dur=summ["duration_sec"], harm=harm,
        atypical=atypical_html, prob_bars=prob_bars, topo=topo_svg, topo_band=topo_band,
        psd=psd_svg, rep_ch=rep_ch, bars=bars_svg,
        iapf=f["iapf"], dom=f["dominant_frequency"], fdom=f["fft_dominant_frequency"],
        edge=f["spectral_edge_95"], ab=f["ratio_alpha_beta"], tb=f["ratio_theta_beta"],
        ba=f["ratio_beta_alpha"], eng=f["engagement"],
        faa=("%.3f" % faa) if faa is not None else "&mdash;",
        fmtval=("%.3f" % fmt_v) if fmt_v is not None else "&mdash;",
        ent=f["spectral_entropy"], disclaimer=config.DISCLAIMER, author=config.AUTHOR,
    )
