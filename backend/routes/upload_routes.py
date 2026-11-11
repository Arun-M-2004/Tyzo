
from pathlib import Path
from uuid import uuid4

import pandas as pd
from flask import Blueprint, jsonify, request

from backend.services.ingestion_pipeline import process_ticket_file
from backend.services.ticket_analyzer import analyze_tickets
from backend.services.collective_analyzer import analyze_collective
from backend.services.database import save_dataset

upload_bp = Blueprint("upload", __name__)

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}


@upload_bp.route("/upload", methods=["POST"])
def upload_file():

    if "file" not in request.files:
        return jsonify({
            "error": "No file provided. Use the field name 'file'."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({"error": "Please select a file."}), 400

    extension = Path(uploaded_file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Unsupported file type.",
            "allowed_types": list(ALLOWED_EXTENSIONS)
        }), 400

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a safe server-side filename.
    saved_name = f"{uuid4().hex}{extension}"
    saved_path = RAW_DIR / saved_name

    uploaded_file.save(saved_path)

    try:
        sheet_name = request.form.get("sheet_name") or None

        # Step 1: Ingest and normalize.
        
        normalized, ingestion_report = process_ticket_file(
            saved_path,
            sheet_name=sheet_name,
            save=False
        )

        # Step 2: Analyze each ticket.
        individual = analyze_tickets(normalized)

# Step 3: Save dataset and ticket analysis into SQLite.
        dataset_id = save_dataset(
            original_filename=uploaded_file.filename,
            analysis_df=individual
        )

        # Step 4: Generate collective intelligence.
        collective = analyze_collective(individual)

        # Step 4: Save individual analysis.
        analysis_file = (
            PROCESSED_DIR /
            f"{saved_path.stem}_analysis.csv"
        )

        individual.to_csv(analysis_file, index=False)

        return jsonify({
            "success": True,
            "message": "Ticket dataset processed successfully.",
            "dataset": {
                "dataset_id": dataset_id,
                "original_filename": uploaded_file.filename,
                "total_tickets": len(individual),
                "analysis_records": len(individual),
                "analysis_file": analysis_file.name,
                "database_saved": True
            },
            "ingestion": ingestion_report,
            "category_distribution": (
                collective["category"].to_dict(orient="records")
            ),
            "status_distribution": (
                collective["status"].to_dict(orient="records")
            ),
            "priority_distribution": (
                collective["priority"].to_dict(orient="records")
            ),
            "aging_distribution": (
                collective["aging"].to_dict(orient="records")
            ),
            "team_distribution": (
                collective["team"].to_dict(orient="records")
            ),
            "recurring_pairs": len(
                collective["recurring_patterns"]
            )
        }), 200

    except Exception as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

