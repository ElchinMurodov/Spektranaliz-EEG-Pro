"""
report.py — Tahlil natijalarini matnli hisobot ko'rinishida shakllantirish.

Ikkala dasturning chiqaruvchi natijalari birlashtirilgan:
  - Yozuv ma'lumotlari (fayl, format, kanallar, fs, davomiylik)
  - Holatlar bo'yicha ballar (0-100) va softmax ishonch ehtimolliklari
  - Chastota diapazonlari bo'yicha quvvat (nisbiy %)
  - To'liq spektral belgilar to'plami (iAPF, FAA, FMT, engagement,
    dominant chastota PSD/FFT, spectral edge, entropiya, nisbatlar)
  - Atipik naqsh ogohlantirishlari
  - Majburiy DISCLAIMER

Ikki ko'rinishda chiqariladi: GUI uchun ixcham, terminal uchun bezakli.
"""

from . import config


def _bar(value, width=18):
    v = max(0.0, min(1.0, value))
    n = int(round(v * width))
    return "#" * n + "-" * (width - n)


def build_report(rec, spec, features, classification, calibrated=False, fancy=True):
    """To'liq matnli hisobotni (str) qaytaradi."""
    L = []
    A = L.append
    summ = rec.summary()
    f = features
    cls = classification
    sep = "=" * 60
    sub = "-" * 60

    A(sep)
    A("  EEG SPEKTRAL TAHLIL HISOBOTI")
    A("  (Sportchining EEG signallarini spektral tahlil qilish)")
    A(sep)

    # --- Yozuv ---
    A("")
    A("YOZUV MA'LUMOTLARI")
    A(sub)
    A("  Fayl              : %s" % rec.meta.get("source_file", "?"))
    A("  Format            : %s" % summ["format"])
    A("  O'qish usuli       : %s" % summ.get("reader", "?"))
    A("  Kanallar soni     : %d" % summ["channels"])
    fs = summ["fs"]
    A("  Namuna chastotasi : %s Hz" % (("%.2f" % fs) if fs else "turlicha"))
    if rec.meta.get("harmonized_fs"):
        A("  Harmonizatsiya    : %.2f Hz ga keltirildi" % rec.meta["harmonized_fs"])
    A("  Davomiyligi       : %.2f s" % summ["duration_sec"])
    if calibrated:
        A("  Kalibrlash        : individual baseline qo'llanildi")
    chs = ", ".join(summ["channel_names"][:24])
    if len(summ["channel_names"]) > 24:
        chs += ", ..."
    A("  Kanallar          : %s" % chs)

    # --- Yakuniy holat ---
    A("")
    A(sep)
    A("  YAKUNIY BAHOLANGAN HOLAT : %s" % cls["state"])
    A("  ISHONCH DARAJASI         : %.1f%%" % (cls["confidence"] * 100))
    A(sep)

    # --- Holat ballari ---
    A("")
    A("HOLATLAR BO'YICHA INDEKSLAR (ball 0-100 / ishonch %)")
    A(sub)
    scores = cls["scores"]
    probs = cls["probabilities"]
    for st in config.STATES:
        sc = scores.get(st, 0.0)
        pr = probs.get(st, 0.0)
        mark = "  <== eng yuqori" if st == cls["state"] else ""
        A("  %-26s %5.1f  | %4.1f%%  %s%s" % (st, sc, pr * 100, _bar(pr) if fancy else "", mark))

    # --- Band quvvatlari ---
    A("")
    A("CHASTOTA DIAPAZONLARI BO'YICHA QUVVAT (nisbiy %, kanallar o'rtachasi)")
    A(sub)
    for b in config.BANDS:
        lo, hi = config.BANDS[b]
        rp = f["rp_%s" % b]
        A("  %-6s (%4.1f-%4.1f Hz): %5.1f%%  %s"
          % (config.BAND_LABELS[b], lo, hi, rp * 100, _bar(rp) if fancy else ""))

    # --- Spektral belgilar ---
    A("")
    A("SPEKTRAL BELGILAR (features)")
    A(sub)
    A("  iAPF (individual alfa cho'qqisi) : %.2f Hz" % f["iapf"])
    A("  Dominant chastota (PSD)          : %.2f Hz" % f["dominant_frequency"])
    A("  Dominant chastota (FFT)          : %.2f Hz" % f["fft_dominant_frequency"])
    A("  Spektral chegara (edge 95%%)      : %.2f Hz" % f["spectral_edge_95"])
    A("  Alpha/Beta nisbati               : %.3f" % f["ratio_alpha_beta"])
    A("  Theta/Beta nisbati               : %.3f" % f["ratio_theta_beta"])
    A("  Theta/Alpha nisbati              : %.3f" % f["ratio_theta_alpha"])
    A("  Beta/Alpha nisbati               : %.3f" % f["ratio_beta_alpha"])
    A("  Engagement (jalb) indeksi        : %.3f" % f["engagement"])
    faa = f.get("faa")
    A("  Frontal alfa asimmetriyasi (FAA) : %s"
      % (("%.3f" % faa) if faa is not None else "kanallar yetarli emas"))
    fmt = f.get("fmt")
    A("  Frontal-median teta (FMT)        : %s"
      % (("%.3f" % fmt) if fmt is not None else "Fz topilmadi"))
    A("  Spektral entropiya               : %.3f" % f["spectral_entropy"])

    # --- Zonalar ---
    regions = f.get("_regions") or {}
    if regions:
        A("")
        A("ZONALAR BO'YICHA NISBIY QUVVAT (10-20 tizimi)")
        A(sub)
        A("  %-10s %6s %6s %6s %6s %6s" % ("Zona", "Delta", "Theta", "Alpha", "Beta", "Gamma"))
        for region, vals in regions.items():
            A("  %-10s %5.0f%% %5.0f%% %5.0f%% %5.0f%% %5.0f%%" % (
                region,
                (vals["delta"] or 0) * 100, (vals["theta"] or 0) * 100,
                (vals["alpha"] or 0) * 100, (vals["beta"] or 0) * 100,
                (vals["gamma"] or 0) * 100))

    # --- Atipik ---
    if cls["atypical"]:
        A("")
        A("  [!] ATIPIK NAQSH BELGILARI:")
        for r in cls["atypical"]:
            A("      - %s" % r)
        A("      => Mutaxassis (nevrolog) ko'rigi tavsiya etiladi.")

    # --- Disclaimer ---
    A("")
    A(sub)
    for chunk in _wrap(config.DISCLAIMER, 58):
        A("  " + chunk)
    A(sub)
    A("  (c) %s" % config.AUTHOR)

    return "\n".join(L)


def _wrap(text, width):
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out
