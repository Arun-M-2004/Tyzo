
import pandas as pd

from backend.services.schema_discovery import discover_schema


CANONICAL_FIELDS = [
    "ticket_id",
    "status",
    "age_days",
    "assigned_team",
    "priority",
    "description",
    "opened_date",
    "closed_date",
    "assigned_person",
    "work_notes",
    "resolution"
]

GENERATED_FIELDS = [
    "source_row_number",
    "record_valid",
    "duplicate_ticket_id",
    "normalization_issue"
]


def normalize_ticket_id(value):

    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if not value:
        return pd.NA

    return (
        pd.Series([value])
        .str.replace(r"\.0$", "", regex=True)
        .iloc[0]
        .upper()
    )


def make_unique_source_columns(columns):

    reserved = {
        name.casefold()
        for name in CANONICAL_FIELDS + GENERATED_FIELDS
    }

    used = set(reserved)
    rename_map = {}

    for column in columns:

        original_name = str(column)
        candidate = original_name

        if candidate.casefold() in used:

            candidate = f"source__{original_name}"
            suffix = 2

            while candidate.casefold() in used:
                candidate = f"source__{original_name}_{suffix}"
                suffix += 1

        rename_map[column] = candidate
        used.add(candidate.casefold())

    return rename_map


def normalize_tickets(df, schema_result=None):

    if df is None or df.empty:
        raise ValueError("Cannot normalize an empty dataset.")

    if not df.columns.is_unique:
        raise ValueError(
            "Source dataset contains duplicate column names. "
            "Resolve duplicate source headers before normalization."
        )

    if schema_result is None:
        schema_result = discover_schema(df)

    if not schema_result["is_valid"]:
        raise ValueError(
            "Ticket ID mapping is missing or ambiguous."
        )

    mapping = schema_result["mapping"]

    # Preserve source data while avoiding canonical name conflicts
    result = df.copy()

    source_rename_map = make_unique_source_columns(
        result.columns
    )

    result = result.rename(
        columns=source_rename_map
    )

    # Preserve original source row numbers
    result["source_row_number"] = range(
        1,
        len(result) + 1
    )

    # Build canonical fields using original source data
    for canonical_field in CANONICAL_FIELDS:

        source_column = mapping.get(canonical_field)

        if source_column is not None:
            result[canonical_field] = df[source_column].copy()

        else:
            result[canonical_field] = pd.NA

    # Normalize ticket IDs
    result["ticket_id"] = (
        result["ticket_id"]
        .apply(normalize_ticket_id)
        .astype("string")
    )

    # Normalize text fields
    text_fields = [
        "status",
        "assigned_team",
        "priority",
        "description",
        "assigned_person",
        "work_notes",
        "resolution"
    ]

    for field in text_fields:

        result[field] = (
            result[field]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Normalize age
    result["age_days"] = pd.to_numeric(
        result["age_days"],
        errors="coerce"
    )

    # Normalize dates
    for field in ["opened_date", "closed_date"]:

        result[field] = pd.to_datetime(
            result[field],
            errors="coerce"
        )

    # Validate ticket IDs
    result["record_valid"] = (
        result["ticket_id"].notna()
        & result["ticket_id"].ne("")
    )

    # Flag duplicates without deleting records
    result["duplicate_ticket_id"] = (
        result["ticket_id"].notna()
        & result["ticket_id"].duplicated(keep=False)
    )

    result["normalization_issue"] = result.apply(
        lambda row: (
            "Missing ticket ID"
            if not row["record_valid"]
            else (
                "Duplicate ticket ID"
                if row["duplicate_ticket_id"]
                else pd.NA
            )
        ),
        axis=1
    )

    # Verify case-insensitive column uniqueness
    column_names = [str(c).casefold() for c in result.columns]

    if len(column_names) != len(set(column_names)):
        raise ValueError(
            "Normalization produced duplicate column names."
        )

    print("\n========== TYZO TICKET NORMALIZATION ==========")

    print("Original records:", len(df))
    print("Valid ticket records:", int(result["record_valid"].sum()))
    print("Invalid records:", int((~result["record_valid"]).sum()))
    print("Duplicate records:", int(result["duplicate_ticket_id"].sum()))
    print("Canonical fields:", len(CANONICAL_FIELDS))
    print("Total output columns:", len(result.columns))

    return result


if __name__ == "__main__":

    sample = pd.DataFrame({
        "Number": ["INC1001", "INC1002", "INC1003"],
        "State": ["Open", "In Progress", "Closed"],
        "Ageing": [25, 12, 45],
        "Assignment Group": [
            "Network Support",
            "Database Team",
            "Application Support"
        ],
        "Priority": ["P2", "P3", "P1"],
        "Short Description": [
            "Network connection failure",
            "Database performance issue",
            "Application unavailable"
        ],
        "Work notes": [
            "Checking network",
            "Database restart",
            "Service restored"
        ]
    })

    schema = discover_schema(sample)

    normalized = normalize_tickets(sample, schema)

    print("\nCANONICAL DATA:")
    print(
        normalized[
            CANONICAL_FIELDS
        ].to_string(index=False)
    )

    print("\nPRESERVED SOURCE COLUMNS:")
    print([
        column for column in normalized.columns
        if column.startswith("source__")
    ])
