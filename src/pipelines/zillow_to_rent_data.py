#!/usr/bin/env python3
"""
Outputs: data/rent_data.csv with columns:
- RegionName (city)
- State (2-letter)
- avg_rent (recent 12-month average)
"""
from pathlib import Path
import datetime as dt
import pandas as pd
import requests

ZILLOW_URL = "https://files.zillowstatic.com/research/public_csvs/zori/City_zori_uc_sfrcondomfr_sm_month.csv"
DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_CSV = DATA_DIR / "City_zori_uc_sfrcondomfr_sm_month.csv"
OUT_CSV = DATA_DIR / "rent_data.csv"

def download(url: str, dest: Path):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)

def last_n_month_cols(df: pd.DataFrame, n: int):
    dates = []
    for c in df.columns:
        try:
            dates.append((dt.date.fromisoformat(c), c))
        except Exception:
            pass
    dates.sort()
    return [c for _, c in dates[-n:]]

def zillow_to_rent_main():
    print("Downloading Zillow ZORI city CSV...")
    download(ZILLOW_URL, RAW_CSV)

    df = pd.read_csv(RAW_CSV)

    # Column detection across Zillow schema variants
    city_col = "City" if "City" in df.columns else ("RegionName" if "RegionName" in df.columns else None)
    state_col = "StateName" if "StateName" in df.columns else ("State" if "State" in df.columns else "StateName")
    if city_col is None:
        raise RuntimeError("Could not find city column (City/RegionName) in Zillow file.")

    month_cols = [c for c in df.columns if c[:4].isdigit() and "-" in c]
    use = df[[city_col, state_col] + month_cols].copy()
    use.rename(columns={city_col: "RegionName", state_col: "State"}, inplace=True)

    last12 = last_n_month_cols(use, 12)
    if len(last12) == 0:
        raise RuntimeError("No month columns detected to compute 12-month average.")
    use["avg_rent"] = use[last12].mean(axis=1, skipna=True)

    out = use[["RegionName", "State", "avg_rent"]].copy()
    out.sort_values(["State","RegionName"], inplace=True, na_position="last")
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV.resolve()}")

if __name__ == "__main__":
    zillow_to_rent_main()
