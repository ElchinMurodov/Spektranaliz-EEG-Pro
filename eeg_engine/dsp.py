"""
dsp.py — Raqamli signalni qayta ishlash (DSP) yadrosi.

Bu modul ikki dasturning yondashuvini birlashtiradi:
  - EEG-signal-edf-bdf: tashqi kutubxonasiz (sof Python) FFT (Cooley-Tukey),
    Hann oynasi, statistik yordamchilar.
  - Spektranaliz-EEG-installation7: numpy/scipy mavjud bo'lsa, ulardan
    foydalangan holda tezlik va aniqlikni oshirish.

Ya'ni: numpy mavjud bo'lsa, FFT va statistika numpy bilan tezlashtiriladi;
bo'lmasa, toza Python amalga oshirilishi ishlaydi (har joyda ishlaydi).
"""

import math
import cmath

# Ixtiyoriy tezkor backend
try:
    import numpy as _np
    HAVE_NUMPY = True
except Exception:
    _np = None
    HAVE_NUMPY = False


# ---------------------------------------------------------------------------
# Asosiy statistik yordamchilar
# ---------------------------------------------------------------------------
def mean(x):
    """O'rta arifmetik qiymat."""
    if HAVE_NUMPY:
        return float(_np.mean(x)) if len(x) else 0.0
    return sum(x) / len(x) if x else 0.0


def std(x):
    """Standart chetlanish (population, ddof=0)."""
    if len(x) < 2:
        return 0.0
    if HAVE_NUMPY:
        return float(_np.std(x))
    m = mean(x)
    var = sum((v - m) ** 2 for v in x) / len(x)
    return math.sqrt(var)


def median(x):
    """Mediana."""
    if not x:
        return 0.0
    if HAVE_NUMPY:
        return float(_np.median(x))
    s = sorted(x)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return 0.5 * (s[mid - 1] + s[mid])


def mad(x):
    """Mediana atrofidagi absolyut chetlanish medianasi (robust tarqalish)."""
    med = median(x)
    if HAVE_NUMPY:
        return float(_np.median(_np.abs(_np.asarray(x, dtype=float) - med)))
    return median([abs(v - med) for v in x])


def detrend_mean(x):
    """Signaldan o'rta qiymatni (DC komponent) ayirish."""
    m = mean(x)
    if HAVE_NUMPY:
        return list(_np.asarray(x, dtype=float) - m)
    return [v - m for v in x]


def detrend_linear(x):
    """Chiziqli trendni (eng kichik kvadratlar bilan) olib tashlash."""
    n = len(x)
    if n < 2:
        return list(x)
    if HAVE_NUMPY:
        arr = _np.asarray(x, dtype=float)
        t = _np.arange(n, dtype=float)
        a, b = _np.polyfit(t, arr, 1)
        return list(arr - (a * t + b))
    # Sof Python: y = a*t + b
    sx = sum(range(n))
    sy = sum(x)
    sxx = sum(i * i for i in range(n))
    sxy = sum(i * x[i] for i in range(n))
    denom = (n * sxx - sx * sx) or 1.0
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    return [x[i] - (a * i + b) for i in range(n)]


def interp_missing(x):
    """NaN/Inf qiymatlarni chiziqli interpolyatsiya bilan to'ldiradi."""
    vals = list(x)
    n = len(vals)
    finite_idx = [i for i in range(n) if _is_finite(vals[i])]
    if len(finite_idx) < 2:
        return [0.0] * n
    if len(finite_idx) == n:
        return [float(v) for v in vals]
    out = [0.0] * n
    first, last = finite_idx[0], finite_idx[-1]
    # chetlarni eng yaqin qiymat bilan to'ldirish
    for i in range(0, first):
        out[i] = float(vals[first])
    for i in range(last + 1, n):
        out[i] = float(vals[last])
    for k in range(len(finite_idx) - 1):
        i0, i1 = finite_idx[k], finite_idx[k + 1]
        v0, v1 = float(vals[i0]), float(vals[i1])
        out[i0] = v0
        for i in range(i0 + 1, i1):
            frac = (i - i0) / (i1 - i0)
            out[i] = v0 * (1 - frac) + v1 * frac
        out[i1] = v1
    return out


def _is_finite(v):
    try:
        return math.isfinite(v)
    except (TypeError, ValueError):
        return False


def next_pow2(n):
    """n dan katta yoki teng eng kichik 2 darajasini qaytaradi."""
    p = 1
    while p < n:
        p <<= 1
    return p


# ---------------------------------------------------------------------------
# Oynaviy funksiyalar
# ---------------------------------------------------------------------------
def hann_window(n):
    """Hann (Hanning) oynasi — spektral 'sizib chiqish' (leakage) ni kamaytiradi."""
    if n == 1:
        return [1.0]
    if HAVE_NUMPY:
        return list(_np.hanning(n))
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


# ---------------------------------------------------------------------------
# FFT — Cooley-Tukey radix-2 (iterativ, bit-reversal) — sof Python fallback
# ---------------------------------------------------------------------------
def _bit_reverse_indices(n):
    bits = n.bit_length() - 1
    result = [0] * n
    for i in range(n):
        rev = 0
        x = i
        for _ in range(bits):
            rev = (rev << 1) | (x & 1)
            x >>= 1
        result[i] = rev
    return result


def fft(signal):
    """Tezkor Fure almashtirishi (uzunligi 2 darajasi). numpy bo'lsa undan foydalanadi."""
    if HAVE_NUMPY:
        return list(_np.fft.fft(_np.asarray(signal)))
    n = len(signal)
    if n == 0:
        return []
    if n & (n - 1) != 0:
        raise ValueError("FFT uzunligi 2 darajasi bo'lishi kerak: " + str(n))
    rev = _bit_reverse_indices(n)
    a = [complex(signal[rev[i]]) for i in range(n)]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlen = cmath.exp(complex(0, ang))
        half = length // 2
        for start in range(0, n, length):
            w = complex(1, 0)
            for k in range(half):
                u = a[start + k]
                v = a[start + k + half] * w
                a[start + k] = u + v
                a[start + k + half] = u - v
                w *= wlen
        length <<= 1
    return a


def rfft_power(segment, nfft):
    """Bir segment uchun bir tomonlama quvvat spektri |X[k]|^2 (uzunligi nfft//2+1)."""
    if len(segment) < nfft:
        segment = list(segment) + [0.0] * (nfft - len(segment))
    if HAVE_NUMPY:
        spec = _np.fft.rfft(_np.asarray(segment, dtype=float), n=nfft)
        return list((spec.real ** 2 + spec.imag ** 2))
    spec = fft(segment)
    half = nfft // 2
    return [(spec[k].real ** 2 + spec[k].imag ** 2) for k in range(half + 1)]


def rfft_mag(segment, nfft):
    """Bir tomonlama amplituda spektri |X[k]| (FFT dominant chastotasi uchun)."""
    if len(segment) < nfft:
        segment = list(segment) + [0.0] * (nfft - len(segment))
    if HAVE_NUMPY:
        spec = _np.fft.rfft(_np.asarray(segment, dtype=float), n=nfft)
        return list(_np.abs(spec))
    spec = fft(segment)
    half = nfft // 2
    return [abs(spec[k]) for k in range(half + 1)]


def ifft(spectrum):
    """Teskari FFT. Kirish uzunligi 2 darajasi bo'lishi kerak."""
    if HAVE_NUMPY:
        return list(_np.fft.ifft(_np.asarray(spectrum)))
    n = len(spectrum)
    if n == 0:
        return []
    conj = [complex(v).conjugate() for v in spectrum]
    transformed = fft(conj)
    return [v.conjugate() / n for v in transformed]
