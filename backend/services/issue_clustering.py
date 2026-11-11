
import re
import pandas as pd


ENVIRONMENT_LABELS = {
    "PROD": "PRODUCTION",
    "PRODUCTION": "PRODUCTION",
    "TEST": "TEST",
    "DEV": "DEVELOPMENT",
    "DEVELOPMENT": "DEVELOPMENT",
    "UAT": "UAT",
    "QA": "QA",
    "STAGE": "STAGING",
    "STAGING": "STAGING",
}

REGION_LABELS = {
    "EUROPE",
    "ASIA",
    "ASIAPAC",
    "ASIA_PAC",
    "ASIA_PACIFIC",
    "NORTH",
    "NORTH2",
    "AMERICAS",
    "AMERICA",
    "GLOBAL",
}

MODULE_SUFFIXES = {
    "WEB",
    "ADMIN",
}


def extract_application_identity(summary):
    """
    Extract application, environment and region
    from structured ticket summaries.

    Unstructured summaries remain UNKNOWN.
    """

    unknown = {
        "application_name": "UNKNOWN",
        "application_key": "UNKNOWN",
        "environment": "UNKNOWN",
        "region": "UNKNOWN",
        "identity_confidence": "LOW",
    }

    if pd.isna(summary):
        return unknown.copy()

    text = str(summary).strip()

    if not text:
        return unknown.copy()

    # Monitoring-style summaries:
    # Issue detected for: ["ASSAICLOUD_NORTH2_PROD_Web"]
    monitoring_match = re.search(
        r"Issue(?:\(s\))?\s+detected\s+for\s*:\s*"
        r"\[?\s*[\"']([^\"']+)[\"']",
        text,
        flags=re.IGNORECASE,
    )

    if monitoring_match:
        prefix = monitoring_match.group(1).strip()

    else:
        # Only use prefixes from structured summaries.
        if not re.search(r":|\|\|", text):
            return unknown.copy()

        parts = re.split(
            r"\s*(?::|\|\|)\s*",
            text,
            maxsplit=1
        )

        prefix = parts[0].strip()

    prefix = prefix.strip(" []\"'")

    if len(prefix) < 3:
        return unknown.copy()

    # Normalize separators.
    normalized = re.sub(
        r"[\s\-]+",
        "_",
        prefix.upper()
    )

    tokens = [
        token
        for token in normalized.split("_")
        if token
    ]

    environment = "UNKNOWN"
    region = "UNKNOWN"

    # Detect environment anywhere in the identifier.
    for token in tokens:
        if token in ENVIRONMENT_LABELS:
            environment = ENVIRONMENT_LABELS[token]
            break

    # Detect region.
    for token in tokens:
        if token in REGION_LABELS:
            region = token
            break

    # Remove environment, region and module suffixes.
    application_tokens = [
        token
        for token in tokens
        if token not in ENVIRONMENT_LABELS
        and token not in REGION_LABELS
        and token not in MODULE_SUFFIXES
    ]

    application_key = "_".join(application_tokens)

    if not application_key:
        return unknown.copy()

    return {
        "application_name": prefix,
        "application_key": application_key,
        "environment": environment,
        "region": region,
        "identity_confidence": "MEDIUM",
    }


def add_application_identity(df):
    """
    Add application identity fields to the ticket dataset.
    Original ticket columns remain unchanged.
    """

    if "ticket_summary" not in df.columns:
        raise ValueError(
            "ticket_summary column is required."
        )

    result = df.copy()

    identities = result["ticket_summary"].apply(
        extract_application_identity
    )

    identity_df = pd.DataFrame(
        identities.tolist(),
        index=result.index
    )

    for column in identity_df.columns:
        result[column] = identity_df[column]

    return result
