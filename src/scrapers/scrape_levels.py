
#!/usr/bin/env python3
import asyncio
import argparse
from playwright.async_api import async_playwright
import pandas as pd
import re
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUT = DATA_DIR / "software-devops-junior-avg-salary.csv"

LIST_URL_TMPL = (
    "https://www.levels.fyi/t/software-engineer/focus/devops"
    "?countryId=254&limit={limit}&offset={offset}&yoeChoice=junior"
)

def pick_auth_path(user_arg: str | None) -> str:
    if user_arg:
        return user_arg
    # prefer src/scrapers/auth.json; fall back to data/auth.json or ./auth.json
    p0 = Path("src/scrapers/auth.json")
    p1 = Path("data/auth.json")
    p2 = Path("auth.json")
    if p0.exists():
        return str(p0)
    if p1.exists():
        return str(p1)
    if p2.exists():
        return str(p2)
    # default to src/scrapers/auth.json even if it doesn't exist (unauthenticated context)
    return str(p0)

async def scrape_levels(storage_state_path: str, headless: bool) -> pd.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(storage_state=storage_state_path if Path(storage_state_path).exists() else None)
        page = await context.new_page()

        all_data = []
        limit = 50
        max_pages = 7

        for page_idx in range(max_pages):
            offset = page_idx * limit
            url = LIST_URL_TMPL.format(limit=limit, offset=offset)
            print(f"\nScraping page {page_idx+1} -> offset={offset}")
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("tbody.MuiTableBody-root", timeout=60000)

            for _ in range(5):
                await page.mouse.wheel(0, 1400)
                await page.wait_for_timeout(350)

            rows = page.locator("tbody.MuiTableBody-root tr")
            row_count = await rows.count()
            print(f"  Found {row_count} rows on the current page")

            for i in range(row_count):
                cols = await rows.nth(i).locator("td").all_inner_texts()
                all_data.append(cols)

        await browser.close()
        df = pd.DataFrame(all_data)
        print(f"Scraped a total of {len(df)} rows of data.")
        return df

CITY_RE = re.compile(r"([A-Za-z\s\.-]+,\s*[A-Z]{2})")
MONEY_RE = re.compile(r"\$[\d,]+")

def clean_and_aggregate(raw_df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in raw_df.iterrows():
        raw_text = str(row.iloc[0]) if len(row) > 0 else ""
        parts = raw_text.split("\n", 1)
        city_part = parts[1] if len(parts) > 1 else parts[0]
        m_city = CITY_RE.search(city_part)
        city = m_city.group(1).strip() if m_city else ""

        salary_text = str(row.iloc[3]) if len(row) > 3 else ""
        m_sal = MONEY_RE.search(salary_text)
        if m_sal:
            try:
                salary = float(m_sal.group(0).replace("$", "").replace(",", ""))
            except ValueError:
                salary = None
        else:
            salary = None

        if city and salary:
            results.append([city, salary])

    df_clean = pd.DataFrame(results, columns=["City", "Salary"])
    df_clean = df_clean[~df_clean["City"].str.contains("hidden", case=False, na=False)]
    df_clean = df_clean[df_clean["City"].str.strip() != ""]
    df_clean = df_clean[~df_clean["City"].str.startswith("Ad", na=False)]

    df_avg = df_clean.groupby("City", as_index=False)["Salary"].mean()
    df_avg.rename(columns={"Salary": "Avg_Salary"}, inplace=True)
    df_avg = df_avg.sort_values("Avg_Salary", ascending=False).reset_index(drop=True)
    return df_avg

async def run(auth_arg: str | None, headless: bool, out_path: Path):
    storage_state = pick_auth_path(auth_arg)
    print(f"Using storage_state: {storage_state if Path(storage_state).exists() else '(none)'}")
    df_raw = await scrape_levels(storage_state, headless=headless)
    print("Cleaning and aggregating...")
    df_final = clean_and_aggregate(df_raw)
    print(f"Aggregation complete. Found data for {len(df_final)} cities.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved -> {out_path}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", type=str, default=None, help="Path to Playwright storage_state JSON (default: src/scrapers/auth.json)")
    ap.add_argument("--show", action="store_true", help="Run headless=False to watch the scrape")
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="Output CSV path")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(auth_arg=args.auth, headless=not args.show, out_path=Path(args.out)))
