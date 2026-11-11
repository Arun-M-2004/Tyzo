
from pathlib import Path
import pandas as pd


# Project directory
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def clean_ticket_dump(file_name, sheet_name, snapshot_date):

    file_path = RAW_DIR / file_name

    print("\nTYZO - TICKET CLEANING")
    print("Reading:", file_name)

    # 1. Read original Excel data
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name
    )

    original_count = len(df)

    # 2. Standardize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # 3. Rename source fields into standard names
    df = df.rename(columns={
        "number": "ticket_id",
        "opened": "opened_date",
        "closed": "closed_date",
        "short_description": "description",
        "state": "status",
        "assigned_to": "assigned_person"
    })

    # 4. Clean ticket IDs
    df["ticket_id"] = (
        df["ticket_id"]
        .astype("string")
        .str.strip()
    )

    # 5. Convert date columns
    for column in [
        "opened_date",
        "closed_date",
        "created",
        "updated"
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce"
            )

    # 6. Normalize text fields
    for column in [
        "status",
        "priority",
        "assigned_person",
        "description"
    ]:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    # 7. Remove invalid ticket IDs
    df = df.dropna(subset=["ticket_id"])

    df = df[df["ticket_id"] != ""]

    # 8. Remove duplicate tickets
    df = df.drop_duplicates(
        subset=["ticket_id"],
        keep="last"
    )

    # 9. Calculate ticket ageing
    snapshot = pd.Timestamp(snapshot_date)

    df["age_days"] = (
        snapshot - df["opened_date"]
    ).dt.days

    # 10. Identify invalid ageing values
    df["age_valid"] = df["age_days"].notna() & (
        df["age_days"] >= 0
    )

    # 11. Categorize ticket ageing
    def get_age_group(age):

        if pd.isna(age) or age < 0:
            return "Invalid / Unknown"

        elif age <= 20:
            return "0-20 Days"

        elif age <= 30:
            return "21-30 Days"

        elif age <= 40:
            return "31-40 Days"

        elif age <= 50:
            return "41-50 Days"

        elif age <= 60:
            return "51-60 Days"

        else:
            return "Above 60 Days"

    df["age_group"] = df["age_days"].apply(
        get_age_group
    )

    # 12. Add enrichment fields
    # These must be supplied or verified later.
    for column in [
        "tower",
        "tower_lead",
        "dependency",
        "current_status",
        "eta",
        "challenges_concerns"
    ]:
        if column not in df.columns:
            df[column] = pd.NA

    # 13. Add snapshot information
    df["snapshot_date"] = snapshot

    # 14. Generate cleaning report
    print("\nCLEANING REPORT")
    print("-----------------------")

    print("Original rows:", original_count)
    print("Cleaned rows:", len(df))
    print(
        "Duplicates / invalid IDs removed:",
        original_count - len(df)
    )

    print(
        "\nAge group distribution:"
    )

    print(df["age_group"].value_counts().to_string())

    print(
        "\nMissing ticket IDs:",
        df["ticket_id"].isna().sum()
    )

    print(
        "Invalid opening dates:",
        df["opened_date"].isna().sum()
    )

    # 15. Export cleaned data
    output_file = (
    PROCESSED_DIR / f"tickets_cleaned_{snapshot_date}.csv"
)

    df.to_csv(
        output_file,
        index=False
    )

    print("\nSaved successfully:")
    print(output_file)

    return df


if __name__ == "__main__":

    # Historical snapshot
    clean_ticket_dump(
        file_name="Aging Tickets-2 Jun (2).xlsx",
        sheet_name="Ticket Dump",
        snapshot_date="2025-06-02"
    )

    # Latest snapshot
    clean_ticket_dump(
        file_name="Incident Aging - 5 Jun (1).xlsx",
        sheet_name="Page 1",
        snapshot_date="2025-06-05"
    )