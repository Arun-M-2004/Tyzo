
import re
import pandas as pd


# Canonical fields and their recognized alternatives
FIELD_ALIASES = {
    "ticket_id": [
        "ticket id", "ticket number", "number",
        "incident number", "incident id",
        "case id", "case number", "request id",
        "record id", "task number"
    ],

    "status": [
        "status", "state", "ticket status",
        "incident status", "resolution status"
    ],

    "age_days": [
        "age", "age days", "age in days",
        "aging", "ageing", "ticket age",
        "days open", "open days"
    ],

    "assigned_team": [
        "assigned team", "assignment group",
        "assigned group", "support group",
        "resolver group", "team", "group"
    ],

    "priority": [
        "priority", "ticket priority",
        "incident priority", "urgency level"
    ],

    "description": [
        "description", "short description",
        "problem description", "issue description",
        "summary", "subject", "title"
    ],

    "opened_date": [
        "opened", "opened date", "created date",
        "creation date", "created", "reported date"
    ],

    "closed_date": [
        "closed", "closed date", "resolved date",
        "resolution date"
    ],

    "assigned_person": [
        "assigned to", "assignee",
        "assigned person", "owner",
        "technician", "agent"
    ],

    "work_notes": [
        "work notes", "comments",
        "resolution notes", "technical notes",
        "activity notes"
    ],

    "resolution": [
        "resolution", "resolution description",
        "actual resolution", "fix details",
        "solution notes"
    ]
}


# Normalize column names for matching
def normalize_column_name(column):

    value = str(column).strip().lower()

    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", "", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def discover_schema(df):

    if df is None or df.empty:
        raise ValueError("Dataset is empty.")

    source_columns = list(df.columns)

    normalized_columns = {
        column: normalize_column_name(column)
        for column in source_columns
    }

    mapping = {}
    confidence = {}
    unmatched = []

    for canonical_field, aliases in FIELD_ALIASES.items():

        normalized_aliases = [
            normalize_column_name(alias)
            for alias in aliases
        ]

        candidates = []

        for original_column, normalized_column in normalized_columns.items():

            if normalized_column in normalized_aliases:

                candidates.append(original_column)

        if len(candidates) == 1:

            mapping[canonical_field] = candidates[0]
            confidence[canonical_field] = "high"

        elif len(candidates) > 1:

            mapping[canonical_field] = None
            confidence[canonical_field] = "ambiguous"

        else:

            mapping[canonical_field] = None
            confidence[canonical_field] = "missing"

    for column in source_columns:

        matched = any(
            mapping[field] == column
            for field in mapping
        )

        if not matched:
            unmatched.append(column)

    essential_fields = [
        "ticket_id",
        "status",
        "age_days"
    ]

    missing_essential = [
        field for field in essential_fields
        if mapping[field] is None
    ]

    return {
        "mapping": mapping,
        "confidence": confidence,
        "unmatched_columns": unmatched,
        "missing_essential_fields": missing_essential,
        "is_valid": mapping["ticket_id"] is not None,
        "source_columns": source_columns
    }


if __name__ == "__main__":

    sample = pd.DataFrame({
        "Number": ["INC1001"],
        "State": ["Open"],
        "Ageing": [25],
        "Assignment Group": ["Network Support"],
        "Priority": ["P2"],
        "Short Description": ["Network connection failure"]
    })

    result = discover_schema(sample)

    print("\n========== TYZO SCHEMA DISCOVERY ==========\n")

    print("COLUMN MAPPING:")

    for field, column in result["mapping"].items():
        print(f"{field}: {column}")

    print("\nCONFIDENCE:")

    for field, level in result["confidence"].items():
        print(f"{field}: {level}")

    print("\nMissing essential fields:")
    print(result["missing_essential_fields"])

    print("\nUnmatched columns:")
    print(result["unmatched_columns"])

    print("\nDataset valid:")
    print(result["is_valid"])
