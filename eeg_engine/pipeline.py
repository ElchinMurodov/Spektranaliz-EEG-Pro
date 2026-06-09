"""
pipeline.py — To'liq tahlil zanjirini bitta funksiyada birlashtiradi.

Zanjir:
  fayl -> o'qish -> preprocessing(+harmonizatsiya) -> spektral tahlil
       -> belgilar -> (ixtiyoriy kalibrlash) -> holat -> hisobot (+HTML)
"""

from . import loader, preprocessing, spectral, features, classifier, report
from . import visualize


def analyze_file(path, fs=None, target_fs=None, notch=True, make_report=True,
                 html_path=None, baseline=None, prefer="auto"):
    """
    Bitta EEG faylni to'liq tahlil qiladi.

    path       — EDF/EDF+/BDF/BDF+/CSV fayl yo'li
    fs         — CSV uchun namuna chastotasi (agar faylda bo'lmasa)
    target_fs  — harmonizatsiya uchun maqsadli chastota (turli qurilmalar uchun)
    notch      — 50/60 Hz tarmoq shovqinini bostirish
    html_path  — berilsa, HTML vizual hisobot shu faylga saqlanadi
    baseline   — individual kalibrlash uchun tinch holat belgilari (dict)
    prefer     — EDF/BDF o'qish usuli: "auto"/"pyedflib"/"mne"/"pure"

    Qaytaradi: dict {recording_summary, features, classification, spectral, report, html_path}
    """
    rec = loader.load(path, fs=fs, prefer=prefer)
    preprocessing.preprocess(rec, target_fs=target_fs, notch=notch)
    spec = spectral.analyze_recording(rec)
    feats = features.extract_features(rec, spec)

    calibrated = False
    if baseline is not None:
        from . import calibration
        feats = calibration.apply_baseline(feats, baseline)
        calibrated = True

    cls = classifier.classify(feats)
    rep = report.build_report(rec, spec, feats, cls, calibrated=calibrated) if make_report else None

    if html_path:
        html = visualize.build_html(rec, spec, feats, cls)
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)

    spec_compact = {
        ch: {"absolute": spec[ch]["absolute"], "relative": spec[ch]["relative"]}
        for ch in spec
    }
    return {
        "recording_summary": rec.summary(),
        "features": feats,
        "classification": cls,
        "spectral": spec_compact,
        "report": rep,
        "html_path": html_path,
        "calibrated": calibrated,
    }
