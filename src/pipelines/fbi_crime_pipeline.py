
#!/usr/bin/env python3
# fbi_crime_pipeline.py — config-free, based on original working script
# - Uses the summarized/state endpoint for offenses 'V' and 'P'
# - Computes average 2020–2024 rates and a weighted composite
# - Writes:
#     data/ranking_2020_2024.csv
#     data/crime_data.csv  (State, composite_score) for main()

import os, re, json, time, math
from typing import Dict, List, Optional
import requests, pandas as pd
from pathlib import Path

# ========= OUTPUT PATHS =========
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
RANK_OUT = DATA_DIR / "ranking_2020_2024.csv"
CRIME_OUT = DATA_DIR / "crime_data.csv"

# ========= CONFIGURATION =========
BASE_URL = "https://api.usa.gov/crime/fbi/cde/summarized/state/{state}/{offense}"
API_KEY  = "pLhhs0FMf8vSGF2r9pc8gIyPJcCBMmgo7deDAQif"  # fallback / grading convenience
FROM_MM_YYYY = "01-2020"
TO_MM_YYYY   = "12-2024"
FROM_YEAR, TO_YEAR = int(FROM_MM_YYYY[-4:]), int(TO_MM_YYYY[-4:])

# 50 states
STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
]

STATE_ABBR_TO_FULL = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
    "DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan",
    "MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
    "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
    "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"
}

WEIGHT_V, WEIGHT_P = 0.70, 0.30
TIMEOUT, RETRY = 30, 4
DATE_KEY = re.compile(r"^\d{2}-\d{4}$|^\d{4}-\d{2}$|^\d{4}$")

# ========= HELPERS =========
def _year_from_date(s) -> Optional[int]:
    if s is None: return None
    if isinstance(s, int): return s
    ss = str(s)
    if "-" in ss:
        a, b = ss.split("-", 1)
        if len(b)==4 and b.isdigit(): return int(b)  # mm-YYYY
        if len(a)==4 and a.isdigit(): return int(a)  # YYYY-mm
    if ss.isdigit() and len(ss)==4: return int(ss)
    return None

def _avg_rate_2020_2024(rows: List[Dict]) -> float:
    if not rows: return math.nan
    df = pd.DataFrame(rows)
    if df.empty or "rate" not in df: return math.nan
    df["year"] = df["date"].map(_year_from_date)
    df = df[(df["year"]>=FROM_YEAR) & (df["year"]<=TO_YEAR)].dropna(subset=["rate"])
    if df.empty: return math.nan
    annual = df.groupby("year")["rate"].mean()
    return float(annual.mean())

# ========= PARSE VARIED JSON STRUCTURES =========
def extract_rate_rows(js: Dict, state_abbr: str) -> List[Dict]:
    rows: List[Dict] = []

    # A) Simple dict of date -> value
    if isinstance(js, dict) and "results" not in js and "data" not in js and "offenses" not in js:
        for k, v in js.items():
            if isinstance(k, str) and DATE_KEY.match(k):
                try: rows.append({"date": k, "rate": float(v)})
                except Exception: rows.append({"date": k, "rate": math.nan})
        if rows: return rows

    # B) Nested JSON: offenses.rates.<FullStateName>
    if isinstance(js, dict) and "offenses" in js:
        try:
            full = STATE_ABBR_TO_FULL[state_abbr]
            series = js["offenses"]["rates"].get(full)
            if isinstance(series, dict):
                for k, v in series.items():
                    if isinstance(k, str) and DATE_KEY.match(k):
                        try: rows.append({"date": k, "rate": float(v)})
                        except Exception: rows.append({"date": k, "rate": math.nan})
                if rows: return rows
        except Exception:
            pass

    # C) Fallback: results/data list
    container = js if isinstance(js, list) else (js.get("results") or js.get("data") or [])
    for r in container:
        dt = r.get("date") or r.get("data_year") or r.get("year")
        rate = r.get("rate", r.get("crime_rate", r.get("value")))
        try: rate = float(rate)
        except Exception: rate = math.nan
        rows.append({"date": dt, "rate": rate})
    return rows

# ========= FETCH ONE SERIES =========
def fetch_rate_series(state: str, offense: str) -> List[Dict]:
    url = BASE_URL.format(state=state, offense=offense)
    params = {"from": FROM_MM_YYYY, "to": TO_MM_YYYY, "API_KEY": API_KEY, "api_key": API_KEY}
    headers = {"Accept": "application/json"}
    last = None
    for i in range(1, RETRY+1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            if resp.status_code in (429,) or resp.status_code >= 500:
                raise requests.HTTPError(f"{resp.status_code}: {resp.text[:160]}")
            resp.raise_for_status()
            js = resp.json()
            rows = extract_rate_rows(js, state)
            if not rows:
                print(f"Warning: Could not parse rate: {state}/{offense} url={resp.url} payload[:200]={resp.text[:200]}")
            return rows
        except Exception as e:
            last = e
            time.sleep(0.4 * i)
    raise RuntimeError(f"Request failed {state}/{offense}: {last}")

# ========= MAIN =========
def main():
    recs = []
    for st in STATES:
        try:
            v_rows = fetch_rate_series(st, "V"); time.sleep(0.08)
            p_rows = fetch_rate_series(st, "P"); time.sleep(0.08)
            v_avg = _avg_rate_2020_2024(v_rows)
            p_avg = _avg_rate_2020_2024(p_rows)

            wv = WEIGHT_V if not math.isnan(v_avg) else 0.0
            wp = WEIGHT_P if not math.isnan(p_avg) else 0.0
            den = wv + wp
            comp = (wv*v_avg + wp*p_avg)/den if den>0 else math.nan

            recs.append({
                "state": st,
                "violent_rate_per_100k": v_avg,
                "property_rate_per_100k": p_avg,
                "composite_score": comp
            })
        except Exception as e:
            print(f"ERROR {st}: {e}")

    df = pd.DataFrame(recs)
    df = df.sort_values(
        by=["composite_score","violent_rate_per_100k","property_rate_per_100k"],
        ascending=[True,True,True],
        na_position="last"
    ).reset_index(drop=True)
    df.insert(0, "rank", df.index+1)
    df["period_start"], df["period_end"] = FROM_YEAR, TO_YEAR

    cols = ["rank","state","violent_rate_per_100k","property_rate_per_100k","composite_score","period_start","period_end"]
    df = df[cols]

    # Write detailed ranking
    df.to_csv(RANK_OUT, index=False, encoding="utf-8")
    print(f"Exported: {RANK_OUT.resolve()}")

    # Also produce main() input: State (full name), composite_score
    out2 = df[["state","composite_score"]].copy()
    out2.rename(columns={"state":"State"}, inplace=True)
    out2["State"] = out2["State"].map(STATE_ABBR_TO_FULL).fillna(out2["State"])
    out2.to_csv(CRIME_OUT, index=False, encoding="utf-8")
    print(f"Exported: {CRIME_OUT.resolve()}")

if __name__ == "__main__":
    print(f"Period: {FROM_MM_YYYY}~{TO_MM_YYYY}")
    main()
