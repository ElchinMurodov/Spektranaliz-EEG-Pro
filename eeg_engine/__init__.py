"""
eeg_engine — Sportchining EEG signallarini spektral tahlil qilish va funksional
holatni aniqlash kutubxonasi (BIRLASHTIRILGAN, OPTIMALLASHTIRILGAN yadro).

Ikki dasturning birlashmasi:
  * Spektranaliz-EEG-installation7 — chiroyli Tkinter GUI, scipy/pyedflib,
    engagement indeksi, dominant chastota (PSD+FFT), spektral chegara (edge).
  * EEG-signal-edf-bdf — modular sof Python yadro, custom FFT/EDF parser,
    iAPF, FAA, FMT, harmonizatsiya, individual kalibrlash, HTML/SVG topomap.

Yadro SOF PYTHON da ishlaydi (hech qanday tashqi kutubxona shart emas), lekin
numpy/scipy/pyedflib/mne mavjud bo'lsa, ularni avtomatik aniqlab tezlashtiradi.

Modullar:
  config        — sozlamalar (ritmlar, zonalar, 8 holat)
  dsp           — FFT va DSP yadrosi (sof Python + numpy tezlashtirish)
  loader        — EDF/EDF+/BDF/BDF+/CSV o'qish (pyedflib/mne/sof Python)
  preprocessing — robust tozalash, filtrlash, harmonizatsiya
  spectral      — Welch PSD, band power, dominant chastota, spectral edge
  features      — belgilar (iAPF, FAA, FMT, engagement, dominant, edge, ...)
  calibration   — individual baseline normalizatsiya
  classifier    — 8 funksional holat + softmax ishonch + atipik aniqlash
  report        — matnli hisobot
  visualize     — HTML + SVG vizual hisobot (PSD, topomap, ...)
  pipeline      — to'liq zanjirni birlashtiruvchi (analyze_file)
"""

from . import (config, dsp, loader, preprocessing, spectral, features,
               classifier, report, visualize, calibration)
from .pipeline import analyze_file

__all__ = [
    "config", "dsp", "loader", "preprocessing", "spectral", "features",
    "classifier", "report", "visualize", "calibration", "analyze_file",
]
