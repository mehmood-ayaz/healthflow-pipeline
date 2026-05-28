# HealthFlow Pipeline

Personal analytics project using Synthea → S3 → Snowflake → dbt.

## Structure
- `ingestion/` — Python scripts for data generation and loading
- `dbt/` — dbt models for transformation
- `airflow/` — Orchestration DAGs
- `docs/` — Documentation and data dictionary

## Prerequisites
- Java 17+ installed
- Download `synthea_with_dependencies.jar` from https://github.com/synthetichealth/synthea/releases/latest
- Place it at `data/synthea_with_dependencies.jar`
- Then run: `python ingestion/generate_data.py`