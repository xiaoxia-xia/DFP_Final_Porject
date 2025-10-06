## Quickstart: Setup and Data Download

To get started, you only need to run one command. This will create a local Python virtual environment, install the required packages, and download the initial ZORI dataset.

`make all`

Usage: Querying Rent Data
Once the setup is complete, you can use .venv by 

`source .venv/bin/activate` and

you can query the rent data for a specific city and date using the zori_query.py script.

The script requires a city, state abbreviation, and a year-month (YYYY-MM) to retrieve the rent index.

Example Query
Here is an example of how to query the Zillow Observed Rent Index for Pittsburgh, PA, for the month of July 2024.

`python src/query/zori_query.py --city "Pittsburgh" --state PA --ym 2024-07`

expected to have `$1513.41` as output




### Generate per-year averages + recent 12-month average

Creates a compact CSV with `avg_2024`, `avg_2025`, and a rolling `recent_12mo_avg`
computed from the most recent 12 monthly columns in the source file.

```bash
make avg-by-year
