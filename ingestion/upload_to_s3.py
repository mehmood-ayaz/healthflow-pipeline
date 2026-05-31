import boto3
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import sys

# ── Config ─────────────────────────────────────────────────────────────────────
load_dotenv()

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME        = os.getenv("S3_BUCKET_NAME")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_DIR      = PROJECT_ROOT / "data" / "synthea_output" / "csv"

# Only the files we care about — ignore allergies, careplans etc.
TARGET_FILES = [
    "patients.csv",
    "encounters.csv",
    "conditions.csv",
    "medications.csv",
    "procedures.csv",
    "observations.csv",
    "providers.csv",
    "organizations.csv",
    "payers.csv",
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def validate_env():
    missing = [k for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET_NAME"]
               if not os.getenv(k)]
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("        Check your .env file.")
        sys.exit(1)

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

def add_ingestion_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Add a metadata column so we know exactly when this batch was ingested."""
    df["ingestion_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return df

def build_s3_key(filename: str, ingestion_date: str) -> str:
    """
    Builds the S3 path for a given file.
    
    Pattern: raw/{entity}/{entity}_{date}.csv
    Example: raw/patients/patients_20240101.csv
    
    Why partition by date? If you run this pipeline daily with new data,
    each run creates a new file rather than overwriting — giving you 
    a full history of ingestion batches.
    """
    entity = filename.replace(".csv", "")
    return f"raw/{entity}/{entity}_{ingestion_date}.csv"

def upload_file(s3_client, local_path: Path, s3_key: str) -> dict:
    """Upload a single file, return a result dict for logging."""
    try:
        df = pd.read_csv(local_path, low_memory=False)
        original_rows = len(df)

        df = add_ingestion_timestamp(df)

        # Write to an in-memory buffer rather than a temp file on disk
        csv_buffer = df.to_csv(index=False).encode("utf-8")

        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=csv_buffer,
            ContentType="text/csv",
        )

        return {
            "file": local_path.name,
            "s3_key": s3_key,
            "rows": original_rows,
            "status": "success",
        }

    except Exception as e:
        return {
            "file": local_path.name,
            "s3_key": s3_key,
            "rows": 0,
            "status": f"FAILED: {e}",
        }

# ── Main ───────────────────────────────────────────────────────────────────────
def upload():
    validate_env()

    if not CSV_DIR.exists():
        print(f"[ERROR] CSV directory not found: {CSV_DIR}")
        print("        Run ingestion/generate_data.py first.")
        sys.exit(1)

    s3_client = get_s3_client()
    ingestion_date = datetime.now(timezone.utc).strftime("%Y%m%d")

    print(f"[INFO] Starting upload to s3://{S3_BUCKET_NAME}/raw/")
    print(f"[INFO] Ingestion date partition: {ingestion_date}\n")

    results = []
    for filename in TARGET_FILES:
        local_path = CSV_DIR / filename

        if not local_path.exists():
            print(f"[SKIP] {filename} not found in CSV output — skipping.")
            continue

        s3_key = build_s3_key(filename, ingestion_date)
        print(f"[UPLOAD] {filename:<35} → {s3_key}")
        result = upload_file(s3_client, local_path, s3_key)
        results.append(result)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n── Upload Summary ─────────────────────────────────────────────────")
    success = [r for r in results if r["status"] == "success"]
    failed  = [r for r in results if r["status"] != "success"]

    for r in results:
        status_symbol = "✓" if r["status"] == "success" else "✗"
        print(f"  {status_symbol} {r['file']:<35} {r['rows']:>7} rows   {r['status']}")

    print(f"\n  {len(success)}/{len(results)} files uploaded successfully.")

    if failed:
        print("\n[ERROR] The following files failed:")
        for r in failed:
            print(f"  - {r['file']}: {r['status']}")
        sys.exit(1)
    else:
        print(f"[DONE] All files uploaded to s3://{S3_BUCKET_NAME}/raw/")

if __name__ == "__main__":
    upload()