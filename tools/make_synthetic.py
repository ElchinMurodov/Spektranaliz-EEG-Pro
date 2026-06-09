#!/usr/bin/env python3
"""
make_synthetic.py — Test uchun sun'iy EEG yozuvlarini yaratish.

Real EEG fayllar bo'lmagani uchun, ma'lum funksional holatlarga mos keladigan
spektral tarkibli sun'iy signallar generatsiya qilamiz va ularni EDF hamda CSV
formatida saqlaymiz. Bu pipeline ning to'g'ri ishlashini tekshirish imkonini
beradi (har bir holatni qayta aniqlay oladimi?).

EDF yozuvchi ham shu yerda — toza Python (struct) bilan.
"""

import os
import math
import random
import struct

# 10-20 tizimidagi 19 ta standart kanal
CHANNELS = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8",
            "T3", "C3", "Cz", "C4", "T4",
            "T5", "P3", "Pz", "P4", "T6", "O1", "O2"]

# Har holat uchun ritm amplitudalari (delta, theta, alpha, beta, gamma)
# va shovqin darajasi (entropiyaga ta'sir qiladi)
STATE_PROFILES = {
    "normal":          dict(amp=(1.0, 0.85, 0.85, 1.05, 0.45), noise=0.7),
    "fokus":           dict(amp=(0.6, 0.7, 0.7, 1.7, 0.5), noise=0.4),
    "charchoq":        dict(amp=(1.0, 1.9, 0.8, 0.5, 0.2), noise=0.6),
    "uyquga_moyillik": dict(amp=(2.2, 1.6, 0.3, 0.4, 0.15), noise=0.5),
    "qozgalish":       dict(amp=(0.5, 0.6, 0.6, 1.5, 1.5), noise=0.9),
    "stress":          dict(amp=(0.6, 1.0, 0.5, 1.9, 0.6), noise=1.1),
    "meditativ":       dict(amp=(0.6, 1.3, 2.3, 0.3, 0.2), noise=0.25),
}

BANDS = [(0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 45.0)]


def _band_component(n, fs, lo, hi, amp, k=6):
    """[lo, hi] diapazonida k ta tasodifiy sinusoidadan iborat komponent."""
    out = [0.0] * n
    for _ in range(k):
        f = random.uniform(lo, hi)
        phase = random.uniform(0, 2 * math.pi)
        a = amp * random.uniform(0.6, 1.0) / k
        w = 2 * math.pi * f / fs
        for i in range(n):
            out[i] += a * math.sin(w * i + phase)
    return out


def generate(state, fs, dur, seed=0):
    """Berilgan holat uchun barcha kanallar bo'yicha signal (µV) generatsiya qiladi."""
    random.seed(seed)
    prof = STATE_PROFILES[state]
    amps = prof["amp"]
    noise = prof["noise"]
    n = int(fs * dur)
    data = {}

    for ci, ch in enumerate(CHANNELS):
        sig = [0.0] * n
        # Ritm komponentlari
        for bi, (lo, hi) in enumerate(BANDS):
            a = amps[bi]
            # Fokus holatida Fz da teta'ni kuchaytiramiz (FMT markeri)
            if state == "fokus" and ch == "Fz" and bi == 1:
                a *= 2.2
            # Stress holatida o'ng frontal alfa'ni oshiramiz (FAA musbat)
            if state == "stress" and bi == 2:
                if ch in ("F4", "F8"):
                    a *= 1.6
                elif ch in ("F3", "F7"):
                    a *= 0.7
            # iAPF: alfa komponentini ~10 Hz atrofida jamlash (oksipitalda kuchli)
            if bi == 2:
                aa = a * (1.2 if ch in ("O1", "O2") else 1.0)
                comp = _band_component(n, fs, 9.0, 11.0, aa * 30.0, k=6)
            else:
                comp = _band_component(n, fs, lo, hi, a * 30.0)
            for i in range(n):
                sig[i] += comp[i]
        # Keng diapazonli shovqin (entropiyaga ta'sir)
        for i in range(n):
            sig[i] += noise * 15.0 * (random.random() - 0.5)
        data[ch] = sig
    return data, n


# ---------------------------------------------------------------------------
# EDF yozuvchi (16-bit)
# ---------------------------------------------------------------------------
def _ascii(s, width):
    b = str(s).encode("ascii", errors="replace")[:width]
    return b + b" " * (width - len(b))


def write_edf(path, channels, fs, data, dur):
    """Sodda EDF (16-bit) fayl yozadi."""
    fs = int(fs)
    n_records = int(dur)
    ns = len(channels)
    pmin, pmax = -500.0, 500.0
    dmin, dmax = -32768, 32767

    header = b""
    header += _ascii("0", 8)                      # versiya
    header += _ascii("X SYNTHETIC EEG", 80)       # bemor
    header += _ascii("Startdate 01-JAN-2025", 80) # yozuv
    header += _ascii("01.01.25", 8)               # sana
    header += _ascii("00.00.00", 8)               # vaqt
    header += _ascii(256 + ns * 256, 8)           # header baytlari
    header += _ascii("", 44)                       # rezerv (oddiy EDF)
    header += _ascii(n_records, 8)                 # data records soni
    header += _ascii(1, 8)                         # record davomiyligi (1 s)
    header += _ascii(ns, 4)                        # signallar soni

    # Per-signal sarlavhalar
    def block(values, width):
        return b"".join(_ascii(v, width) for v in values)

    header += block(channels, 16)                          # label
    header += block(["AgAgCl"] * ns, 80)                   # transducer
    header += block(["uV"] * ns, 8)                        # physical dim
    header += block([pmin] * ns, 8)                        # physical min
    header += block([pmax] * ns, 8)                        # physical max
    header += block([dmin] * ns, 8)                        # digital min
    header += block([dmax] * ns, 8)                        # digital max
    header += block(["HP:0.1Hz LP:75Hz"] * ns, 80)         # prefilter
    header += block([fs] * ns, 8)                          # samples/record
    header += block([""] * ns, 32)                         # rezerv

    # Ma'lumot rekordlari
    body = bytearray()
    gain = (dmax - dmin) / (pmax - pmin)
    for r in range(n_records):
        for ch in channels:
            seg = data[ch][r * fs:(r + 1) * fs]
            for v in seg:
                d = int(round((v - pmin) * gain + dmin))
                d = max(dmin, min(dmax, d))
                body += struct.pack("<h", d)

    with open(path, "wb") as f:
        f.write(header)
        f.write(bytes(body))


def write_csv(path, channels, fs, data, dur):
    """Sodda CSV fayl yozadi (time ustuni bilan)."""
    n = int(fs * dur)
    with open(path, "w") as f:
        f.write("time," + ",".join(channels) + "\n")
        for i in range(n):
            t = i / fs
            row = [f"{t:.4f}"] + [f"{data[ch][i]:.3f}" for ch in channels]
            f.write(",".join(row) + "\n")


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(out_dir, exist_ok=True)

    dur = 20  # soniya

    # Har bir holat uchun EDF fayl (100 Hz — Contec KT-88 ga o'xshash)
    for i, state in enumerate(STATE_PROFILES):
        data, n = generate(state, fs=100, dur=dur, seed=i + 1)
        path = os.path.join(out_dir, f"synth_{state}_100hz.edf")
        write_edf(path, CHANNELS, 100, data, dur)
        print("Yozildi:", os.path.relpath(path, out_dir.replace("/data", "")))

    # Bitta CSV fayl (256 Hz)
    data, n = generate("meditativ", fs=256, dur=dur, seed=99)
    csv_path = os.path.join(out_dir, "synth_meditativ_256hz.csv")
    write_csv(csv_path, CHANNELS, 256, data, dur)
    print("Yozildi:", csv_path)

    # Bitta 500 Hz EDF (Компакт-нейро ga o'xshash) — harmonizatsiya testi uchun
    data, n = generate("fokus", fs=500, dur=dur, seed=7)
    edf500 = os.path.join(out_dir, "synth_fokus_500hz.edf")
    write_edf(edf500, CHANNELS, 500, data, dur)
    print("Yozildi:", edf500)


if __name__ == "__main__":
    main()
