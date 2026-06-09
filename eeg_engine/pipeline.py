"""
pipeline.py — To'liq tahlil zanjirini bitta funksiyada birlashtiradi.

Zanjir:
  fayl -> o'qish -> preprocessing(+harmonizatsiya) -> spektral tahlil
       -> belgilar -> (ixtiyoriy kalibrlash) -> holat -> hisobot

Chiqarish (eksport) formatlari: TXT (matn), HTML (SVG grafiklar), PDF (rasm).
"""

from . import loader, preprocessing, spectral, features, classifier, report
from . import visualize


def analyze_objects(path, fs=None, target_fs=None, notch=True, baseline=None, prefer="auto"):
    """
    Faylni tahlil qilib, JONLI obyektlarni qaytaradi (qayta hisoblamasdan
    grafik/HTML/PDF/TXT chiqarish uchun qulay).

    Qaytaradi: dict {rec, spec, features, classification, calibrated, report}
      rec            — Recording obyekti
      spec           — to'liq spektral natija (freqs/psd bilan)
      features       — belgilar dict
      classification — holat natijasi
      report         — matnli hisobot (str)
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
    rep = report.build_report(rec, spec, feats, cls, calibrated=calibrated)

    return {
        "rec": rec,
        "spec": spec,
        "features": feats,
        "classification": cls,
        "calibrated": calibrated,
        "report": rep,
    }


# ---------------------------------------------------------------------------
# Eksport yordamchilari (jonli obyektlardan)
# ---------------------------------------------------------------------------
def export_txt(objs, path):
    """Matnli (TXT) hisobotni saqlaydi."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(objs["report"])
    return path


def export_html(objs, path, topo_band="alpha"):
    """HTML (SVG grafikli) hisobotni saqlaydi."""
    html = visualize.build_html(objs["rec"], objs["spec"], objs["features"],
                                objs["classification"], topo_band=topo_band)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def export_pdf(objs, path, topo_band="alpha"):
    """PDF (grafikli poster) hisobotni saqlaydi. Pillow talab qilinadi."""
    from . import charts
    return charts.save_pdf(objs["rec"], objs["spec"], objs["features"],
                           objs["classification"], path, topo_band=topo_band)


# ---------------------------------------------------------------------------
# Yuqori darajadagi qulay funksiya (CLI uchun)
# ---------------------------------------------------------------------------
def analyze_file(path, fs=None, target_fs=None, notch=True, make_report=True,
                 html_path=None, pdf_path=None, txt_path=None,
                 baseline=None, prefer="auto"):
    """
    Bitta EEG faylni to'liq tahlil qiladi va so'ralgan formatlarda saqlaydi.

    html_path / pdf_path / txt_path — berilsa, mos hisobot saqlanadi.
    Qaytaradi: dict {recording_summary, features, classification, spectral,
                     report, html_path, pdf_path, txt_path, calibrated}
    """
    objs = analyze_objects(path, fs=fs, target_fs=target_fs, notch=notch,
                           baseline=baseline, prefer=prefer)
    rec, spec, feats, cls = objs["rec"], objs["spec"], objs["features"], objs["classification"]
    rep = objs["report"] if make_report else None

    if html_path:
        export_html(objs, html_path)
    if pdf_path:
        export_pdf(objs, pdf_path)
    if txt_path:
        export_txt(objs, txt_path)

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
        "pdf_path": pdf_path,
        "txt_path": txt_path,
        "calibrated": objs["calibrated"],
    }
