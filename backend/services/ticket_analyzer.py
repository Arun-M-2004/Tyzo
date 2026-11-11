
import re
import pandas as pd


def clean_text(value):
    """Convert missing values into safe empty strings."""

    if pd.isna(value):
        return ""

    return str(value).strip()


def extract_labeled_section(text, labels):
    """Extract information following a known work-note label."""

    if not text:
        return None

    for label in labels:

        pattern = (
            rf"{re.escape(label)}\s*:\s*(.*?)(?="
            rf"\n\s*(?:Issue|Action Taken|Actions taken|"
            rf"Action taken|Next action|Actions to be taken|"
            rf"Action to be taken|Resolution)\s*:|$)"
        )

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            value = match.group(1).strip()

            if value:
                return value

    return None


def identify_category(description, work_notes):
    """Identify an initial problem category using text evidence."""

    text = f"{description} {work_notes}".lower()

    categories = {
        "Network / Connectivity": [
            "network", "connectivity", "connection",
            "vpn", "internet", "dns"
        ],
        "Access / Authentication": [
            "access", "login", "authentication",
            "permission", "password", "account"
        ],
        "Application / Software": [
            "application", "software", "excel",
            "client", "installation", "addin"
        ],
        "Performance / Resource": [
            "performance", "slow", "cpu", "ram",
            "memory", "high usage"
        ],
        "Monitoring / Alerts": [
            "alert", "notification", "threshold",
            "cpu_util", "monitoring"
        ],
        "Database": [
            "database", "sql", "query", "db connection"
        ],
        "Data / Reporting": [
            "incorrect records", "data mismatch",
            "report", "records are displaying"
        ]
    }

    matched = []

    for category, keywords in categories.items():

        if any(keyword in text for keyword in keywords):
            matched.append(category)

    if not matched:
        return "Unclassified"

    return matched[0]


def identify_recommended_action(work_notes, status):
    """Identify the next action without claiming it is completed."""

    text = work_notes.lower()

    if any(term in text for term in [
        "awaiting response",
        "waiting for response",
        "pending response"
    ]):
        return "Follow up with the responsible team for an update."

    if any(term in text for term in [
        "escalated",
        "escalating",
        "assigned to l2",
        "assigning it to l2"
    ]):
        return "Track the escalation and obtain an update from the assigned support team."

    if any(term in text for term in [
        "uninstall",
        "reinstall",
        "configuration",
        "configure"
    ]):
        return "Review the documented configuration or installation steps and verify the outcome."

    if status.lower() in ["closed", "resolved"]:
        return "Review the documented resolution and verify closure evidence."

    if not work_notes:
        return "Review the ticket details and collect missing troubleshooting information."

    return "Review the latest work notes and identify the next required troubleshooting step."


def identify_possible_solution(description, work_notes, category):
    """
    Suggest a potential investigation direction.

    This is not an actual resolution.
    """

    text = f"{description} {work_notes}".lower()

    if "pi datalink" in text or "pi client" in text:
        return "Investigate PI Client installation, DataLink add-in registration and server connectivity."

    if "cpu" in text or "ram" in text or "memory" in text:
        return "Investigate resource utilization, running processes and infrastructure capacity."

    if "404" in text:
        return "Investigate the requested endpoint, application availability and service routing."

    if "access" in text or "login" in text:
        return "Investigate user permissions, account status and authentication configuration."

    if category == "Network / Connectivity":
        return "Investigate network connectivity, DNS and relevant endpoint availability."

    return "Review historical tickets and technical documentation for a verified solution."


def analyze_ticket(ticket):
    """Generate intelligence for one individual ticket."""

    ticket_id = clean_text(ticket.get("ticket_id"))

    description = clean_text(
        ticket.get("description")
    )

    work_notes = clean_text(
        ticket.get("work_notes")
    )

    status = clean_text(
        ticket.get("status")
    )

    priority = clean_text(
        ticket.get("priority")
    )

    age = ticket.get("age_days")

    category = identify_category(
        description,
        work_notes
    )

    documented_issue = extract_labeled_section(
        work_notes,
        ["Issue"]
    )

    documented_action = extract_labeled_section(
        work_notes,
        ["Action Taken", "Actions taken", "Action taken"]
    )

    documented_next_action = extract_labeled_section(
        work_notes,
        ["Next action", "Actions to be taken", "Action to be taken"]
    )

    # Do not invent actual resolutions.
    actual_resolution = ticket.get("resolution")

    if pd.isna(actual_resolution) or not clean_text(actual_resolution):
        actual_resolution = None

    # Build summary using source evidence.
    summary = (
        description
        if description
        else documented_issue
        if documented_issue
        else "Insufficient information to summarize this ticket."
    )

    recommended_action = identify_recommended_action(
        work_notes,
        status
    )

    if documented_next_action:
        recommended_action = documented_next_action

    possible_solution = identify_possible_solution(
        description,
        work_notes,
        category
    )

    # Record evidence and basic confidence.
    evidence = []

    if description:
        evidence.append("Source ticket description")

    if work_notes:
        evidence.append("Documented work notes")

    if documented_action:
        evidence.append("Extracted action taken")

    if documented_issue:
        evidence.append("Extracted documented issue")

    confidence = (
        "High" if description and work_notes
        else "Medium" if description or work_notes
        else "Low"
    )

    return {
        "ticket_id": ticket_id,
        "ticket_summary": summary,
        "problem_category": category,
        "status": status or None,
        "priority": priority or None,
        "age_days": age,
        "documented_issue": documented_issue,
        "documented_action_taken": documented_action,
        "recommended_action": recommended_action,
        "possible_solution": possible_solution,
        "actual_resolution": actual_resolution,
        "evidence": evidence,
        "confidence": confidence
    }


def analyze_tickets(df):
    """Generate one intelligence record for every input row."""

    if df is None or df.empty:
        raise ValueError("No tickets available for analysis.")

    required = {"ticket_id", "description", "work_notes"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required canonical columns: {missing}"
        )

    analyses = [
        analyze_ticket(row)
        for row in df.to_dict(orient="records")
    ]

    result = pd.DataFrame(analyses)

    if len(result) != len(df):
        raise RuntimeError(
            "Analysis record count does not match input ticket count."
        )

    return result



if __name__ == "__main__":

    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parents[2]
    PROCESSED_DIR = BASE_DIR / "data" / "processed"

    # Find the latest normalized ticket dataset
    files = list(
        PROCESSED_DIR.glob(
            "Aging Tickets-2 Jun (2)_tyzo_*.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            "No normalized ticket dataset found."
        )

    input_file = max(
        files,
        key=lambda path: path.stat().st_mtime
    )

    print("\n========== TYZO BATCH INTELLIGENCE ==========")
    print("Input:", input_file.name)

    # Load normalized tickets
    tickets = pd.read_csv(input_file)

    print("Tickets loaded:", len(tickets))

    # Analyze every ticket independently
    analyses = analyze_tickets(tickets)

    # Verify record count
    assert len(analyses) == len(tickets), (
        "Analysis count does not match ticket count!"
    )

    # Generate output file
    output_file = (
        PROCESSED_DIR /
        f"ticket_analysis_{pd.Timestamp.now():%Y%m%d_%H%M%S}.csv"
    )

    analyses.to_csv(
        output_file,
        index=False
    )

    print("\n========== ANALYSIS REPORT ==========")

    print("Input tickets:", len(tickets))
    print("Analysis records:", len(analyses))
    print("Unique ticket IDs:", analyses["ticket_id"].nunique())
    print(
        "Missing summaries:",
        analyses["ticket_summary"].isna().sum()
    )

    print("\nCATEGORY DISTRIBUTION:")
    print(
        analyses["problem_category"]
        .value_counts()
        .to_string()
    )

    print("\nCONFIDENCE DISTRIBUTION:")
    print(
        analyses["confidence"]
        .value_counts()
        .to_string()
    )

    print("\nSaved:", output_file)
    print("\nTYZO BATCH ANALYSIS COMPLETED")
