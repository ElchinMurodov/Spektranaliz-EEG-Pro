# Spektranaliz EEG Pro

**Sportchining Elektroensefalografik (EEG) signallarini spektral tahlil qilish algoritmi va dasturiy vositasi**

Ushbu dastur ikki loyihaning **birlashtirilgan va optimallashtirilgan** ko'rinishidir:

- [**Spektranaliz-EEG-installation7**](https://github.com/ElchinMurodov/Spektranaliz-EEG-installation7) — chiroyli Tkinter GUI, fon/logotip, `.exe` ga yig'ish (Windows o'rnatuvchi).
- [**EEG-signal-edf-bdf**](https://github.com/ElchinMurodov/EEG-signal-edf-bdf) — modular, sof Python ilmiy yadro (custom FFT/EDF parser, zona tahlili, HTML/SVG hisobot).

> **Tamoyil:** *Dizayn va dastur tuzilishi* installation7 dan olingan; *tahlil algoritmi* esa ikkala dasturning eng kuchli tomonlarini birlashtiradi. Natijada **birida bor, birida yo'q** barcha funksiya va chiqaruvchi natijalar bitta dasturda jamlangan.

---

## 1. Ikki dastur algoritmlari o'rtasidagi farq

| Jihat | installation7 | EEG-signal-edf-bdf | **EEG Pro (birlashma)** |
|------|----------------|--------------------|--------------------------|
| Interfeys | Tkinter GUI (dizayn) | CLI + HTML hisobot | **GUI + CLI + HTML** |
| Tuzilish | Bitta fayl (~1000 qator) | Modular paket | **GUI + modular `eeg_engine`** |
| EDF/BDF o'qish | `mne`/`pyedflib` (tashqi) | Sof Python parser | **Ikkalasi (avto fallback)** |
| Spektral usul | `scipy.welch` | Sof Python Welch | **Ikkalasi (avto)** |
| Tashqi kutubxonaga bog'liqlik | Majburiy (numpy/scipy) | Yo'q | **Yo'q (ixtiyoriy tezlashtirish)** |
| Harmonizatsiya (resampling) | Yuklashda median fs | Anti-aliasing bilan maqsadli fs | **Maqsadli fs + anti-aliasing** |
| Zona/kanal tahlili | Yo'q (faqat global) | 10-20 tizimi, zonalar | **10-20 tizimi, zonalar** |
| iAPF (alfa cho'qqisi) | ✗ | ✓ | **✓** |
| FAA (frontal alfa asimmetriyasi) | ✗ | ✓ | **✓** |
| FMT (frontal-median teta) | ✗ | ✓ | **✓** |
| Engagement indeksi | ✓ | ✗ | **✓** |
| Dominant chastota (PSD + FFT) | ✓ | ✗ | **✓** |
| Spektral chegara (edge 95%) | ✓ | ✗ | **✓** |
| Individual kalibrlash (baseline) | ✗ | ✓ | **✓** |
| Atipik naqshni aniqlash | ✗ | ✓ | **✓** |
| Ishonch darajasi (softmax) | ✗ (faqat 0-100 ball) | ✓ | **✓ (ball + ishonch %)** |
| HTML/SVG hisobot (topomap) | ✗ | ✓ | **✓** |
| `.exe` / o'rnatuvchi | ✓ | ✗ | **✓** |
| Sun'iy ma'lumot generatori | ✗ | ✓ | **✓** |

### Holatlar to'plamidagi farq

- **installation7:** Charchoq, Uyqusizlik, Normal, Fokus, Xayojonlanish, Stress, Meditativ holat
- **edf-bdf:** Normal, Fokus, Charchoq, Uyquga moyillik, Qo'zg'alish, Stress, Meditativ

**EEG Pro** ikkala to'plamni birlashtiradi (8 holat). "Uyqusizlik" (tinch holatda yuqori qo'zg'alish, alfa kam) va "Uyquga moyillik" (sekin ritmlar ustun) — fiziologik jihatdan **qarama-qarshi** holatlar, shuning uchun ikkalasi ham saqlangan:

> **Normal · Fokus · Charchoq · Uyquga moyillik · Uyqusizlik · Qo'zg'alish / Xayojonlanish · Stress · Meditativ**

### Asosiy algoritmik xulosa

1. **installation7** — kuchli signal tozalash (MAD asosida artefakt cheklash, IIR notch/bandpass `filtfilt`) va boy *global* spektral belgilar (engagement, dominant chastota, spektral chegara), lekin **kanal/zona** tahlili va vizualizatsiya yo'q; tashqi kutubxonalarga bog'liq.
2. **edf-bdf** — *neyrofiziologik* yondashuv: 10-20 tizimi bo'yicha zonalar, iAPF/FAA/FMT markerlari, harmonizatsiya, individual kalibrlash va HTML/SVG topomap; tashqi kutubxonasiz ishlaydi, lekin GUI va `.exe` yo'q.
3. **EEG Pro** — har ikkala yondashuvni birlashtiradi: **GUI dizayni + sof Python ishonchli yadro + barcha belgilar + barcha chiqaruvchi natijalar**.

---

## 2. Imkoniyatlar (chiqaruvchi natijalar)

- Qo'llab-quvvatlanadigan formatlar: **EDF / EDF+ / BDF / BDF+ / CSV**
- Ritmlar bo'yicha quvvat (absolyut va nisbiy %): Delta, Theta, Alpha, Beta, Gamma
- Belgilar: **iAPF, FAA, FMT, engagement, dominant chastota (PSD va FFT), spektral chegara (edge 95%), Alpha/Beta, Theta/Beta, Theta/Alpha, Beta/Alpha, spektral entropiya**
- 10-20 tizimi bo'yicha **zonaviy** taqsimot (frontal, central, parietal, occipital, temporal)
- 8 funksional holat bo'yicha **ball (0-100)** va **softmax ishonch (%)**
- **Atipik naqsh** ogohlantirishlari
- **Natijalar oynasida CHIROYLI ZAMONAVIY GRAFIKLAR** — **tablarga ajratilgan** (Umumiy / Spektr / Topografiya / Kanallar): gradiyentli sarlavha, ishonch **halqa-diagrammasi (donut)**, to'ldirilgan PSD grafigi, yumaloq ustunlar, **topomap**, holatlar diagrammasi
- **Rang temasi** almashtiriladi: **Akademik (dissertatsiya)** yoki **Zamonaviy** (menyu: Vositalar → Rang temasi)
- Natijani **uch formatda eksport**: **HTML** (SVG grafikli), **PDF** (ko'p sahifali grafikli poster), **TXT** (matnli)
- **PDF hisobot 2 bo'limdan iborat**: (1) asosiy hisobot, (2) batafsil zonaviy/kanal tahlili — **har bir ritm uchun alohida topomap** (Delta…Gamma), zona×ritm issiqlik-jadvali va kanallar jadvali
- **HTML + SVG** vizual hisobot: PSD chizig'i, ritm ustunlari, **topografik xarita (topomap)**, holat ehtimolliklari
- **Individual kalibrlash** (tinch holat baseline) va **harmonizatsiya** (maqsadli fs)

---

## 3. Loyiha tuzilishi

```
Spektranaliz-EEG-Pro/
├── Spektranaliz EEG Pro.py     # Tkinter GUI (installation7 dizayni) -> eeg_engine ga ulangan
├── cli.py                      # Buyruq qatori interfeysi
├── eeg_engine/                 # BIRLASHTIRILGAN tahlil yadrosi (sof Python)
│   ├── config.py               # ritmlar, zonalar, 8 holat, sozlamalar
│   ├── dsp.py                  # FFT/DSP (sof Python + numpy tezlashtirish)
│   ├── loader.py               # EDF/EDF+/BDF/BDF+/CSV o'qish
│   ├── preprocessing.py        # tozalash, filtrlash, harmonizatsiya
│   ├── spectral.py             # Welch PSD, band power, dominant, edge
│   ├── features.py             # iAPF, FAA, FMT, engagement, ...
│   ├── calibration.py          # individual baseline normalizatsiya
│   ├── classifier.py           # 8 holat + softmax + atipik aniqlash
│   ├── report.py               # matnli hisobot
│   ├── charts.py               # PIL grafiklari (PSD, ustunlar, topomap) + PDF
│   ├── visualize.py            # HTML + SVG (topomap)
│   └── pipeline.py             # to'liq zanjir (analyze_objects / analyze_file)
├── tools/make_synthetic.py     # sinov uchun sun'iy EEG generatori
├── data/                       # namuna fayllar
├── requirements.txt
├── spektranaliz_eeg_pro.spec   # PyInstaller
├── build.bat                   # Windows: .exe + o'rnatuvchi yig'ish
├── installer.iss               # Inno Setup o'rnatuvchi
└── make_assets.py              # SVG -> .ico/.png rasterlash
```

> **Eslatma:** Tahlil yadrosi (`eeg_engine`) sof Python da yozilgan va hech qanday tashqi kutubxonasiz ishlaydi. `numpy`/`scipy`/`pyedflib`/`mne` mavjud bo'lsa — avtomatik aniqlanadi va tezlik/aniqlik uchun ishlatiladi.

---

## 4. Foydalanish

### GUI (asosiy dastur)
```bash
pip install -r requirements.txt        # tavsiya etiladi (GUI uchun pillow shart)
python "Spektranaliz EEG Pro.py"
```
"Fayl tanlash" → EEG faylni tanlang → "Natijani olish". Natijalar oynasida natija **tablarga ajratilgan** chiroyli grafiklarda chiqadi: **Umumiy · Spektr (PSD) · Topografiya · Kanallar**. Pastdagi **HTML / PDF / TXT** tugmalari yoki yuqori menyu orqali eksport qiling. Menyu (Vositalar) orqali: **rang temasi** (Akademik/Zamonaviy), **individual kalibrlash (baseline)** va **harmonizatsiya** chastotasi.

### CLI (terminal / skript)
```bash
python cli.py data/0000007.EDF
python cli.py data/synth_stress_100hz.edf --html hisobot.html --pdf hisobot.pdf --txt hisobot.txt
python cli.py signal.csv --fs 256
python cli.py data/synth_fokus_500hz.edf --target-fs 100
python cli.py mashqdan_keyin.edf --baseline dam_olish.edf
```

### Sun'iy sinov ma'lumotlari
```bash
python tools/make_synthetic.py     # data/ ichida turli holatdagi EEG yaratadi
```

### Windows `.exe` va o'rnatuvchi
`build.bat` ni ishga tushiring (Python 3.10+ kerak). Natija: `dist/Spektranaliz EEG Pro/Spektranaliz EEG Pro.exe` va (Inno Setup bo'lsa) `installer/Spektranaliz-EEG-Pro-Setup.exe`.

---

## 5. Muhim eslatma

> Ushbu dastur **tibbiy tashxis vositasi emas**. U EEG signalining funksional holat ko'rsatkichlarini (spektral indekslarni) ifodalaydi. Klassifikator chegaralari **namunaviy** bo'lib, haqiqiy ilmiy ishda yorliqlangan (ground-truth) ma'lumotlar asosida kalibrlanishi yoki mashinaviy o'qitish (ML) klassifikatori bilan almashtirilishi tavsiya etiladi. Yakuniy talqin malakali mutaxassis (nevrolog / EEG shifokori) tomonidan amalga oshiriladi.

---

© Murodov Elchin O‘ktamovich
