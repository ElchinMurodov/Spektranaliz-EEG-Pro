"""
calibration.py — Individual kalibrlash (baseline normalizatsiya). ILMIY YANGILIK.

Muammo: har bir insonning "tinch holat" EEG spektri tabiatan farq qiladi.
Qat'iy (absolyut) chegaralar shu sababli xato natija berishi mumkin.

Yechim: avval sportchining TINCH HOLATDAGI yozuvidan shaxsiy "baseline"
hisoblanadi. Keyingi yozuvlar shu bazaga NISBATAN baholanadi (chetlanish).

Foydalanish:
    base = calibration.compute_baseline("dam_olish.edf")
    natija = pipeline.analyze_file("mashqdan_keyin.edf", baseline=base)
"""

from . import loader, preprocessing, spectral, features as feat_mod


# Neytral (markaziy) qiymatlar — chetlanish shularga nisbatan markazlashtiriladi
NEUTRAL = {
    "rp_delta": 0.20, "rp_theta": 0.18, "rp_alpha": 0.22,
    "rp_beta": 0.20, "rp_gamma": 0.06,
    "fmt": 0.18, "faa": 0.0, "spectral_entropy": 0.80,
}

_CORRECTABLE = list(NEUTRAL.keys())


def _safe_div(a, b, eps=1e-9):
    return a / (b + eps)


def compute_baseline(path, fs=None, target_fs=None, notch=True):
    """Tinch holatdagi yozuvdan shaxsiy baseline (belgilar) ni hisoblaydi."""
    rec = loader.load(path, fs=fs)
    preprocessing.preprocess(rec, target_fs=target_fs, notch=notch)
    spec = spectral.analyze_recording(rec)
    return feat_mod.extract_features(rec, spec)


def apply_baseline(features, baseline):
    """
    Belgilar vektorini baseline ga nisbatan markazlashtiradi:
        yangi = NEYTRAL + (joriy - baseline)
    Agar joriy qiymat baseline bilan teng bo'lsa, natija neytral bo'ladi.
    """
    out = dict(features)
    for k in _CORRECTABLE:
        cur = features.get(k)
        base = baseline.get(k)
        if cur is None or base is None:
            continue
        out[k] = NEUTRAL[k] + (cur - base)

    # Nisbatlarni tuzatilgan nisbiy quvvatlardan qayta hisoblash
    out["ratio_alpha_beta"] = _safe_div(out["rp_alpha"], out["rp_beta"])
    out["ratio_theta_beta"] = _safe_div(out["rp_theta"], out["rp_beta"])
    out["ratio_theta_alpha"] = _safe_div(out["rp_theta"], out["rp_alpha"])
    out["ratio_beta_alpha"] = _safe_div(out["rp_beta"], out["rp_alpha"])
    out["engagement"] = _safe_div(out["rp_beta"], out["rp_alpha"] + out["rp_theta"])
    out["_calibrated"] = True
    return out
