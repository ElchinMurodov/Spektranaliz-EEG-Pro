"""
classifier.py — Funksional holatni aniqlash (qoidaviy ko'p belgili ball tizimi).

8 ta BIRLASHGAN holat (ikkala dastur to'plamining yig'indisi):
  Normal, Fokus, Charchoq, Uyquga moyillik, Uyqusizlik,
  Qo'zg'alish / Xayojonlanish, Stress, Meditativ.

Yondashuv ikkala dasturni birlashtiradi:
  - installation7: scale()/bell() asosida 0-100 vaznli ballar (engagement,
    spectral edge, dominant chastota bilan)
  - edf-bdf: indikatorlar + softmax ishonch darajasi + atipik naqsh aniqlash
    (FAA, FMT, iAPF, entropiya bilan)

MUHIM: chegaralar va vaznlar NAMUNAVIY (demonstratsion). Haqiqiy dissertatsiyada
ular yorliqlangan (ground-truth) ma'lumotlar asosida kalibrlanishi yoki
mashinaviy o'qitish (ML) klassifikatori bilan almashtirilishi mumkin.
"""

import math

from . import config


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def scale(value, low, high):
    """value ni [low, high] dan [0, 1] ga chiziqli o'tkazadi (cheklangan)."""
    if high == low:
        return 0.0
    return _clamp((value - low) / (high - low))


def bell(value, center, width):
    """Markazga yaqinlikni [0, 1] da baholaydi (uchburchak 'qo'ng'iroq')."""
    return _clamp(1.0 - abs(value - center) / width)


def score_states(f):
    """
    Har bir holat uchun 0-100 ball hisoblaydi (belgilarning vaznli yig'indisi).

    f — features.extract_features qaytargan belgilar dict.
    """
    alpha = f["rp_alpha"]
    beta = f["rp_beta"]
    theta = f["rp_theta"]
    delta = f["rp_delta"]
    gamma = f["rp_gamma"]
    low_freq = delta + theta            # sekin ritmlar
    fast_freq = beta + gamma            # tez ritmlar
    entropy = f["spectral_entropy"]
    dominant = f["dominant_frequency"]
    edge = f["spectral_edge_95"]
    alpha_beta = f["ratio_alpha_beta"]
    theta_beta = f["ratio_theta_beta"]
    beta_alpha = f["ratio_beta_alpha"]
    engagement = f["engagement"]
    fmt = f.get("fmt") if f.get("fmt") is not None else theta
    faa = f.get("faa") if f.get("faa") is not None else 0.0

    scores = {}

    # Normal — hech bir ritm haddan tashqari emas (muvozanat) + tabiiy alfa
    extremes = max(
        scale(low_freq, 0.45, 0.75),
        scale(beta, 0.30, 0.50),
        scale(gamma, 0.18, 0.35),
        scale(delta, 0.35, 0.60),
    )
    scores["Normal"] = 100 * (
        0.45 * (1 - extremes)
        + 0.25 * bell(alpha, 0.30, 0.22)
        + 0.15 * bell(dominant, 10.0, 5.0)
        + 0.15 * bell(entropy, 0.72, 0.28)
    )

    # Fokus — engagement va beta oshgan + frontal-median teta (FMT) + tartibli
    scores["Fokus"] = 100 * (
        0.30 * scale(engagement, 0.35, 0.95)
        + 0.25 * scale(beta, 0.18, 0.35)
        + 0.20 * scale(fmt, 0.18, 0.38)
        + 0.15 * scale(edge, 18.0, 32.0)
        + 0.10 * (1 - scale(theta, 0.20, 0.40))
    )

    # Charchoq — teta oshgan + sekinlashuv + beta pasaygan + theta/beta yuqori
    scores["Charchoq"] = 100 * (
        0.35 * scale(theta, 0.20, 0.40)
        + 0.25 * scale(theta_beta, 1.8, 5.0)
        + 0.20 * scale(low_freq, 0.42, 0.72)
        + 0.20 * (1 - scale(fast_freq, 0.20, 0.48))
    )

    # Uyquga moyillik — delta/teta ustun + alfa yo'qolishi (alpha dropout)
    scores["Uyquga moyillik"] = 100 * (
        0.40 * scale(delta, 0.30, 0.60)
        + 0.30 * scale(low_freq, 0.50, 0.80)
        + 0.30 * (1 - scale(alpha, 0.10, 0.30))
    )

    # Uyqusizlik (tinch holatda yuqori qo'zg'alish) — beta oshgan, alfa kam,
    # entropiya yuqori, dominant chastota yuqori (installation7 holati)
    scores["Uyqusizlik"] = 100 * (
        0.32 * scale(beta, 0.22, 0.45)
        + 0.24 * (1 - scale(alpha, 0.16, 0.40))
        + 0.22 * scale(entropy, 0.62, 0.92)
        + 0.12 * scale(gamma, 0.06, 0.20)
        + 0.10 * scale(dominant, 13.0, 25.0)
    )

    # Qo'zg'alish / Xayojonlanish — tez ritmlar va GAMMA kuchli + beta/alfa
    scores["Qo'zg'alish / Xayojonlanish"] = 100 * (
        0.34 * scale(fast_freq, 0.28, 0.55)
        + 0.30 * scale(gamma, 0.10, 0.30)
        + 0.22 * scale(beta_alpha, 0.8, 2.4)
        + 0.14 * scale(entropy, 0.60, 0.92)
    )

    # Stress — beta/alfa yuqori + spektral chegara yuqori + FAA o'ngga + teta
    scores["Stress"] = 100 * (
        0.34 * scale(beta_alpha, 0.9, 2.8)
        + 0.22 * scale(edge, 20.0, 35.0)
        + 0.18 * scale(faa, 0.0, 0.35)
        + 0.14 * scale(gamma, 0.06, 0.22)
        + 0.12 * (1 - scale(alpha, 0.18, 0.40))
    )

    # Meditativ — alfa va teta birga yuqori + alfa/beta yuqori + past entropiya
    scores["Meditativ"] = 100 * (
        0.35 * scale(alpha + theta, 0.42, 0.72)
        + 0.22 * scale(alpha_beta, 1.3, 4.0)
        + 0.18 * (1 - scale(beta, 0.16, 0.35))
        + 0.15 * bell(dominant, 9.5, 5.0)
        + 0.10 * (1 - scale(entropy, 0.55, 0.85))
    )

    return {name: round(_clamp(v, 0.0, 100.0), 1) for name, v in scores.items()}


def _softmax(scores, temp=8.0):
    """0-100 ballardan ishonch ehtimolliklari (yumshoq tanlov)."""
    keys = list(scores.keys())
    mx = max(scores.values())
    exps = [math.exp((scores[k] - mx) / temp) for k in keys]
    tot = sum(exps) or 1.0
    return {keys[i]: exps[i] / tot for i in range(len(keys))}


def detect_atypical(f):
    """G'ayritabiiy (atipik) naqshni belgilaydi — TASHXIS EMAS, ogohlantirish."""
    reasons = []
    if f["rp_delta"] > 0.55:
        reasons.append("delta ritmining kuchli ustunligi")
    if f["rp_gamma"] > 0.35:
        reasons.append("gamma diapazonida haddan tashqari quvvat (mushak shovqini ehtimoli)")
    if max(f["rp_delta"], f["rp_theta"], f["rp_alpha"],
           f["rp_beta"], f["rp_gamma"]) > 0.70:
        reasons.append("bitta ritmning haddan tashqari dominantligi")
    faa = f.get("faa")
    if faa is not None and abs(faa) > 0.8:
        reasons.append("kuchli frontal alfa asimmetriyasi")
    return reasons


def classify(features):
    """
    Belgilar asosida funksional holatni aniqlaydi.

    Qaytaradi: dict {
        "state", "confidence", "scores" (0-100), "probabilities" (softmax),
        "atypical" (sabablar ro'yxati)
    }
    """
    scores = score_states(features)
    probs = _softmax(scores)
    state = max(scores, key=scores.get)
    return {
        "state": state,
        "confidence": probs[state],
        "scores": scores,
        "probabilities": probs,
        "atypical": detect_atypical(features),
    }
