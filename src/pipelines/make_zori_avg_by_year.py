#!/usr/bin/env python3
"""
Create per-city averages for 2024 and 2025 from Zillow ZORI (city-level) CSV.

Input : data/raw/zori_city.csv
Output: data/processed/zori_avg_by_year.csv with columns:
        RegionName, State, avg_2024, avg_2025
"""
from pathlib import Path
import pandas as pd

RAW_PATH = Path("data/raw/zori_city.csv")
OUT_PATH = Path("data/processed/zori_avg_by_year.csv")

def _date_cols(cols):
    """Return {col_name: datetime or NaT} for date-like columns."""
    out = {}
    for c in cols:
        if isinstance(c, str) and len(c) >= 8 and any(sep in c for sep in ("-", "/")):
            out[c] = pd.to_datetime(c, errors="coerce")
    return out

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_PATH)
    # Basic checks
    for required in ("RegionName", "State"):
        if required not in df.columns:
            raise SystemExit(f"[error] Missing required column: {required}")

    date_map = _date_cols(df.columns)
    if not date_map:
        raise SystemExit("[error] No date-like columns detected in CSV.")

    cols_2024 = [c for c, d in date_map.items() if pd.notna(d) and d.year == 2024]
    cols_2025 = [c for c, d in date_map.items() if pd.notna(d) and d.year == 2025]

    if not cols_2024:
        print("[warn] No 2024 columns found; avg_2024 will be NaN for all rows.")
    if not cols_2025:
        print("[warn] No 2025 columns found; avg_2025 will be NaN for all rows.")

    # Compute row-wise means (skip NaNs)
    df["avg_2024"] = df[cols_2024].mean(axis=1, skipna=True) if cols_2024 else float("nan")
    df["avg_2025"] = df[cols_2025].mean(axis=1, skipna=True) if cols_2025 else float("nan")

    out = df[["RegionName", "State", "avg_2024", "avg_2025"]].copy()
    out.to_csv(OUT_PATH, index=False)
    print(f"[ok] Wrote {len(out):,} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()
