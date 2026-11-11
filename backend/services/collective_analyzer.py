
import re
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def distribution_report(df, column):
    """Generate count and percentage distribution."""

    if column not in df.columns:
        return pd.DataFrame()

    values = (
    df[column]
    .astype("string")
    .fillna("Unknown")
    .str.strip()
    )

    report = values.value_counts().rename_axis(column).reset_index(name="ticket_count")
    report["percentage"] = (
        report["ticket_count"] / len(df) * 100
    ).round(2)

    return report


def aging_report(df):
    """Group tickets into age bands."""

    if "age_days" not in df.columns:
        return pd.DataFrame()

    ages = pd.to_numeric(df["age_days"], errors="coerce")

    conditions = [
        ages < 7,
        (ages >= 7) & (ages < 15),
        (ages >= 15) & (ages < 30),
        (ages >= 30) & (ages < 60),
        ages >= 60,
    ]

    labels = [
        "0-6 days",
        "7-14 days",
        "15-29 days",
        "30-59 days",
        "60+ days",
    ]

    df = df.copy()
    df["aging_band"] = pd.Series(
        pd.NA, index=df.index, dtype="object"
    )

    for condition, label in zip(conditions, labels):
        df.loc[condition, "aging_band"] = label

    df["aging_band"] = df["aging_band"].fillna("Unknown")

    return distribution_report(df, "aging_band")



def find_recurring_patterns(df, similarity_threshold=0.35):
    """
    Find pairs of tickets with similar summaries.
    Each ticket remains an independent record.
    """

    if "ticket_id" not in df.columns:
        return pd.DataFrame()

    # Individual analysis output uses ticket_summary.
    # Normalized input may use description.
    text_column = (
        "ticket_summary"
        if "ticket_summary" in df.columns
        else "description"
    )

    if text_column not in df.columns:
        return pd.DataFrame()

    working = df[["ticket_id", text_column]].copy()

    working[text_column] = (
        working[text_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    working = working[
        working[text_column].str.len() > 0
    ].reset_index(drop=True)

    if len(working) < 2:
        return pd.DataFrame()

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000
    )

    try:
        matrix = vectorizer.fit_transform(working[text_column])
    except ValueError:
        return pd.DataFrame()

    similarity_matrix = cosine_similarity(matrix)

    matches = []

    for i in range(len(working)):
        for j in range(i + 1, len(working)):

            score = similarity_matrix[i, j]

            if score >= similarity_threshold:
                matches.append({
                    "ticket_id_1": working.loc[i, "ticket_id"],
                    "ticket_id_2": working.loc[j, "ticket_id"],
                    "similarity_score": round(float(score), 3),
                    "summary_1": working.loc[i, text_column],
                    "summary_2": working.loc[j, text_column],
                })

    return pd.DataFrame(matches)


def team_report(df):
    """Analyze assigned team workload when available."""

    if "assigned_team" not in df.columns:
        return pd.DataFrame()

    return distribution_report(df, "assigned_team")


def analyze_collective(df):
    """Run all collective intelligence analyses."""

    if "ticket_id" not in df.columns:
        raise ValueError("Dataset must contain ticket_id.")

    results = {
        "category": distribution_report(df, "problem_category"),
        "status": distribution_report(df, "status"),
        "priority": distribution_report(df, "priority"),
        "aging": aging_report(df),
        "team": team_report(df),
        "recurring_patterns": find_recurring_patterns(df),
    }

    return results


def save_collective_reports(results, output_dir):
    """Save each report as a separate CSV."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for report_name, report_df in results.items():

        output_file = output_dir / f"{report_name}_report.csv"

        report_df.to_csv(
            output_file,
            index=False
        )

        print(
            f"Saved {report_name}: "
            f"{len(report_df)} records"
        )


if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parents[2]
    PROCESSED_DIR = BASE_DIR / "data" / "processed"

    analysis_files = list(
        PROCESSED_DIR.glob("ticket_analysis_*.csv")
    )

    if not analysis_files:
        raise FileNotFoundError(
            "No individual ticket analysis file found."
        )

    input_file = max(
        analysis_files,
        key=lambda path: path.stat().st_mtime
    )

    print("\n========== TYZO COLLECTIVE INTELLIGENCE ==========")
    print("Input:", input_file.name)

    tickets = pd.read_csv(input_file)

    print("Tickets loaded:", len(tickets))

    results = analyze_collective(tickets)

    output_dir = (
        PROCESSED_DIR /
        f"collective_{pd.Timestamp.now():%Y%m%d_%H%M%S}"
    )

    save_collective_reports(results, output_dir)

    print("\n========== COLLECTIVE ANALYSIS SUMMARY ==========")

    print("\nCATEGORY DISTRIBUTION:")
    print(results["category"].to_string(index=False))

    print("\nAGING DISTRIBUTION:")
    print(results["aging"].to_string(index=False))

    print("\nRECURRING TICKET PAIRS:")
    print("Similar pairs found:", len(results["recurring_patterns"]))

    print("\nOutput folder:", output_dir)
    print("\nTYZO COLLECTIVE ANALYSIS COMPLETED")
