.PHONY: all ingest build export experiment clean
all: ingest build export experiment

ingest:                 ## load raw CSV -> DuckDB raw layer
	python src/ingest.py

build:                  ## dbt: run models + tests (transform layer)
	cd dbt && DBT_PROFILES_DIR=. dbt build

export:                 ## write Tableau-ready CSVs from the marts
	python src/export_for_tableau.py

experiment:             ## size + simulate the recommender A/B test
	python src/experiment.py

clean:
	rm -f data/warehouse/*.duckdb
