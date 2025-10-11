import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import re

ROLES = {
    "Web Developer": ("https://www.levels.fyi/t/software-engineer/title/web-developer?country=254", "web_developer_salary.csv"),
    "Machine Learning Engineer": ("https://www.levels.fyi/t/software-engineer/title/machine-learning-engineer?country=254", "machine_learning_engineer_salary.csv"),
    "Data Engineer": ("https://www.levels.fyi/t/software-engineer/title/data-engineer?country=254", "data_engineer_salary.csv"),
    "AI Engineer": ("https://www.levels.fyi/t/software-engineer/title/ai-engineer?country=254", "ai_engineer_salary.csv"),
    "Full-Stack Software Engineer": ("https://www.levels.fyi/t/software-engineer/title/full-stack-software-engineer?country=254", "full_stack_software_engineer_salary.csv"),
    "Analytics Product Manager": ("https://www.levels.fyi/t/product-manager/focus/analytic?countryId=254&country=254", "analytics_product_manager_salary.csv"),
}


# ========== ① Scraping Function ==========
async def scrape_levels(url_base):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Can be changed to True for headless mode
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()

        all_data = []
        limit = 50
        max_pages = 7

        for page_idx in range(max_pages):
            offset = page_idx * limit
            print(f"\n📄 Scraping page {page_idx+1} -> offset={offset}")
            url = f"{url_base}&limit={limit}&offset={offset}"
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("tbody.MuiTableBody-root", timeout=60000)

            # Scroll to load lazy-loaded content
            for _ in range(5):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(400)

            rows = page.locator("tbody.MuiTableBody-root tr")
            row_count = await rows.count()
            if row_count == 1:
                raise RuntimeError("Too many requests recently — has been blocked by levels.fyi. Wait ~5 minutes and retry.")


            print(f"  ✅ Found {row_count} rows on the current page")

            for i in range(row_count):
                cols = await rows.nth(i).locator("td").all_inner_texts()
                all_data.append(cols)

        await browser.close()
        df = pd.DataFrame(all_data)
        print(f"\n✅ Scraped a total of {len(df)} rows of data.")
        return df


# ========== ② Cleaning and Aggregation Function ==========
def clean_and_aggregate(raw_df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in raw_df.iterrows():
        # --- ① Extract City ---
        raw_text = str(row[0])
        parts = raw_text.split("\n", 1)
        city_part = parts[1] if len(parts) > 1 else parts[0]
        city_match = re.search(r"([A-Za-z\s\.-]+,\s*[A-Z]{2})", city_part)
        city = city_match.group(1).strip() if city_match else ""

        # --- ② Extract Salary ---
        salary_text = str(row[3])
        salary_match = re.search(r"\$[\d,]+", salary_text)
        if salary_match:
            salary_str = salary_match.group(0).replace("$", "").replace(",", "")
            try:
                salary = float(salary_str)
            except ValueError:
                salary = None
        else:
            salary = None

        if city and salary:
            results.append([city, salary])

    df_clean = pd.DataFrame(results, columns=["City", "Salary"])

    # ✅ Remove rows with "hidden" or empty cities
    df_clean = df_clean[~df_clean["City"].str.contains("hidden", case=False, na=False)]
    df_clean = df_clean[df_clean["City"].str.strip() != ""]

    # ✅ Remove cities that start with "Ad" (advertisements)
    df_clean = df_clean[~df_clean["City"].str.startswith("Ad", na=False)]

    # ✅ Calculate the average salary by city
    df_avg = df_clean.groupby("City", as_index=False)["Salary"].mean()
    df_avg.rename(columns={"Salary": "Avg_Salary"}, inplace=True)

    # ✅ Sort by average salary in descending order (optional)
    df_avg = df_avg.sort_values("Avg_Salary", ascending=False).reset_index(drop=True)

    return df_avg


# ========== ③ Main Program Entry Point ==========
async def scrape_levels_main(choice):
    (url, output_name) = ROLES[choice]
    print("🚀 Starting" + choice + "to scrape data from Levels.fyi...")
    df_raw = await scrape_levels(url)
    print("\n🧹 Starting to clean and aggregate the data...")
    df_final = clean_and_aggregate(df_raw)
    print(f"✅ Aggregation complete. Found data for {len(df_final)} cities.")
    output = f"data/{output_name}"
    df_final.to_csv(output, index=False, encoding="utf-8-sig")
    print("\n🎉 Saved as" + output_name)
    print(df_final.head(10))


if __name__ == "__main__":
    asyncio.run(scrape_levels_main("Web Developer"))