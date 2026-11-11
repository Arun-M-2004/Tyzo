
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = BASE_DIR / "data" / "database"
DATABASE_PATH = DATABASE_DIR / "tyzo.db"


def get_connection():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Stores information about every uploaded dataset.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                total_tickets INTEGER DEFAULT 0,
                uploaded_at TEXT NOT NULL
            )
        """)

        # Stores individual ticket analysis.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                ticket_id TEXT,
                ticket_summary TEXT,
                problem_category TEXT,
                status TEXT,
                priority TEXT,
                age_days REAL,
                documented_issue TEXT,
                documented_action_taken TEXT,
                recommended_action TEXT,
                possible_solution TEXT,
                actual_resolution TEXT,
                evidence TEXT,
                confidence TEXT,
                full_analysis TEXT,

                FOREIGN KEY (dataset_id)
                REFERENCES datasets(id),

                UNIQUE(dataset_id, ticket_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_id
            ON tickets(ticket_id)
        """)

        connection.commit()

        print("Tyzo database initialized successfully.")

    finally:
        connection.close()



def save_dataset(original_filename, analysis_df):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO datasets (
                dataset_name,
                original_filename,
                total_tickets,
                uploaded_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            original_filename,
            original_filename,
            len(analysis_df),
            datetime.now(timezone.utc).isoformat()
        ))

        dataset_id = cursor.lastrowid

        def clean_value(value):
            if value is None:
                return None

            try:
                if value != value:
                    return None
            except (TypeError, ValueError):
                pass

            if hasattr(value, "item"):
                value = value.item()

            if isinstance(value, (list, dict, tuple, set)):
                return json.dumps(value, default=str)

            return value

        # Save every ticket into SQLite.
        for _, row in analysis_df.iterrows():

            record = {
                key: clean_value(value)
                for key, value in row.to_dict().items()
            }

            cursor.execute("""
                INSERT INTO tickets (
                    dataset_id,
                    ticket_id,
                    ticket_summary,
                    problem_category,
                    status,
                    priority,
                    age_days,
                    documented_issue,
                    documented_action_taken,
                    recommended_action,
                    possible_solution,
                    actual_resolution,
                    evidence,
                    confidence,
                    full_analysis
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id,
                str(record.get("ticket_id", "")),
                record.get("ticket_summary"),
                record.get("problem_category"),
                record.get("status"),
                record.get("priority"),
                record.get("age_days"),
                record.get("documented_issue"),
                record.get("documented_action_taken"),
                record.get("recommended_action"),
                record.get("possible_solution"),
                record.get("actual_resolution"),
                record.get("evidence"),
                record.get("confidence"),
                json.dumps(record, default=str)
            ))

        connection.commit()

        print(
            f"Successfully saved dataset {dataset_id} "
            f"with {len(analysis_df)} tickets."
        )

        return dataset_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
