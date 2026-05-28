.PHONY: generate upload dbt-run

generate:
python ingestion/generate_data.py

upload:
python ingestion/upload_to_s3.py
python ingestion/load_to_snowflake.py

dbt-run:
cd dbt/healthflow && dbt run
