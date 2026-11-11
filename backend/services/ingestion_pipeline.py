
from pathlib import Path
from datetime import datetime
import pandas as pd

from backend.services.excel_reader import read_ticket_file
from backend.services.schema_discovery import discover_schema
from backend.services.ticket_normalizer import normalize_tickets


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def process_ticket_file(file_path, sheet_name=None, save=True):
    """
    Complete Tyzo ingestion workflow:

    1. Read Excel or CSV.
    2. Discover source schema.
    3. Validate ticket ID mapping.
    4. Normalize tickets.
    5. Optionally save normalized dataset.
    """

    file_path = Path(file_path)

    print("\n========== TYZO INGESTION PIPELINE ==========")

    # STEP 1: Read source file
    print("\n[1/4] Reading source dataset...")

    df, metadata = read_ticket_file(
        file_path,
        sheet_name=sheet_name
    )

    print("File:", metadata["file_name"])
    print("Rows:", metadata["total_rows"])
    print("Columns:", metadata["total_columns"])

    # STEP 2: Discover schema
    print("\n[2/4] Discovering ticket schema...")

    schema = discover_schema(df)

    for field, source in schema["mapping"].items():
        if source is not None:
            print(f"{field} <- {source}")

    if not schema["is_valid"]:
        raise ValueError(
            "Ticket ID could not be identified. "
            "Please review the source columns."
        )

    # STEP 3: Normalize tickets
    print("\n[3/4] Normalizing ticket records...")

    normalized = normalize_tickets(
        df,
        schema
    )

    # STEP 4: Save processed dataset
    output_file = None

    if save:

        PROCESSED_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_file = (
            PROCESSED_DIR /
            f"{file_path.stem}_tyzo_{timestamp}.csv"
        )

        normalized.to_csv(
            output_file,
            index=False
        )

        print("\n[4/4] Dataset saved successfully.")
        print("Output:", output_file)

    else:

        print("\n[4/4] Saving skipped.")

    # Final report
    report = {
        "file_name": metadata["file_name"],
        "total_records": len(normalized),
        "valid_records": int(normalized["record_valid"].sum()),
        "invalid_records": int((~normalized["record_valid"]).sum()),
        "duplicate_records": int(
            normalized["duplicate_ticket_id"].sum()
        ),
        "schema_mapping": schema["mapping"],
        "missing_essential_fields": schema["missing_essential_fields"],
        "output_file": str(output_file) if output_file else None
    }

    print("\n========== TYZO INGESTION REPORT ==========")

    print("Total records:", report["total_records"])
    print("Valid records:", report["valid_records"])
    print("Invalid records:", report["invalid_records"])
    print("Duplicate records:", report["duplicate_records"])

    print("\nTYZO INGESTION COMPLETED")

    return normalized, report


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m backend.services.ingestion_pipeline "
            "<file_path> [sheet_name]"
        )
        sys.exit(1)

    source_file = Path(sys.argv[1])

    selected_sheet = (
        sys.argv[2] if len(sys.argv) > 2 else None
    )

    process_ticket_file(
        source_file,
        sheet_name=selected_sheet
    )
