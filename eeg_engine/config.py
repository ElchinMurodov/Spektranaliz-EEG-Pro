"""
config.py — Birlashtirilgan EEG tahlil tizimining markaziy konfiguratsiyasi.

Bu fayl ikki dastur (Spektranaliz-EEG-installation7 va EEG-signal-edf-bdf)
sozlamalarini birlashtiradi:
  - EEG ritmlari (chastota diapazonlari)
  - 10-20 xalqaro tizimdagi elektrod zonalari
  - Welch spektral tahlil parametrlari
  - Aniqlanadigan funksional holatlar (ikkala dasturning BIRLASHGAN to'plami)

Barcha modullar shu yagona manbadan foydalanadi — sozlamalar bir joydan
boshqariladi (dissertatsiya uchun qulay).
"""

# ---------------------------------------------------------------------------
# EEG ritmlari (chastota diapazonlari), Hz
# ---------------------------------------------------------------------------
# Gamma yuqori chegarasi 45 Hz (edf-bdf dasturidan). Qurilmaning Nyquist
# chastotasiga qarab avtomatik cheklanadi (masalan Contec KT-88 100 Hz da
# Nyquist = 50 Hz, shuning uchun gamma ~45 Hz gacha ishonchli baholanadi).
BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta":  (13.0, 30.0),
    "gamma": (30.0, 45.0),
}

# O'zbekcha ko'rinish nomlari (hisobotlar uchun)
BAND_LABELS = {
    "delta": "Delta",
    "theta": "Theta",
    "alpha": "Alpha",
    "beta":  "Beta",
    "gamma": "Gamma",
}

# Tahlil qilinadigan umumiy chastota oralig'i (band-pass filtr chegaralari)
ANALYSIS_BAND = (0.5, 45.0)

# Elektr tarmog'i shovqini chastotalari. O'zbekistonda 50 Hz asosiy;
# 60 Hz ham (installation7 dasturidagidek) ehtiyot uchun bostiriladi.
POWERLINE_HZ = (50.0, 60.0)

# ---------------------------------------------------------------------------
# 10-20 xalqaro tizim bo'yicha zona guruhlari
# ---------------------------------------------------------------------------
REGIONS = {
    "frontal":   ["Fp1", "Fp2", "F3", "F4", "F7", "F8", "Fz"],
    "central":   ["C3", "C4", "Cz"],
    "parietal":  ["P3", "P4", "Pz"],
    "occipital": ["O1", "O2"],
    "temporal":  ["T3", "T4", "T5", "T6", "T7", "T8"],
}

# Maxsus kanallar — ma'lum belgilarni hisoblash uchun kerak
FRONTAL_MIDLINE = "Fz"          # Frontal-median teta (FMT) uchun
FRONTAL_LEFT = ["F3", "F7"]     # Frontal alfa asimmetriyasi (FAA) — chap
FRONTAL_RIGHT = ["F4", "F8"]    # Frontal alfa asimmetriyasi (FAA) — o'ng
OCCIPITAL = ["O1", "O2"]        # iAPF (individual alfa cho'qqisi) uchun

# ---------------------------------------------------------------------------
# Spektral tahlil parametrlari (Welch usuli)
# ---------------------------------------------------------------------------
WELCH_SEGMENT_SEC = 2.0   # segment uzunligi (soniya) -> 0.5 Hz aniqlik
WELCH_OVERLAP = 0.5       # segmentlar orasidagi ustma-ustlik (0..1)

# Spektral chegara (spectral edge) hisoblash uchun kumulyativ ulush
SPECTRAL_EDGE_RATIO = 0.95

# ---------------------------------------------------------------------------
# Aniqlanadigan funksional holatlar — IKKALA DASTURNING BIRLASHGAN TO'PLAMI
# ---------------------------------------------------------------------------
# installation7: Charchoq, Uyqusizlik, Normal, Fokus, Xayojonlanish, Stress, Meditativ
# edf-bdf:       Normal, Fokus, Charchoq, Uyquga moyillik, Qo'zg'alish, Stress, Meditativ
#
# "Uyqusizlik" (yuqori qo'zg'alish, alfa kam) va "Uyquga moyillik" (sekin
# ritmlar ustun) — fiziologik jihatdan QARAMA-QARSHI holatlar, shuning uchun
# ikkalasi ham saqlanadi. "Xayojonlanish" va "Qo'zg'alish" yaqin tushunchalar,
# bitta holatda birlashtiriladi ("Qo'zg'alish / Xayojonlanish").
STATES = [
    "Normal",
    "Fokus",
    "Charchoq",
    "Uyquga moyillik",
    "Uyqusizlik",
    "Qo'zg'alish / Xayojonlanish",
    "Stress",
    "Meditativ",
]

# Muhim ogohlantirish — har bir hisobotga qo'shiladi
DISCLAIMER = (
    "DIQQAT: Ushbu natija TIBBIY TASHXIS EMAS. U faqat EEG signalining "
    "funksional holat ko'rsatkichlarini (spektral indekslarni) ifodalaydi. "
    "Epilepsiya, depressiya kabi kasalliklar aniqlanmaydi. Yakuniy talqin "
    "malakali mutaxassis (nevrolog/EEG shifokori) tomonidan amalga oshiriladi."
)

APP_NAME = "Spektranaliz EEG Pro"
AUTHOR = "Murodov Elchin O‘ktamovich"
