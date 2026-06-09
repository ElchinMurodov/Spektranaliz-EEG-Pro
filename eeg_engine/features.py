"""
features.py — EEG dan diagnostik belgilarni (features) ajratish.

Bu modul IKKALA dasturning barcha belgilarini birlashtiradi:

  EEG-signal-edf-bdf dan (zona/kanal asosida):
    - iAPF  — individual alfa cho'qqi chastotasi
    - FAA   — frontal alfa asimmetriyasi (stress/emotsiya markeri)
    - FMT   — frontal-median teta (diqqat/fokus markeri)
    - theta/alpha nisbati

  Spektranaliz-EEG-installation7 dan (global spektral):
    - dominant chastota (PSD bo'yicha)
    - dominant chastota (xom FFT bo'yicha)
    - spektral chegara (spectral edge 95%)
    - beta/alpha nisbati
    - engagement (jalb qilinganlik) indeksi = beta / (alpha + theta)

  Umumiy (har ikkisida):
    - nisbiy quvvatlar (RP): delta, theta, alpha, beta, gamma
    - alpha/beta, theta/beta nisbatlari
    - spektral entropiya
"""

from . import config


def _safe_div(a, b, eps=1e-9):
    return a / (b + eps)


def _channels_in_region(rec, region_name):
    wanted = set(config.REGIONS.get(region_name, []))
    return [c for c in rec.channels if c in wanted]


def _region_relative(spec, channels, band_name):
    vals = [spec[c]["relative"][band_name] for c in channels if c in spec]
    return sum(vals) / len(vals) if vals else None


def _region_absolute(spec, channels, band_name):
    vals = [spec[c]["absolute"][band_name] for c in channels if c in spec]
    return sum(vals) / len(vals) if vals else None


def individual_alpha_peak(freqs, psd, search=(7.0, 14.0)):
    """Alfa diapazonida (7-14 Hz) PSD maksimumiga mos chastota (iAPF)."""
    lo, hi = search
    best_f, best_p = None, -1.0
    for k in range(len(freqs)):
        if lo <= freqs[k] <= hi and psd[k] > best_p:
            best_p, best_f = psd[k], freqs[k]
    return best_f if best_f is not None else 10.0


def frontal_alpha_asymmetry(rec, spec):
    """FAA = ln(alfa_o'ng) - ln(alfa_chap). Kanallar yetmasa None."""
    import math
    left = [c for c in config.FRONTAL_LEFT if c in spec]
    right = [c for c in config.FRONTAL_RIGHT if c in spec]
    if not left or not right:
        return None
    la = _region_absolute(spec, left, "alpha")
    ra = _region_absolute(spec, right, "alpha")
    if not la or not ra:
        return None
    return math.log(ra + 1e-12) - math.log(la + 1e-12)


def frontal_midline_theta(rec, spec):
    """FMT — Fz kanalidagi nisbiy teta (bo'lmasa frontal zona o'rtachasi)."""
    fz = config.FRONTAL_MIDLINE
    if fz in spec:
        return spec[fz]["relative"]["theta"]
    fch = _channels_in_region(rec, "frontal")
    return _region_relative(spec, fch, "theta")


def region_summary(rec, spec):
    """Har zona uchun nisbiy band quvvatlari o'rtachasi (hisobot uchun)."""
    out = {}
    for region in config.REGIONS:
        chans = _channels_in_region(rec, region)
        if not chans:
            continue
        out[region] = {b: _region_relative(spec, chans, b) for b in config.BANDS}
    return out


def extract_features(rec, spec):
    """
    Butun yozuv bo'yicha yagona belgilar vektorini (dict) qaytaradi.

    Nisbiy quvvatlar va global spektral ko'rsatkichlar kanallar bo'yicha
    o'rtachalanadi; iAPF oksipital, FAA/FMT frontal kanallardan olinadi.
    """
    chans = [c for c in rec.channels if c in spec]
    if not chans:
        raise ValueError("Spektral natija bo'sh — belgilar ajratilmadi.")

    def avg(key_fn):
        vals = [key_fn(c) for c in chans]
        return sum(vals) / len(vals)

    rp = {b: avg(lambda c, b=b: spec[c]["relative"][b]) for b in config.BANDS}

    # iAPF — oksipital kanallar bo'yicha (bo'lmasa, hammasi)
    occ = [c for c in config.OCCIPITAL if c in spec]
    iapf_src = occ if occ else chans
    iapf = sum(individual_alpha_peak(spec[c]["freqs"], spec[c]["psd"])
               for c in iapf_src) / len(iapf_src)

    entropy = avg(lambda c: spec[c]["entropy"])
    dominant = avg(lambda c: spec[c]["dominant"])
    fft_dominant = avg(lambda c: spec[c]["fft_dominant"])
    edge95 = avg(lambda c: spec[c]["edge95"])

    feats = {
        # nisbiy quvvatlar
        "rp_delta": rp["delta"],
        "rp_theta": rp["theta"],
        "rp_alpha": rp["alpha"],
        "rp_beta": rp["beta"],
        "rp_gamma": rp["gamma"],
        # nisbatlar (ikkala dastur birlashmasi)
        "ratio_alpha_beta": _safe_div(rp["alpha"], rp["beta"]),
        "ratio_theta_beta": _safe_div(rp["theta"], rp["beta"]),
        "ratio_theta_alpha": _safe_div(rp["theta"], rp["alpha"]),
        "ratio_beta_alpha": _safe_div(rp["beta"], rp["alpha"]),
        "engagement": _safe_div(rp["beta"], rp["alpha"] + rp["theta"]),
        # zona asosidagi belgilar (edf-bdf)
        "iapf": iapf,
        "faa": frontal_alpha_asymmetry(rec, spec),
        "fmt": frontal_midline_theta(rec, spec),
        # global spektral belgilar (installation7)
        "spectral_entropy": entropy,
        "dominant_frequency": dominant,
        "fft_dominant_frequency": fft_dominant,
        "spectral_edge_95": edge95,
    }
    feats["_regions"] = region_summary(rec, spec)
    return feats
