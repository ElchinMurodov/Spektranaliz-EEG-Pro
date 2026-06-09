"""
preprocessing.py — EEG signalini dastlabki qayta ishlash va harmonizatsiya.

Ikki dasturning eng kuchli tomonlari birlashtirilgan:

  installation7 dan:
    - Yetishmayotgan (NaN) qiymatlarni interpolyatsiya bilan to'ldirish
    - Robust (MAD asosida) chekka qiymatlarni cheklash (artefakt bostirish)
    - z-score normalizatsiya
    - scipy mavjud bo'lsa: Butterworth band-pass + IIR notch (filtfilt)

  EEG-signal-edf-bdf dan:
    - Harmonizatsiya: turli qurilmalarni yagona namuna chastotasiga keltirish
      (anti-aliasing bilan) — ILMIY YANGILIK
    - scipy bo'lmasa: FFT sohasida band-pass va notch (sof Python)

Bosqichlar: interp -> robust clip -> detrend -> band-pass -> notch(50/60)
            -> harmonizatsiya -> z-score
"""

import math

from . import dsp
from . import config

try:
    from scipy import signal as _sp_signal
    HAVE_SCIPY = True
except Exception:
    _sp_signal = None
    HAVE_SCIPY = False


# ---------------------------------------------------------------------------
# Robust artefakt bostirish (installation7 yondashuvi)
# ---------------------------------------------------------------------------
def _robust_clip(x, k=6.0):
    """Mediana ± k*robust_std oralig'iga cheklab, kuchli artefaktlarni yumshatadi."""
    med = dsp.median(x)
    m = dsp.mad(x)
    robust_std = 1.4826 * m if m > 0 else dsp.std(x)
    if robust_std <= 0:
        return list(x)
    lo, hi = med - k * robust_std, med + k * robust_std
    return [hi if v > hi else (lo if v < lo else v) for v in x]


def _zscore(x):
    """O'rta 0, standart chetlanish 1 ga keltirish."""
    m = dsp.mean(x)
    s = dsp.std(x)
    if s <= 0:
        return [0.0 for _ in x]
    return [(v - m) / s for v in x]


# ---------------------------------------------------------------------------
# Filtrlash — scipy bo'lsa IIR, bo'lmasa FFT (sof Python)
# ---------------------------------------------------------------------------
def _fft_bandpass(x, fs, low, high):
    n = len(x)
    if n < 4:
        return list(x)
    nfft = dsp.next_pow2(n)
    padded = list(x) + [0.0] * (nfft - n)
    spec = dsp.fft(padded)
    df = fs / nfft
    half = nfft // 2
    for k in range(half + 1):
        freq = k * df
        if not (low <= freq <= high):
            spec[k] = complex(0, 0)
            if k != 0 and k != half:
                spec[nfft - k] = complex(0, 0)
    rec = dsp.ifft(spec)
    return [rec[i].real for i in range(n)]


def _fft_notch(x, fs, f0, width=2.0):
    n = len(x)
    if n < 4:
        return list(x)
    nfft = dsp.next_pow2(n)
    padded = list(x) + [0.0] * (nfft - n)
    spec = dsp.fft(padded)
    df = fs / nfft
    half = nfft // 2
    for k in range(half + 1):
        freq = k * df
        if abs(freq - f0) <= width:
            spec[k] = complex(0, 0)
            if k != 0 and k != half:
                spec[nfft - k] = complex(0, 0)
    rec = dsp.ifft(spec)
    return [rec[i].real for i in range(n)]


def _bandpass(x, fs, low, high):
    eff_high = min(high, fs / 2.0 * 0.95)
    if eff_high <= low:
        return list(x)
    if HAVE_SCIPY and len(x) > 24:
        try:
            sos = _sp_signal.butter(4, [low, eff_high], btype="bandpass", fs=fs, output="sos")
            return list(_sp_signal.sosfiltfilt(sos, x))
        except Exception:
            pass
    return _fft_bandpass(x, fs, low, eff_high)


def _notch(x, fs, freqs):
    out = list(x)
    for f0 in freqs:
        if f0 >= fs / 2.0 - 1.0:
            continue
        if HAVE_SCIPY and len(out) > 24:
            try:
                b, a = _sp_signal.iirnotch(f0, Q=30, fs=fs)
                out = list(_sp_signal.filtfilt(b, a, out))
                continue
            except Exception:
                pass
        out = _fft_notch(out, fs, f0)
    return out


# ---------------------------------------------------------------------------
# Harmonizatsiya (resampling) — ILMIY YANGILIK
# ---------------------------------------------------------------------------
def _resample(x, fs_in, fs_out):
    """Qayta diskretlash (anti-aliasing bilan). scipy bo'lsa undan foydalanadi."""
    if abs(fs_in - fs_out) < 1e-6:
        return list(x)
    n_out = int(round(len(x) / fs_in * fs_out))
    if n_out < 2:
        return list(x)
    if HAVE_SCIPY:
        try:
            return list(_sp_signal.resample(x, n_out))
        except Exception:
            pass
    # Sof Python: downsampling bo'lsa avval anti-aliasing
    if fs_out < fs_in:
        new_nyq = fs_out / 2.0
        x = _fft_bandpass(x, fs_in, 0.0, new_nyq * 0.95)
    n_in = len(x)
    out, step = [], fs_in / fs_out
    for i in range(n_out):
        src = i * step
        i0 = int(math.floor(src))
        frac = src - i0
        if i0 + 1 < n_in:
            out.append(x[i0] * (1 - frac) + x[i0 + 1] * frac)
        else:
            out.append(x[min(i0, n_in - 1)])
    return out


# ---------------------------------------------------------------------------
# Asosiy preprocessing
# ---------------------------------------------------------------------------
def preprocess(rec, target_fs=None, band=None, notch=True, zscore=True, robust=True):
    """
    Recording obyektini to'liq qayta ishlaydi (joyida o'zgartiradi va qaytaradi).

    target_fs — harmonizatsiya uchun maqsadli namuna chastotasi (Hz). None bo'lsa
                har kanal o'z fs sida qoladi.
    band      — (low, high) band-pass chegaralari; None bo'lsa config dan olinadi
    notch     — 50/60 Hz tarmoq shovqinini bostirish
    zscore    — z-score normalizatsiya
    robust    — MAD asosida artefakt cheklash
    """
    low, high = band if band else config.ANALYSIS_BAND

    for ch in rec.channels:
        sig = rec.signals[ch]
        fs = rec.fs[ch]

        sig = dsp.interp_missing(sig)         # 1) NaN/Inf to'ldirish
        if robust:
            sig = _robust_clip(sig)           # 2) artefakt cheklash
        sig = dsp.detrend_linear(sig)         # 3) chiziqli trendni olib tashlash
        sig = _bandpass(sig, fs, low, high)   # 4) band-pass (0.5-45)
        if notch:
            sig = _notch(sig, fs, config.POWERLINE_HZ)  # 5) 50/60 Hz notch

        if target_fs is not None and abs(fs - target_fs) > 1e-6:
            sig = _resample(sig, fs, target_fs)         # 6) harmonizatsiya
            rec.fs[ch] = float(target_fs)

        if zscore:
            sig = _zscore(sig)                # 7) normalizatsiya

        rec.signals[ch] = sig

    if target_fs is not None:
        rec.meta["harmonized_fs"] = float(target_fs)
    rec.meta["scipy"] = HAVE_SCIPY
    return rec
