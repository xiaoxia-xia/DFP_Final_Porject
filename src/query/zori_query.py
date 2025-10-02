#!/usr/bin/env python3
"""
Query Zillow ZORI (city-level CSV) by city/state and year-month.

Examples
--------
# exact city:
python src/query/zori_query.py --city "Pittsburgh" --state PA --ym 2024-07

# state-only aggregate:
python src/query/zori_query.py --state PA --ym 2024-07 --aggregate mean

# list available month columns (ISO):
python src/query/zori_query.py --list-dates
"""
import argparse
import sys
import calendar
from pathlib import Path
from datetime import date, datetime

import pandas as pd


# ---------- date helpers ----------
def parse_year_month(ym_str: str) -> date:
    """Parse many year-month formats and return the last day of that month."""
    s = ym_str.strip()
    # Try strict formats first
    for fmt in ("%Y-%m", "%Y/%m", "%m/%Y", "%b-%Y", "%b %Y", "%B-%Y", "%B %Y"):
        try:
            ts = pd.to_datetime(s, format=fmt)
            y, m = ts.year, ts.month
            last = calendar.monthrange(y, m)[1]
            return date(y, m, last)
        except Exception:
            pass
    # Fallback to pandas inference
    ts = pd.to_datetime(s, errors="raise")
    y, m = ts.year, ts.month
    last = calendar.monthrange(y, m)[1]
    return date(y, m, last)


def _try_parse_date_header(text: str):
    """Attempt to parse a header string as a date. Return datetime or None."""
    t = text.strip()
    # Try a handful of common formats in Zillow files
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d",  # ISO-ish
        "%m/%d/%Y", "%-m/%-d/%Y",  # US long year
        "%m/%d/%y", "%-m/%-d/%y",  # US short year
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(t, fmt)
        except Exception:
            continue
    # Last resort: let pandas try
    try:
        return pd.to_datetime(t, errors="raise").to_pydatetime()
    except Exception:
        return None


def build_date_index(columns) -> dict:
    """
    Build a mapping from normalized ISO 'YYYY-MM-DD' -> actual column name.
    Works for headers like '2015-01-31', '2015/01/31', '1/31/15', etc.
    """
    mapping = {}
    for col in columns:
        if not isinstance(col, str):
            continue
        dt = _try_parse_date_header(col)
        if dt is None:
            continue
        iso = dt.strftime("%Y-%m-%d")
        mapping[iso] = col  # prefer the *original* column name
    return mapping


# ---------- CSV load & selection ----------
def load_city_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for col in ("RegionName", "State"):
        if col not in df.columns:
            raise SystemExit(f"[error] CSV missing required column: {col}")
    df["RegionName_norm"] = df["RegionName"].astype(str).str.strip().str.casefold()
    df["State_norm"] = df["State"].astype(str).str.strip().str.upper()
    return df


def select_city_row(df: pd.DataFrame, city: str, state: str) -> pd.DataFrame:
    city_norm = str(city).strip().casefold()
    state_norm = str(state).strip().upper()
    return df[(df["RegionName_norm"] == city_norm) & (df["State_norm"] == state_norm)]


# ---------- main query ----------
def query_value(df: pd.DataFrame, city: str | None, state: str, ym: str,
                aggregate: str | None, date_map: dict) -> float:
    target_dt = parse_year_month(ym)
    iso_key = target_dt.strftime("%Y-%m-%d")
    col = date_map.get(iso_key)
    if not col:
        available = sorted(date_map.keys())
        hint = ", ".join(available[-12:]) or "(no month columns detected)"
        raise SystemExit(
            f"[error] Month column not found for {iso_key}. "
            f"Available recent months: {hint}"
        )

    if city:
        rows = select_city_row(df, city, state)
        if rows.empty:
            hint = df[df["State_norm"] == str(state).strip().upper()]["RegionName"].unique()
            raise SystemExit(f"[error] No city='{city}' in state='{state}'. "
                             f"Try one of: {sorted(hint)[:15]}{' ...' if len(hint)>15 else ''}")
        if len(rows) > 1:
            rows = rows.head(1)
        val = rows.iloc[0][col]
        try:
            return float(val)
        except Exception:
            raise SystemExit(f"[error] Cell is not numeric: {val!r}")
    else:
        subset = df[df["State_norm"] == str(state).strip().upper()]
        if subset.empty:
            raise SystemExit(f"[error] No rows for state='{state}'.")
        series = pd.to_numeric(subset[col], errors="coerce").dropna()
        if series.empty:
            raise SystemExit(f"[error] No numeric values for state='{state}' and month '{iso_key}'.")
        agg = (aggregate or "mean").lower()
        if   agg == "mean":   return float(series.mean())
        elif agg == "median": return float(series.median())
        elif agg == "max":    return float(series.max())
        elif agg == "min":    return float(series.min())
        else:
            raise SystemExit("Unsupported aggregate. Use: mean, median, max, min.")


def main():
    ap = argparse.ArgumentParser(description="Query ZORI (city CSV) by city/state and year-month.")
    ap.add_argument("--csv", type=Path, default=Path("data/raw/zori_city.csv"),
                    help="Path to the downloaded city-level CSV.")
    ap.add_argument("--city", type=str, default=None,
                    help="City name (e.g., 'Pittsburgh'). If omitted, aggregates by state.")
    ap.add_argument("--state", type=str, required=True,
                    help="Two-letter state code (e.g., PA, CA, TX).")
    ap.add_argument("--ym", type=str, required=False,
                    help="Year-month like 2024-07. If omitted with --list-dates, only lists.")
    ap.add_argument("--aggregate", type=str, default="mean",
                    help="For state-only queries: mean|median|min|max (default: mean).")
    ap.add_argument("--verbose", action="store_true",
                    help="Print context info instead of just the number.")
    ap.add_argument("--list-dates", dest="list_dates", action="store_true",
                    help="List all month columns detected in the CSV (ISO format).")
    args = ap.parse_args()

    df = load_city_csv(args.csv)
    date_map = build_date_index(df.columns)

    if args.list_dates:
        dates = sorted(date_map.keys())
        print(", ".join(dates))
        sys.exit(0)

    if not args.ym:
        raise SystemExit("[error] --ym is required unless you use --list-dates.")

    value = query_value(df, args.city, args.state, args.ym, args.aggregate, date_map)

    if args.verbose:
        who = f"City='{args.city}', State='{args.state}'" if args.city else f"State='{args.state}', agg='{args.aggregate}'"
        print(f"{who}, YM='{args.ym}' → {value}")
    else:
        print(value)


if __name__ == "__main__":
    main()
