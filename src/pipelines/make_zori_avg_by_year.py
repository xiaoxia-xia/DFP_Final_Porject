#!/usr/bin/env python3
"""
Create per-city averages for 2024, 2025, and the most recent 12 months
from the Zillow ZORI city-level CSV.

Input : data/raw/zori_city.csv
Output: data/processed/zori_avg_by_year.csv with columns:
        RegionName, State, avg_2024, avg_2025, recent_12mo_avg
"""
from pathlib import Path
import pandas as pd

RAW_PATH = Path("data/raw/zori_city.csv")
OUT_PATH = Path("data/processed/zori_avg_by_year.csv")

def _date_cols(cols):
    """Return {col_name: datetime or NaT} for date-like columns."""
    out = {}
    for c in cols:
        if isinstance(c, str) and any(sep in c for sep in ("-", "/")) and len(c) >= 8:
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

    # --- Identify per-year columns ---
    cols_2024 = [c for c, d in date_map.items() if pd.notna(d) and d.year == 2024]
    cols_2025 = [c for c, d in date_map.items() if pd.notna(d) and d.year == 2025]

    if not cols_2024:
        print("[warn] No 2024 columns found; avg_2024 will be NaN for all rows.")
    if not cols_2025:
        print("[warn] No 2025 columns found; avg_2025 will be NaN for all rows.")

    # --- Recent 12 months ---
    # Sort monthly date columns ascending by actual date, then take the last 12.
    dated_cols_sorted = sorted(
        [ (c, d) for c, d in date_map.items() if pd.notna(d) ],
        key=lambda x: x[1]
    )
    last_12 = [c for c, _ in dated_cols_sorted[-12:]]  # could be < 12 if file is short

    if not last_12:
        print("[warn] Could not determine any monthly columns for recent_12mo_avg; will be NaN.")
        recent_span = "(none)"
    else:
        first_dt = pd.to_datetime(date_map[last_12[0]]).date()
        last_dt  = pd.to_datetime(date_map[last_12[-1]]).date()
        recent_span = f"{first_dt} → {last_dt}"

    # --- Compute row-wise means (skip NaNs) ---
    df["avg_2024"] = df[cols_2024].mean(axis=1, skipna=True) if cols_2024 else float("nan")
    df["avg_2025"] = df[cols_2025].mean(axis=1, skipna=True) if cols_2025 else float("nan")
    df["recent_12mo_avg"] = df[last_12].mean(axis=1, skipna=True) if last_12 else float("nan")

    # --- Select and write ---
    out = df[["RegionName", "State", "avg_2024", "avg_2025", "recent_12mo_avg"]].copy()
    out.to_csv(OUT_PATH, index=False)

    print(f"[ok] Wrote {len(out):,} rows to {OUT_PATH}")
    print(f"[info] recent_12mo_avg computed over: {recent_span}")
    if cols_2024:
        print(f"[info] 2024 months counted: {len(cols_2024)}")
    if cols_2025:
        print(f"[info] 2025 months counted: {len(cols_2025)}")

if __name__ == "__main__":
    main()
