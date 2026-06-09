"""
loader.py — Universal EEG signal o'qish moduli (ikki dastur birlashmasi).

Qo'llab-quvvatlanadigan formatlar:
  - EDF / EDF+  (European Data Format, 16-bit)
  - BDF / BDF+  (BioSemi Data Format, 24-bit)
  - CSV         (sarlavhali yoki sarlavhasiz; 'time' ustunidan fs aniqlanadi)

O'qish ustuvorligi (eng ishonchlisidan boshlab):
  1) pyedflib  — mavjud bo'lsa (installation7 yo'li)
  2) mne       — mavjud bo'lsa (professional o'quvchi)
  3) sof Python binar parser — hech qanday kutubxonasiz (edf-bdf yo'li)

Barcha manbalar yagona `Recording` obyektiga keltiriladi — turli qurilmalar
(Contec KT-88, Нейротех "Компакт-нейро" va boshq.) bir xil interfeysda
tahlil qilinadi.
"""

import os
import csv
import struct

from . import config


# ---------------------------------------------------------------------------
# Yagona ma'lumot strukturasi
# ---------------------------------------------------------------------------
class Recording:
    """Bitta EEG yozuvini ifodalovchi obyekt (fizik qiymatlar µV da)."""

    def __init__(self):
        self.channels = []          # standartlashtirilgan kanal nomlari
        self.signals = {}           # {kanal: [float, ...]}
        self.fs = {}                # {kanal: float}
        self.meta = {}              # format, bemor, davomiylik, ...

    def common_fs(self):
        rates = set(round(self.fs[c], 3) for c in self.channels)
        return rates.pop() if len(rates) == 1 else None

    def duration_sec(self):
        best = 0.0
        for c in self.channels:
            n = len(self.signals[c])
            best = max(best, n / self.fs[c] if self.fs[c] else 0.0)
        return best

    def summary(self):
        return {
            "format": self.meta.get("format", "?"),
            "channels": len(self.channels),
            "channel_names": list(self.channels),
            "fs": self.common_fs(),
            "fs_per_channel": dict(self.fs),
            "duration_sec": round(self.duration_sec(), 2),
            "reader": self.meta.get("reader", "pure-python"),
        }


# ---------------------------------------------------------------------------
# Kanal nomlarini standartlashtirish (10-20 tizimi)
# ---------------------------------------------------------------------------
_KNOWN = set()
for _names in config.REGIONS.values():
    _KNOWN.update(n.upper() for n in _names)


def standardize_channel_name(raw):
    """Xom kanal nomini ("EEG Fz-A1") 10-20 standart nomiga ("Fz") keltiradi."""
    name = raw.strip()
    upper = name.upper()
    for pref in ("EEG ", "EEG-", "EEG"):
        if upper.startswith(pref):
            name = name[len(pref):].strip()
            upper = name.upper()
            break
    for sep in ("-", "/"):
        if sep in name:
            name = name.split(sep)[0].strip()
            upper = name.upper()
            break
    if upper in _KNOWN:
        for _names in config.REGIONS.values():
            for n in _names:
                if n.upper() == upper:
                    return n
    return name


def _is_annotation_label(label):
    up = label.upper()
    return "ANNOTATION" in up or "STATUS" in up


# ---------------------------------------------------------------------------
# Sof Python EDF / EDF+ / BDF / BDF+ parser
# ---------------------------------------------------------------------------
def _read_ascii(buf, n, offset):
    return buf[offset:offset + n].decode("ascii", errors="replace").strip(), offset + n


def read_edf_bdf(path):
    """EDF/EDF+/BDF/BDF+ faylni sof Python bilan o'qib, Recording qaytaradi."""
    with open(path, "rb") as f:
        raw = f.read()

    header = raw[:256]
    is_bdf = (header[0] == 0xFF)
    bytes_per_sample = 3 if is_bdf else 2
    fmt_name = "BDF" if is_bdf else "EDF"

    patient = header[8:88].decode("ascii", errors="replace").strip()
    reserved = header[192:236].decode("ascii", errors="replace").strip()
    if "+" in reserved or "EDF+" in reserved or "BDF+" in reserved:
        fmt_name += "+"
    n_records = int(header[236:244].decode("ascii").strip())
    record_dur = float(header[244:252].decode("ascii").strip())
    ns = int(header[252:256].decode("ascii").strip())

    off = 256

    def read_block(width):
        nonlocal off
        items = []
        for _ in range(ns):
            s, off = _read_ascii(raw, width, off)
            items.append(s)
        return items

    labels = read_block(16)
    _transducer = read_block(80)
    phys_dim = read_block(8)
    phys_min = [float(x) for x in read_block(8)]
    phys_max = [float(x) for x in read_block(8)]
    dig_min = [float(x) for x in read_block(8)]
    dig_max = [float(x) for x in read_block(8)]
    _prefilter = read_block(80)
    n_samp = [int(x) for x in read_block(8)]
    _reserved_sig = read_block(32)

    header_bytes = 256 + ns * 256
    data = raw[header_bytes:]

    scale, offset_phys = [], []
    for i in range(ns):
        d_span = (dig_max[i] - dig_min[i]) or 1.0
        p_span = (phys_max[i] - phys_min[i])
        gain = p_span / d_span
        unit = phys_dim[i].lower()
        if unit == "mv":
            gain *= 1000.0
        elif unit == "v":
            gain *= 1_000_000.0
        scale.append(gain)
        offset_phys.append(phys_min[i] - dig_min[i] * gain)

    samples_per_record = sum(n_samp)
    bytes_per_record = samples_per_record * bytes_per_sample

    rec = Recording()
    rec.meta = {
        "format": fmt_name, "patient": patient, "n_records": n_records,
        "record_dur": record_dur, "source_file": os.path.basename(path),
        "reader": "pure-python",
    }

    raw_signals = [[] for _ in range(ns)]
    pos = 0
    for _r in range(n_records):
        rec_bytes = data[pos:pos + bytes_per_record]
        pos += bytes_per_record
        if len(rec_bytes) < bytes_per_record:
            break
        bp = 0
        for i in range(ns):
            cnt = n_samp[i]
            seg_len = cnt * bytes_per_sample
            seg = rec_bytes[bp:bp + seg_len]
            bp += seg_len
            if _is_annotation_label(labels[i]):
                continue
            if is_bdf:
                vals = _decode_int24(seg, cnt)
            else:
                vals = struct.unpack("<%dh" % cnt, seg)
            g, o = scale[i], offset_phys[i]
            raw_signals[i].extend(v * g + o for v in vals)

    for i in range(ns):
        if _is_annotation_label(labels[i]):
            continue
        name = standardize_channel_name(labels[i])
        uniq, k = name, 2
        while uniq in rec.signals:
            uniq = "%s_%d" % (name, k)
            k += 1
        rec.channels.append(uniq)
        rec.signals[uniq] = raw_signals[i]
        rec.fs[uniq] = (n_samp[i] / record_dur) if record_dur else float(n_samp[i])

    return rec


def _decode_int24(buf, count):
    """24-bitli little-endian belgili butun sonlarni dekodlash (BDF)."""
    out = []
    for j in range(count):
        b0 = buf[3 * j]
        b1 = buf[3 * j + 1]
        b2 = buf[3 * j + 2]
        val = b0 | (b1 << 8) | (b2 << 16)
        if val & 0x800000:
            val -= 0x1000000
        out.append(val)
    return out


# ---------------------------------------------------------------------------
# CSV o'qish (sof Python)
# ---------------------------------------------------------------------------
def read_csv(path, fs=None):
    """CSV fayldan EEG o'qish. 'time' ustunidan fs avtomatik aniqlanishi mumkin."""
    with open(path, "r", newline="") as f:
        reader = list(csv.reader(f))
    if not reader:
        raise ValueError("CSV bo'sh: " + path)

    first = reader[0]

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    has_header = not all(is_number(x) for x in first)
    if has_header:
        names = [c.strip() for c in first]
        rows = reader[1:]
    else:
        names = ["ch%d" % (i + 1) for i in range(len(first))]
        rows = reader

    time_idx = None
    for i, nm in enumerate(names):
        if nm.lower() in ("time", "vaqt", "t", "timestamp"):
            time_idx = i
            break

    cols = {nm: [] for nm in names}
    times = []
    for row in rows:
        if len(row) < len(names):
            continue
        for i, nm in enumerate(names):
            try:
                v = float(row[i])
            except ValueError:
                v = 0.0
            cols[nm].append(v)
            if i == time_idx:
                times.append(v)

    if fs is None and time_idx is not None and len(times) > 2:
        dts = sorted(d for d in (times[k + 1] - times[k] for k in range(len(times) - 1)) if d > 0)
        if dts:
            med = dts[len(dts) // 2]
            fs = 1.0 / med if med > 0 else None
    if fs is None:
        fs = 256.0  # installation7 dagi DEFAULT_FS (zaxira qiymat)

    rec = Recording()
    rec.meta = {"format": "CSV", "source_file": os.path.basename(path), "reader": "pure-python"}
    for nm in names:
        if time_idx is not None and nm == names[time_idx]:
            continue
        std_name = standardize_channel_name(nm)
        uniq, k = std_name, 2
        while uniq in rec.signals:
            uniq = "%s_%d" % (std_name, k)
            k += 1
        rec.channels.append(uniq)
        rec.signals[uniq] = cols[nm]
        rec.fs[uniq] = float(fs)
    return rec


# ---------------------------------------------------------------------------
# Ixtiyoriy: pyedflib orqali o'qish (installation7 yo'li)
# ---------------------------------------------------------------------------
def read_with_pyedflib(path):
    """pyedflib yordamida EDF/BDF o'qish (o'rnatilgan bo'lsa)."""
    import pyedflib  # ixtiyoriy bog'liqlik
    ext = os.path.splitext(path)[1].lower()
    reader = pyedflib.EdfReader(path)
    try:
        ns = reader.signals_in_file
        if ns == 0:
            raise ValueError("EDF/BDF faylda signal kanallari topilmadi.")
        labels = reader.getSignalLabels()
        rec = Recording()
        rec.meta = {
            "format": "BDF/BDF+" if ext == ".bdf" else "EDF/EDF+",
            "source_file": os.path.basename(path), "reader": "pyedflib",
        }
        for i in range(ns):
            if _is_annotation_label(labels[i]):
                continue
            name = standardize_channel_name(labels[i])
            uniq, k = name, 2
            while uniq in rec.signals:
                uniq = "%s_%d" % (name, k)
                k += 1
            rec.channels.append(uniq)
            rec.signals[uniq] = [float(v) for v in reader.readSignal(i)]
            rec.fs[uniq] = float(reader.getSampleFrequency(i))
        return rec
    finally:
        reader.close()


# ---------------------------------------------------------------------------
# Ixtiyoriy: MNE-Python orqali o'qish
# ---------------------------------------------------------------------------
def read_with_mne(path):
    """MNE-Python yordamida EDF/BDF o'qish (mne o'rnatilgan bo'lsa)."""
    import mne  # ixtiyoriy bog'liqlik
    ext = os.path.splitext(path)[1].lower()
    if ext.startswith(".bdf"):
        raw = mne.io.read_raw_bdf(path, preload=True, verbose="ERROR")
    else:
        raw = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
    data = raw.get_data() * 1e6  # V -> µV
    rec = Recording()
    rec.meta = {"format": ext.upper().strip("."), "source_file": os.path.basename(path),
                "reader": "mne"}
    fs = float(raw.info["sfreq"])
    for i, ch_name in enumerate(raw.ch_names):
        name = standardize_channel_name(ch_name)
        uniq, k = name, 2
        while uniq in rec.signals:
            uniq = "%s_%d" % (name, k)
            k += 1
        rec.channels.append(uniq)
        rec.signals[uniq] = list(data[i])
        rec.fs[uniq] = fs
    return rec


# ---------------------------------------------------------------------------
# Universal dispatcher
# ---------------------------------------------------------------------------
def load(path, fs=None, prefer="auto"):
    """
    Fayl kengaytmasiga qarab mos o'quvchini chaqiradi.

    prefer:
      "auto"      — EDF/BDF uchun avval pyedflib, keyin mne, keyin sof Python
      "pyedflib"  — faqat pyedflib (bo'lmasa sof Python)
      "mne"       — faqat mne (bo'lmasa sof Python)
      "pure"      — har doim sof Python parser
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".edf", ".bdf", ".edf+", ".bdf+"):
        if prefer in ("auto", "pyedflib"):
            try:
                return read_with_pyedflib(path)
            except Exception:
                pass
        if prefer in ("auto", "mne"):
            try:
                return read_with_mne(path)
            except Exception:
                pass
        return read_edf_bdf(path)
    if ext == ".csv":
        return read_csv(path, fs=fs)
    raise ValueError("Qo'llab-quvvatlanmaydigan format: " + ext)
