
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


def compare_snapshots():

    print("\n========== TYZO SNAPSHOT COMPARISON ==========\n")

    old_file = PROCESSED_DIR / "tickets_cleaned_2025-06-02.csv"
    new_file = PROCESSED_DIR / "tickets_cleaned_2025-06-05.csv"

    old = pd.read_csv(old_file)
    new = pd.read_csv(new_file)

    # Normalize IDs
    old["ticket_id"] = old["ticket_id"].astype(str).str.strip().str.upper()
    new["ticket_id"] = new["ticket_id"].astype(str).str.strip().str.upper()

    # Remove duplicate IDs for safe comparison
    old = old.drop_duplicates(subset="ticket_id")
    new = new.drop_duplicates(subset="ticket_id")

    # Match old and new records
    merged = old.merge(
        new,
        on="ticket_id",
        how="outer",
        suffixes=("_old", "_new"),
        indicator=True
    )

    # Identify ticket additions and removals
    merged["change_type"] = merged["_merge"].map({
    "left_only": "Missing from latest dump - Verify",
    "right_only": "New ticket",
    "both": "Existing ticket"
}).astype("string")

    # Fields to compare when available in both snapshots
    fields_to_compare = [
        "status",
        "priority",
        "assigned_person",
        "description",
        "work_notes",
        "age_days"
    ]

    # Detect changes in existing tickets
    for field in fields_to_compare:

        old_column = f"{field}_old"
        new_column = f"{field}_new"

        if old_column in merged.columns and new_column in merged.columns:

            changed = (
                merged["_merge"].eq("both")
                & merged[old_column].fillna("").astype(str).ne(
                    merged[new_column].fillna("").astype(str)
                )
            )

            merged.loc[changed, "change_type"] = (
                merged.loc[changed, "change_type"]
                + f" | {field} changed"
            )

    # Generate summary
    summary = merged["change_type"].value_counts()

    print("PREVIOUS SNAPSHOT:", len(old))
    print("LATEST SNAPSHOT:", len(new))

    print("\nCHANGE SUMMARY:")
    print(summary.to_string())

    # Save comparison
    output_file = PROCESSED_DIR / "snapshot_changes.csv"

    merged.drop(columns=["_merge"]).to_csv(
        output_file,
        index=False
    )

    print("\nComparison saved:", output_file)

    return merged


if __name__ == "__main__":
    compare_snapshots()
