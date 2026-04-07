# 📻 YO Log PRO v19 — Full Edition

**Dezvoltat de:** Ardei Constantin-Cătălin (YO8ACR)  
**Email:** yo8acr@gmail.com  
**Versiune:** 19.0  
**Compatibilitate:** Windows 7 SP1 / 8 / 8.1 / 10 / 11 (x64)  
**Limbă interfață:** Română / Engleză  

[![Build Status](https://github.com/acc1311/YOLogPRO/actions/workflows/build.yml/badge.svg)](https://github.com/acc1311/YOLogPRO/actions)
[![Release](https://img.shields.io/github/v/release/acc1311/YOLogPRO?label=Ultima%20versiune)](https://github.com/acc1311/YOLogPRO/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📥 Descărcare

| Fișier | Descriere |
|--------|-----------|
| `YO_Log_PRO_v19_Setup.exe` | ⭐ **Installer recomandat** — instalează în Program Files, creează scurtătură Desktop + meniu Start |
| `YO_Log_PRO_v19_Portabil.exe` | 💼 **Versiune portabilă** — copiați într-un folder dedicat și rulați direct |
| `YO_Log_PRO_v19_Windows.zip` | 📦 Pachet complet (installer + portabil + README) |

> 📥 Descărcați din tab-ul **[Releases](../../releases/latest)**  
> 💡 Fără Python necesar — executabilul conține totul

---

## 📋 Descriere

YO Log PRO este un program complet de logare pentru radioamatori, destinat atât activității zilnice cât și concursurilor naționale și internaționale. Suportă toate formatele standard de export și import, control CAT bidirecțional, callbook online și offline, DX Cluster și multe altele.

---

## ✅ Funcționalități principale

### 🏆 Concursuri suportate (23+)

| Concurs | Tip scorare | Multiplicatori |
|---------|-------------|----------------|
| Log Simplu | — | — |
| Maraton Ion Creangă | Maraton YO | Județe |
| Cupa Elevului | Per QSO | Județe |
| YO DX HF Contest | Per bandă | DXCC |
| YO VHF/UHF Contest | Distanță km | Grid |
| Field Day | Per QSO | — |
| La Multi Ani YO! | Per QSO | Județe |
| Cupa Moldovei | Special YO8 | Județe+DXCC |
| Cupa 1 Decembrie | Per QSO | Județe |
| Cupa Tomis | Per QSO | Județe |
| Concursul Lucian Blaga | Per QSO | Județe |
| Memorial YO | Per bandă | Județe |
| Cupa Napoca | Per QSO | Județe |
| YO UHF-SHF Marathon | Distanță km | Grid |
| Cupa Fundatiei Zamolxes | Distanță km | Grid |
| Pro Digital Contest | Per QSO | Județe |
| Pro CW Contest | Per QSO | Județe |
| Memorial YO2BCT | Distanță km | Grid |
| SSB Diaspora Românească | Special DX | DXCC |
| Campionat National HF CW | Per QSO | Județe |
| VHF FT8 Activity Contest | Distanță km | Grid |
| Stafetă | Per QSO | Județe |
| Concurs Custom | Configurabil | Configurabil |

### 📡 Control CAT Radio
- **Icom: IC-735 ✓, IC-731, IC-736, IC-737, IC-738, IC-703, IC-7760, IC-7300 MK2, IC-905, IC-705, IC-9700, toate Xiegu (G90, X5105, X6100, X6200, X108G) și multe altele — 50+ modele Icom.
- **Yaesu CAT** — FT-991, FT-817, FT-857, FT-897, FT-847, FT-100, FT-736
- **Icom CI-V** — IC-7300, IC-7610, IC-756, IC-746, IC-7000
- **Kenwood CAT** — TS-590, TS-480, TS-2000, TS-990
- **Elecraft CAT** — K3, KX3, K2
- **Hamlib/rigctld** — suport universal

### 📤 Export

| Format | Versiune | Utilizare |
|--------|----------|-----------|
| Cabrillo | 3.0 și 2.0 | Concursuri |
| ADIF | 3.1 | LoTW, eQSL, orice software |
| CSV | Standard | Excel, analize |
| EDI | REG1TEST | VHF europene |
| Print/Text | — | Raport 90 col. |

### 📥 Import: ADIF, CSV, Cabrillo 2.0/3.0

### 🌐 Callbook

- **ANCOM Local (offline)** — 4 964 indicative YO + 437 repetoare
- **radioamator.ro** — online
- **QRZ.com** — online

### 📊 Instrumente

Band Map, DX Cluster, Scor Live, Rate QSO Stats, Timer concurs, Log Editor dedicat, Verificare hash MD5, Statistici avansate cu grafic per bandă.

### 🎨 Teme: Dark Blue, Dark Green, Dark Red, Dark Purple, Light (Zi), Light Sepia + personalizat

### ⌨️ Scurtături: `Enter` = Log, `Ctrl+S` = Save, `Ctrl+Z` = Undo, `Ctrl+F` = Caută, `F2` = Bandă+, `F3` = Mod+

---

## 💻 Instalare

### Varianta 1 — Installer (recomandat)

1. Descărcați `YO_Log_PRO_v19_Setup.exe` din [Releases](../../releases/latest)
2. Rulați installerul (necesită drepturi de administrator)
3. La final bifați „Lansează YO Log PRO acum"

### Varianta 2 — Portabil (fără instalare)

1. Descărcați `YO_Log_PRO_v19_Portabil.exe` din [Releases](../../releases/latest)
2. Copiați într-un folder dedicat (ex: `D:\RadioAmator\YOLogPRO\`)
3. Rulați direct — datele se salvează în același folder

---

## 🖥️ Cerințe sistem

| Componentă | Minim | Recomandat |
|------------|-------|------------|
| OS | Windows 7 SP1 x64 | Windows 10/11 x64 |
| RAM | 256 MB | 512 MB |
| Spațiu disc | 80 MB | 150 MB |
| Rezoluție | 1024×600 | 1280×720 sau mai mare |
| Python | **NU necesar** | — |

---

## 🔧 Rulare din cod sursă Python

```bash
git clone https://github.com/acc1311/YOLogPRO.git
cd YOLogPRO
pip install -r requirements.txt
python main.py
```

**Dependențe Python:**

| Pachet | Rol | Obligatoriu |
|--------|-----|-------------|
| `tkinter` | Interfață grafică | ✅ Inclus în Python |
| `pyserial` | Control CAT serial | ❌ Opțional |
| `requests` | Callbook online | ❌ Opțional |
| `beautifulsoup4` | Parsare HTML | ❌ Opțional |
| `pandas` + `openpyxl` | Actualizare callbook ANCOM | ❌ Opțional |

---

## 🧪 Rulare teste

```bash
pip install pytest
pytest tests/ -v

# Sau fără pytest:
python -m pytest tests/test_score.py -v
```

**Acoperire (36 teste):** Scoring, duplicate, multiplicatori, validare log, DXCC lookup, import ADIF round-trip, DataManager, helpers v19.

---

## 📁 Structura proiectului

```
YOLogPRO/
├── main.py                        # Punct de intrare + logging
├── yolog/
│   ├── core/
│   │   ├── score.py               # Motor scorare + statistici
│   │   ├── dxcc.py                # Baza DXCC + cty.dat loader
│   │   ├── locator.py             # Maidenhead locator
│   │   └── bands.py               # Benzi HF/VHF/UHF/SHF, moduri
│   ├── data/
│   │   ├── manager.py             # Persistenta JSON atomic
│   │   └── importer.py            # Import ADIF / CSV / Cabrillo
│   ├── hardware/
│   │   └── cat_engine.py          # CAT Yaesu/Icom/Kenwood/Hamlib
│   ├── network/
│   │   ├── callbook.py            # Callbook online
│   │   ├── local_callbook.py      # Callbook local ANCOM (offline)
│   │   ├── callbook_local.json    # Date ANCOM (4964+437)
│   │   └── callbook_updater.py    # Parser XLSX ANCOM
│   ├── export/
│   │   └── exporters.py           # Cabrillo/ADIF/CSV/EDI/Print
│   ├── ui/
│   │   ├── app.py                 # Fereastra principala
│   │   ├── theme.py               # Teme + UIFactory
│   │   └── dialogs/               # Toate dialogurile
│   └── i18n/
│       ├── ro.json                # Traduceri romana
│       └── en.json                # Traduceri engleza
├── scripts/
│   └── update_local_callbook.py   # Actualizare callbook ANCOM
├── tests/
│   ├── test_score.py              # 36 teste pytest
│   └── run_tests.py               # Runner standalone CI
├── .github/workflows/
│   └── build.yml                  # CI/CD build automat
├── installer.nsi                  # Installer Windows NSIS
├── requirements.txt
└── icon.ico
```

---

## 🔄 Actualizare Callbook ANCOM

```bash
python scripts/update_local_callbook.py \
    --callbook  Callbook_NOU.xlsx \
    --repetoare Callbook_repetoare_NOU.xlsx
```

---

## 🚀 Cum se face un Release

1. Mergeți la **Actions → Build YO Log PRO v19 → Run workflow**
2. Opțional adăugați sufix (ex: `rc1`, `beta1`)
3. Click **Run workflow**

GitHub Actions compilează automat EXE, installer NSIS și ZIP, apoi publică release-ul.

---

## 📝 Changelog

### v19.0 — versiunea curentă

#### 🐛 Bug-uri rezolvate
- **Fix critic EXE**: `callbook_local.json` și fișierele `i18n/*.json` nu erau găsite în EXE PyInstaller — fixat cu detecție corectă `sys._MEIPASS`
- **Fix crash**: Funcție `_reload()` duplicată cu variabilă inexistentă în `local_callbook.py`
- **Fix crash**: `rules.get("special_scoring")` putea returna `None` → `if call in None` → crash rezolvat cu guard
- **Fix crash**: `rules.get("county_list")` putea returna `None` în `Score.mults()` și `Score.is_new_mult()`
- **Fix menu**: Label meniu „v18" → „Avansat" în fereastra principală

#### ✨ Funcționalități noi
- `Score.band_summary()` — distribuție QSO per bandă
- `Score.mode_summary()` — distribuție QSO per mod
- `Score.unique_calls()` — număr indicative unice
- `band2freq()` helper în `bands.py`
- Benzi SHF adăugate: `13cm`, `9cm`, `6cm`
- `DataManager.list_logs()` — listare log-uri existente
- `DataManager.data_dir` property
- Statistici complet rescrise: grafic ASCII per bandă, top 10 țări DXCC, rate/durata

#### 🔧 Îmbunătățiri tehnice
- `build.yml`: runner `windows-2019` stabil, Python 3.8, test job separat pe Linux/3.11, toate `--hidden-import` completate
- `i18n/__init__.py`: path compatibil PyInstaller
- `local_callbook.py`: path compatibil PyInstaller, cod duplicat eliminat
- 36 teste (vs 32 în v18)

### v18.0
- Callbook local ANCOM offline, arhitectură modulară, CAT thread-safe, BeautifulSoup4 callbook

### v17.1
- Log Editor, Band Map, DX Cluster, Live Score, Rate Stats, CAT complet

---

## 🤝 Contribuții

1. Fork repo-ul
2. Creați ramură (`git checkout -b feature/functie-noua`)
3. Adăugați teste în `tests/test_score.py`
4. Deschideți Pull Request

---

## 📜 Licență

MIT License — [LICENSE](LICENSE)  
Copyright (c) 2026 Ardei Constantin-Cătălin (YO8ACR)

---

## 📞 Contact

- **Email:** yo8acr@gmail.com
- **GitHub Issues:** [Raportați bug-uri](../../issues)
- **QRZ.com:** [YO8ACR](https://www.qrz.com/db/YO8ACR)

---

*73 de YO8ACR! 📻*
