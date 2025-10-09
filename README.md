# UrbanLens — City Affordability Explorer

UrbanLens ranks cities by an **affordability index** tailored to a chosen **job** and **state**, combining:
- **Salary** (Levels.fyi scrape, averaged by city)
- **Rent** (Zillow ZORI 12-month average, city level)
- **Crime** (FBI Crime Data API, state composite score)

One clear entry point: `urbanLens_team_main.py`.

---

## UrbanLens Team

- Tingting An
- Xiaoxia Xia
- Jingwei Xiong
- Hairan Yu
- Lyra Liu


---

## Data sources & acquisition

1) **Zillow ZORI (city)** — downloaded CSV (official monthly data)  
2) **FBI Crime Data Explorer (state)** — REST API (annual estimates 2020–2024)  
3) **Levels.fyi** — web scraping (junior SWE/DevOps comp → aggregated by city/state)

We cache processed CSVs in `data/` so graders can run the app quickly. You can refresh on demand.

---

## Project structure

```
.
├── urbanLens_team_main.py          # single MAIN entry point (run this)
├── config.yaml                     # base config (safe defaults, no secrets)
├── config.local.yaml               # local secrets (gitignored, optional)
├── requirements.txt                # all dependencies
├── Makefile                        # convenience targets (optional but included)
├── src/
│   ├── scrapers/
│   │   ├── login_levels.py         # first-time login → saves data/auth.json
│   │   └── scrape_levels.py        # scrapes salary → software-devops-junior-avg-salary.csv
│   └── pipelines/
│       ├── zillow_to_rent_data.py  # Zillow → rent_data.csv
│       ├── fbi_crime_pipeline.py   # FBI API → crime_data.csv (+ ranking CSV)
│       └── salary_adapter.py       # fan-out 1 salary CSV → 5 per-job salary CSVs
└── data/                           # generated artifacts (gitignored)
```

---

## Install (manual; no auto-installs in program)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install     # one-time, installs browsers for scraping
```

---

## Prepare data (cached vs. refresh)

We ship **pipelines** to build exactly the CSVs `urbanLens_team_main.py` expects.  
You can use the **Makefile** or run Python scripts directly.

### 0) First-time Levels.fyi login (saves session)
```bash
python src/scrapers/login_levels.py
# a browser opens; log in, then press ENTER in terminal to save data/auth.json
```

### 1) Zillow → rent
```bash
python src/pipelines/zillow_to_rent_data.py
# writes data/rent_data.csv  (columns: RegionName, State, avg_rent)
```

### 2) FBI → crime
```bash
# ensure FBI_API_KEY set via ENV or config.local.yaml
python src/pipelines/fbi_crime_pipeline.py
# writes data/crime_data.csv (State, composite_score)
# and data/ranking_2020_2024.csv (details)
```

### 3) Levels.fyi → salary
```bash
python src/scrapers/scrape_levels.py
python src/pipelines/salary_adapter.py
# writes data/software-devops-junior-avg-salary.csv (unified)
# and fans out:
#   data_analyst_salary.csv
#   analyst_salary.csv
#   data_scientist_salary.csv
#   software_engineer_salary.csv
#   software_development_engineer_salary.csv
```

### Makefile shortcuts (optional)

```bash
make venv           # create venv + install deps + playwright browsers
make data-zillow    # build rent_data.csv
make data-crime     # build crime_data.csv (needs FBI_API_KEY)
make data-salary    # scrape + fan-out salary CSVs
make data-all       # all of the above
```

**Caching vs refresh**  
- We **reuse** CSVs in `data/` for fast, reproducible runs.  
- Refresh on demand by re-running the respective pipeline target.  
  - Zillow: monthly cadence (TTL ~30 days)  
  - Crime: yearly cadence (TTL ~365 days)  
  - Salary: weekly/manual as needed (TTL ~7 days)

---

## Run the main program

Interactive (prompts for job & state):
```bash
python urbanLens_team_main.py
```

With flags:
```bash
python urbanLens_team_main.py --job "Software Engineer" --state PA --top 25
python urbanLens_team_main.py --job "Data Scientist"  --state "Pennsylvania"
```

Output: a ranked table of cities in the chosen state and a CSV snapshot:
```
data/affordability_<STATE>_<job>.csv
```

---

## Troubleshooting

- **Missing `FBI_API_KEY`** → Set via `export FBI_API_KEY=...` or `config.local.yaml`.  
- **First-time scrape fails** → Run `python src/scrapers/login_levels.py`, complete login, then re-run `scrape_levels.py`.  
- **Slow scraping / site layout changed** → Use cached CSVs in `data/` or refresh later.  
- **No city matches** → Ensure salary CSV has `City` names that exist in Zillow for that state; the main infers state for salaries where possible.  
- **Playwright not installed** → Run `python -m playwright install` once after `pip install`.

---

## Notes on rubric alignment

- **Single main**: `urbanLens_team_main.py` is the only entry point.  
- **One README**: this file.  
- **Manual installs**: via `requirements.txt`; no hidden installs at runtime.  
- **No hard-coded absolute paths**: all paths are relative to the repo (configurable in `config.yaml`).  
- **Fresh vs cached**: CSV caching in `data/` with explicit refresh steps.  
- **≥3 sources & variety**: direct CSV (Zillow), API (FBI), web scraping (Levels.fyi).  
- **Basic comments & file headers**: included in scripts.

