# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spetsifikatsiya fayli - 'Spektranaliz EEG Pro' dasturi uchun.

Yig'ish:
    pyinstaller spektranaliz_eeg_pro.spec

Natija: dist/Spektranaliz EEG Pro/Spektranaliz EEG Pro.exe (onedir).
Resurslar (fon, ikona, logolar) va eeg_engine paketi .exe yoniga bundle qilinadi.
"""

import os

block_cipher = None

if not os.path.exists("spektranaliz-eeg-icon.ico"):
    import subprocess
    import sys as _sys
    print("[spec] Rasterlar topilmadi - make_assets.py ishga tushirilmoqda...")
    subprocess.run([_sys.executable, "make_assets.py"], check=False)

ICON_FILE = "spektranaliz-eeg-icon.ico" if os.path.exists("spektranaliz-eeg-icon.ico") else None

datas = [
    ("EEG spectrum background 700x700.svg", "."),
    ("EEG-spectrum-background-730x730.png", "."),
    ("EEG spectrum background 685x685.jpg", "."),
    ("spektranaliz-eeg-icon.svg", "."),
    ("spektranaliz-eeg-icon.ico", "."),
    ("spektranaliz-eeg-icon.png", "."),
    ("spektranaliz-eeg-logo.svg", "."),
    ("spektranaliz-eeg-logo-dark.svg", "."),
    ("spektranaliz-eeg-logo.png", "."),
    ("spektranaliz-eeg-logo-dark.png", "."),
]
datas = [(src, dst) for (src, dst) in datas if os.path.exists(src)]

# eeg_engine paketi avtomatik aniqlanadi, lekin kafolat uchun submodullarni
# yashirin importlar sifatida ham ko'rsatamiz.
hiddenimports = [
    "PIL._tkinter_finder",
    "eeg_engine",
    "eeg_engine.config",
    "eeg_engine.dsp",
    "eeg_engine.loader",
    "eeg_engine.preprocessing",
    "eeg_engine.spectral",
    "eeg_engine.features",
    "eeg_engine.calibration",
    "eeg_engine.classifier",
    "eeg_engine.report",
    "eeg_engine.charts",
    "eeg_engine.visualize",
    "eeg_engine.pipeline",
    # Ixtiyoriy tezlashtiruvchilar (mavjud bo'lsa qo'shiladi)
    "numpy",
    "scipy.signal",
    "svglib",
    "reportlab",
    "pyedflib",
]

a = Analysis(
    ["Spektranaliz EEG Pro.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["mne", "matplotlib", "tkinter.test", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Spektranaliz EEG Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Spektranaliz EEG Pro",
    contents_directory=".",
)
