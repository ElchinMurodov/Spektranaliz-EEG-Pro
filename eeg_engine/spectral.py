"""
spectral.py — Spektral tahlil: Welch usuli bilan quvvat spektral zichligi (PSD).

Welch usuli (ikkala dasturda ham asos):
  1. Signal qisman ustma-ust segmentlarga bo'linadi
  2. Har segment Hann oynasi bilan oynalanadi
  3. Har segment uchun |FFT|^2 (periodogramma) hisoblanadi
  4. Periodogrammalar o'rtachalanadi -> barqaror PSD bahosi

scipy mavjud bo'lsa scipy.signal.welch ishlatiladi (installation7 yo'li),
bo'lmasa sof Python Welch (edf-bdf yo'li). Natija bir xil interfeysda.

Har kanal uchun quyidagilar hisoblanadi:
  - band quvvatlari (absolyut va nisbiy): delta, theta, alpha, beta, gamma
  - dominant chastota (PSD bo'yicha)        — installation7 dan
  - dominant chastota (xom FFT amplitudasi) — installation7 dan
  - spektral chegara (spectral edge 95%)    — installation7 dan
  - spektral entropiya                       — har ikki dasturda
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


def welch_psd(x, fs, seg_sec=None, overlap=None):
    """Welch usuli bilan bir tomonlama PSD. Qaytaradi: (freqs, psd)."""
    seg_sec = seg_sec if seg_sec is not None else config.WELCH_SEGMENT_SEC
    overlap = overlap if overlap is not None else config.WELCH_OVERLAP

    n = len(x)
    nperseg = int(seg_sec * fs)
    if nperseg < 8:
        nperseg = min(n, 8)
    if nperseg > n:
        nperseg = n
    if nperseg < 2:
        return [0.0], [0.0]

    if HAVE_SCIPY:
        try:
            noverlap = int(nperseg * overlap)
            f, p = _sp_signal.welch(x, fs=fs, nperseg=nperseg, noverlap=noverlap)
            return list(f), list(p)
        except Exception:
            pass

    # Sof Python Welch
    nfft = dsp.next_pow2(nperseg)
    win = dsp.hann_window(nperseg)
    win_power = sum(w * w for w in win)
    step = max(1, int(nperseg * (1.0 - overlap)))
    starts = list(range(0, n - nperseg + 1, step)) or [0]

    half = nfft // 2
    psd_acc = [0.0] * (half + 1)
    count = 0
    for s in starts:
        seg = x[s:s + nperseg]
        if len(seg) < nperseg:
            continue
        seg = dsp.detrend_mean(seg)
        seg = [seg[i] * win[i] for i in range(nperseg)]
        power = dsp.rfft_power(seg, nfft)
        for k in range(half + 1):
            psd_acc[k] += power[k]
        count += 1
    count = count or 1

    norm = fs * win_power
    psd = []
    for k in range(half + 1):
        val = psd_acc[k] / count / norm
        if k != 0 and k != half:
            val *= 2.0
        psd.append(val)
    freqs = [k * fs / nfft for k in range(half + 1)]
    return freqs, psd


def band_power(freqs, psd, low, high):
    """PSD ni [low, high] da trapetsiya usulida integrallaydi."""
    total = 0.0
    for k in range(len(freqs) - 1):
        f0, f1 = freqs[k], freqs[k + 1]
        if f1 < low or f0 > high:
            continue
        a, b = max(f0, low), min(f1, high)
        if b <= a:
            continue
        if f1 > f0:
            pa = psd[k] + (psd[k + 1] - psd[k]) * (a - f0) / (f1 - f0)
            pb = psd[k] + (psd[k + 1] - psd[k]) * (b - f0) / (f1 - f0)
        else:
            pa = pb = psd[k]
        total += 0.5 * (pa + pb) * (b - a)
    return total


def channel_band_powers(freqs, psd, bands=None):
    """Bitta kanal uchun barcha ritmlar bo'yicha absolyut va nisbiy quvvat."""
    bands = bands if bands else config.BANDS
    absolute = {name: band_power(freqs, psd, lo, hi) for name, (lo, hi) in bands.items()}
    total = sum(absolute.values()) or 1e-12
    relative = {name: absolute[name] / total for name in absolute}
    return {"absolute": absolute, "relative": relative, "total": total}


def dominant_frequency(freqs, psd, band=None):
    """PSD maksimumiga to'g'ri keladigan chastota (dominant chastota)."""
    lo, hi = band if band else config.ANALYSIS_BAND
    best_f, best_p = 0.0, -1.0
    for k in range(len(freqs)):
        if lo <= freqs[k] <= hi and psd[k] > best_p:
            best_p, best_f = psd[k], freqs[k]
    return best_f


def spectral_edge(freqs, psd, ratio=None, band=None):
    """
    Spektral chegara chastotasi: umumiy quvvatning `ratio` ulushi shu
    chastotagacha jamlanadi (odatda 95%). installation7 dan.
    """
    ratio = ratio if ratio is not None else config.SPECTRAL_EDGE_RATIO
    lo, hi = band if band else config.ANALYSIS_BAND
    idx = [k for k in range(len(freqs)) if lo <= freqs[k] <= hi]
    if len(idx) < 2:
        return 0.0
    cum, total = 0.0, sum(psd[k] for k in idx) or 1e-12
    target = ratio * total
    for k in idx:
        cum += psd[k]
        if cum >= target:
            return freqs[k]
    return freqs[idx[-1]]


def spectral_entropy(freqs, psd, band=None):
    """Normallashtirilgan Shannon spektral entropiyasi [0, 1]."""
    lo, hi = band if band else config.ANALYSIS_BAND
    vals = [psd[k] for k in range(len(freqs)) if lo <= freqs[k] <= hi]
    s = sum(vals)
    if s <= 0 or len(vals) < 2:
        return 0.0
    p = [v / s for v in vals if v > 0]
    h = -sum(pi * math.log(pi) for pi in p)
    return h / math.log(len(vals))


def fft_dominant_frequency(signal, fs, band=None):
    """Xom signalning FFT amplitudasi bo'yicha dominant chastota. installation7 dan."""
    lo, hi = band if band else config.ANALYSIS_BAND
    n = len(signal)
    if n < 4:
        return 0.0
    nfft = dsp.next_pow2(n)
    mag = dsp.rfft_mag(dsp.detrend_mean(signal), nfft)
    best_f, best_m = 0.0, -1.0
    for k in range(len(mag)):
        f = k * fs / nfft
        if lo <= f <= hi and mag[k] > best_m:
            best_m, best_f = mag[k], f
    return best_f


def analyze_recording(rec):
    """
    Butun Recording bo'yicha har kanal uchun to'liq spektral natijani hisoblaydi.

    Qaytaradi: {kanal: {
        "freqs", "psd", "absolute", "relative", "total",
        "dominant", "fft_dominant", "edge95", "entropy"
    }}
    """
    result = {}
    for ch in rec.channels:
        fs = rec.fs[ch]
        sig = rec.signals[ch]
        freqs, psd = welch_psd(sig, fs)
        bp = channel_band_powers(freqs, psd)
        result[ch] = {
            "freqs": freqs,
            "psd": psd,
            "absolute": bp["absolute"],
            "relative": bp["relative"],
            "total": bp["total"],
            "dominant": dominant_frequency(freqs, psd),
            "fft_dominant": fft_dominant_frequency(sig, fs),
            "edge95": spectral_edge(freqs, psd),
            "entropy": spectral_entropy(freqs, psd),
        }
    return result
