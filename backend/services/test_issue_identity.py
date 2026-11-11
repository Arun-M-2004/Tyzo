
def extract_application_identity(summary):
    """
    Extract application, environment and region from structured
    ticket summaries. Unstructured summaries remain UNKNOWN.
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

    # Detect monitoring-style application identifiers.
    monitoring_match = re.search(
        r"Issue(?:\(s\))?\s+detected\s+for\s*:\s*"
        r"\[?\s*[\"']([^\"']+)[\"']",
        text,
        flags=re.IGNORECASE,
    )

    if monitoring_match:
        prefix = monitoring_match.group(1).strip()

    else:
        # Only trust a prefix when the summary has a structured
        # separator. Avoid guessing from free-form descriptions.
        if not re.search(r":|\|\|", text):
            return unknown.copy()

        parts = re.split(r"\s*(?::|\|\|)\s*", text, maxsplit=1)
        prefix = parts[0].strip()

    prefix = prefix.strip(" []\"'")

    if len(prefix) < 3:
        return unknown.copy()

    # Normalize hyphens and spaces for token analysis.
    normalized = re.sub(r"[\s\-]+", "_", prefix.upper())
    tokens = [token for token in normalized.split("_") if token]

    environment = "UNKNOWN"
    region = "UNKNOWN"

    # Environment can appear before or after a module suffix.
    for token in tokens:
        if token in ENVIRONMENT_LABELS:
            environment = ENVIRONMENT_LABELS[token]
            break

    # Identify region labels.
    for token in tokens:
        if token in REGION_LABELS:
            region = token
            break

    # Remove environment, region and common module suffixes
    # from the application identity.
    module_suffixes = {"WEB", "ADMIN"}

    application_tokens = [
        token for token in tokens
        if token not in ENVIRONMENT_LABELS
        and token not in REGION_LABELS
        and token not in module_suffixes
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
