# UrbanLens — City Affordability Explorer

A small, CLI‑driven toolchain that combines **rent (Zillow ZORI)**, **crime (FBI CDE API)**, and **salary (Levels.fyi web data)** to help you compare cities by an affordability index.

---

## 👥 UrbanLens Team (CMU Heinz)
- **Tingting An** — *tingtina*
- **Xiaoxia Xia** — *xxia2*
- **Jingwei Xiong** — *jxiong2*
- **Hairan Yu** — *hairany*
- **Lyra Liu** — *lyral*

---

## 📦 What’s included
- `urbanLens_team_main.py` — interactive CLI that ties everything together.
- `zillow_to_rent_data.py` — downloads and aggregates Zillow ZORI rent data to `data/rent_data.csv`.
- `fbi_crime_pipeline.py` — pulls state‑level crime rates (FBI CDE API) and outputs `data/crime_data.csv`.
- `scrape_levels.py` — scrapes Levels.fyi pages for a given job role and saves a per‑city salary CSV (e.g., `data/web_developer_salary.csv`).
- `requirements.txt` — pinned Python dependencies.
- `data/` — created at runtime; all CSV outputs are written here.
- `auth.json` — for login in to Levels/fyi


---

## 🧰 Prerequisites
- Python **3.10+** (3.11 recommended)
- macOS / Linux / Windows
- Ability to install Python packages (no admin required)
- Internet access (to download Zillow CSVs, FBI API data, and to scrape Levels.fyi)

---

## 🐍 1) Create a virtual environment (recommended)
```bash
# from the project root (same folder as this README)
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\\Scripts\\Activate.ps1
```

To deactivate later: `deactivate`

---

## 📥 2) Install dependencies (manual)
Install exactly the packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```
**Playwright browsers:** after installing the Python package, install a browser engine for scraping:
```bash
python -m playwright install chromium
```

> We intentionally **do not auto‑install** anything in code. All installation is **manual** per course rules.


---

## ▶️ How to run (end‑to‑end)

Run programmatically via the main app (recommended), or directly:

```bash
# example: run the main app and choose the role interactively (see below)
python urbanLens_team_main.py
```


---

## 📁 Expected files after a successful run
```
.
├── README.md
├── requirements.txt
├── urbanLens_team_main.py
├── zillow_to_rent_data.py
├── fbi_crime_pipeline.py
├── scrape_levels.py
├── auth.json              # created by you (optional but recommended)
└── data/
    ├── rent_data.csv
    ├── crime_data.csv
    ├── web_developer_salary.csv                # role‑specific (example)
    └── <other role salary files>.csv
```

---


