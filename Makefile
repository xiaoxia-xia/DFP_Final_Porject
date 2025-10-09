PY=python3
VENV=.venv
PIP=$(VENV)/bin/pip
PYBIN=$(VENV)/bin/python

.DEFAULT_GOAL := help

help:
	@echo "Targets:"
	@echo "  venv               - create venv & install deps"
	@echo "  data-zillow        - build data/rent_data.csv"
	@echo "  data-crime         - build data/crime_data.csv   (requires FBI_API_KEY)"
	@echo "  data-salary        - scrape + fan-out salary CSVs"
	@echo "  data-all           - run all data steps"
	@echo "  main               - run the app (interactive or with CLI flags)"

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@$(PYBIN) -m playwright install

data-zillow: venv
	@$(PYBIN) src/pipelines/zillow_to_rent_data.py

data-crime: venv
	@[ -n "$$FBI_API_KEY" ] || (echo "FBI_API_KEY not set"; exit 1)
	@$(PYBIN) src/pipelines/fbi_crime_pipeline.py

data-salary: venv
	@echo "If first time, run: .venv/bin/python src/scrapers/login_levels.py"
	@$(PYBIN) src/scrapers/scrape_levels.py
	@$(PYBIN) src/pipelines/salary_adapter.py

data-all: data-zillow data-crime data-salary
	@echo "✓ All data ready"

main: venv
	@$(PYBIN) urbanLens_team_main.py
