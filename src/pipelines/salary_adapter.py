#!/usr/bin/env python3
"""
Reads data/software-devops-junior-avg-salary.csv and writes 5 per-job CSVs:
- data_analyst_salary.csv
- analyst_salary.csv
- data_scientist_salary.csv
- software_engineer_salary.csv
- software_development_engineer_salary.csv
All with at least columns: City, Salary (State kept if present).
"""
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")
SRC = DATA_DIR / "software-devops-junior-avg-salary.csv"

TARGETS = [
    "data_analyst_salary.csv",
    "analyst_salary.csv",
    "data_scientist_salary.csv",
    "software_engineer_salary.csv",
    "software_development_engineer_salary.csv",
]

def main():
    if not SRC.exists():
        raise SystemExit(f"Expected source salary file not found: {SRC}")

    df = pd.read_csv(SRC)
    # Robust column detect
    city_col = next((c for c in df.columns if c.lower()=="city"), None)
    sal_col  = next((c for c in df.columns if "salary" in c.lower()), None)
    state_col = next((c for c in df.columns if c.lower()=="state"), None)

    if not city_col or not sal_col:
        raise RuntimeError(f"Need City and Salary-like columns in {SRC.name}. Found: {df.columns.tolist()}")

    keep = [city_col, sal_col] + ([state_col] if state_col else [])
    out = df[keep].rename(columns={city_col:"City", sal_col:"Salary"})
    out["Salary"] = pd.to_numeric(out["Salary"], errors="coerce")

    for name in TARGETS:
        path = DATA_DIR / name
        out.to_csv(path, index=False)
        print(f"Wrote {path.resolve()}")

if __name__ == "__main__":
    main()
