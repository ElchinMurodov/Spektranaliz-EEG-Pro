#!/usr/bin/env python3
"""
cli.py — Spektranaliz EEG Pro dasturining buyruq qatori (CLI) interfeysi.

GUI dan tashqari, dasturni terminalda (va skriptlarda) ham ishlatish mumkin.

Foydalanish:
    python cli.py <fayl.edf|.bdf|.csv> [parametrlar]

Misollar:
    python cli.py data/0000007.EDF
    python cli.py data/synth_stress_100hz.edf --html hisobot.html
    python cli.py signal.csv --fs 256
    python cli.py data/synth_fokus_500hz.edf --target-fs 100
    python cli.py mashqdan_keyin.edf --baseline dam_olish.edf
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eeg_engine import analyze_file


def main():
    p = argparse.ArgumentParser(
        description="EEG signallarini spektral tahlil qilib, funksional holatni aniqlaydi.")
    p.add_argument("file", help="EEG fayl yo'li (EDF/EDF+/BDF/BDF+/CSV)")
    p.add_argument("--fs", type=float, default=None, help="Namuna chastotasi (CSV uchun)")
    p.add_argument("--target-fs", type=float, default=None, help="Harmonizatsiya chastotasi (Hz)")
    p.add_argument("--no-notch", action="store_true", help="50/60 Hz tarmoq filtrini o'chirish")
    p.add_argument("--html", metavar="FAYL", help="HTML vizual hisobotni saqlash")
    p.add_argument("--baseline", metavar="FAYL", help="Tinch holat yozuvi (individual kalibrlash)")
    p.add_argument("--reader", default="auto", choices=["auto", "pyedflib", "mne", "pure"],
                   help="EDF/BDF o'qish usuli")
    args = p.parse_args()

    if not os.path.exists(args.file):
        print("XATO: fayl topilmadi:", args.file)
        sys.exit(1)

    base = None
    if args.baseline:
        from eeg_engine import calibration
        base = calibration.compute_baseline(args.baseline)
        print("Kalibrlash: baseline '%s' dan hisoblandi.\n" % args.baseline)

    result = analyze_file(
        args.file, fs=args.fs, target_fs=args.target_fs,
        notch=not args.no_notch, html_path=args.html, baseline=base, prefer=args.reader)
    print(result["report"])
    if args.html:
        print("\nHTML hisobot saqlandi:", args.html)


if __name__ == "__main__":
    main()
