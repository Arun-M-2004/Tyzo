
from pathlib import Path
import pandas as pd


# Tyzo project paths
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


# Convert ticket IDs into a consistent format
def normalize_ticket_id(series):

    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.upper()
    )


def enrich_tickets():

    print("\n========== TYZO TICKET ENRICHMENT ==========\n")

    # 1. Read cleaned original dump
    original_file = (
        PROCESSED_DIR / "tickets_cleaned_2025-06-05.csv"
    )

    original = pd.read_csv(original_file)

    # 2. Read your manually enriched tracker
    tracker_file = (
        RAW_DIR / "Incident Aging - 5 Jun_1 (1).xlsx"
    )

    tracker = pd.read_excel(
        tracker_file,
        sheet_name="Page 1"
    )

    print("Original tickets:", len(original))
    print("Tracker records:", len(tracker))

    # 3. Standardize ticket ID column names
    tracker = tracker.rename(columns={
        "Number": "ticket_id"
    })

    # 4. Normalize IDs in both datasets
    original["ticket_id"] = normalize_ticket_id(
        original["ticket_id"]
    )

    tracker["ticket_id"] = normalize_ticket_id(
        tracker["ticket_id"]
    )

    # 5. Identify duplicate tracker records
    duplicate_count = tracker["ticket_id"].duplicated().sum()

    print("Duplicate tracker IDs:", duplicate_count)

    tracker = tracker.drop_duplicates(
        subset=["ticket_id"],
        keep="last"
    )

    # 6. Select enrichment fields
    enrichment_columns = {
        "Configuration item": "configuration_item",
        "On hold reason": "on_hold_reason",
        "current date": "tracker_current_date",
        "age": "tracker_age",
        "age group": "tracker_age_group",
        "Tower": "tower",
        "Tower Lead": "tower_lead",
        "Dependency": "dependency",
        "Current Status": "current_status",
        "ETA": "eta",
        "Challenges/Concerns": "challenges_concerns",
        "Assigned to": "tracker_assigned_to",
        "Updated": "tracker_updated",
        "Updated by": "tracker_updated_by",
        "Work notes": "tracker_work_notes"
    }

    # 7. Rename tracker columns
    tracker = tracker.rename(
        columns=enrichment_columns
    )

    selected_columns = [
        "ticket_id",
        *enrichment_columns.values()
    ]

    tracker = tracker[selected_columns]

    # 8. Merge using ticket ID
    merged = original.merge(
        tracker,
        on="ticket_id",
        how="left",
        indicator=True
    )

    # 9. Check matching results
    matched = (merged["_merge"] == "both").sum()

    unmatched = (merged["_merge"] == "left_only").sum()

    tracker_only = len(
        set(tracker["ticket_id"])
        - set(original["ticket_id"])
    )

    print("\n========== MERGE REPORT ==========")

    print("Original tickets:", len(original))
    print("Matched tickets:", matched)
    print("Unmatched original tickets:", unmatched)
    print("Tracker-only tickets:", tracker_only)

    # 10. Identify records without enrichment
    merged["enrichment_status"] = merged["_merge"].map({
        "both": "Matched",
        "left_only": "Needs enrichment",
        "right_only": "Tracker only"
    })

    merged = merged.drop(columns=["_merge"])

    # 11. Save unified dataset
    output_file = (
        PROCESSED_DIR / "tyzo_enriched_tickets.csv"
    )

    merged.to_csv(
        output_file,
        index=False
    )

    print("\nEnriched dataset saved:")
    print(output_file)

    return merged


if __name__ == "__main__":

    enrich_tickets()
