import subprocess
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNTHEA_JAR  = PROJECT_ROOT / "data" / "synthea-with-dependencies.jar"
OUTPUT_DIR   = PROJECT_ROOT / "data" / "synthea_output"

# ── Config ─────────────────────────────────────────────────────────────────────
PATIENT_COUNT = 1000
RANDOM_SEED   = 42
STATE         = "Massachusetts"

def generate():
    if not SYNTHEA_JAR.exists():
        print(f"[ERROR] Synthea JAR not found at: {SYNTHEA_JAR}")
        print("Download it from: https://github.com/synthetichealth/synthea/releases/latest")
        print("Place it at: data/synthea_with_dependencies.jar")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        "java", "-jar", str(SYNTHEA_JAR),
        "-p", str(PATIENT_COUNT),
        "-s", str(RANDOM_SEED),
        f"--exporter.csv.export=true",
        f"--exporter.fhir.export=false",
        f"--exporter.ccda.export=false",
        f"--exporter.text.export=false",
        f"--exporter.baseDirectory={OUTPUT_DIR}",
        STATE,
    ]

    print(f"[INFO] Generating {PATIENT_COUNT} patients (seed={RANDOM_SEED}, state={STATE})")
    print(f"[INFO] Output directory: {OUTPUT_DIR}")

    result = subprocess.run(command, capture_output=False, text=True)

    if result.returncode != 0:
        print("[ERROR] Synthea exited with an error. Check output above.")
        sys.exit(1)

    csv_dir = OUTPUT_DIR / "csv"
    if csv_dir.exists():
        files = list(csv_dir.glob("*.csv"))
        print(f"\n[DONE] {len(files)} CSV files generated in {csv_dir}")
        for f in sorted(files):
            row_count = sum(1 for _ in open(f)) - 1  # subtract header
            print(f"       {f.name:<35} {row_count:>6} rows")
    else:
        print("[WARN] CSV output folder not found — check Synthea flags.")

if __name__ == "__main__":
    generate()