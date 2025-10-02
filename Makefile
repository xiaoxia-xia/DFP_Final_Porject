# Add 'all' to thePHONY list and make it the default target
.PHONY: all venv install download

VENV?=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

# 'all' is the first target, so it's the default.
# Running 'make' will now be the same as 'make all'.
all: install download

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

download:
	$(PY) src/data/download_zillow.py --out data/raw/zori_city.csv