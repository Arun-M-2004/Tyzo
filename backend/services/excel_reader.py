
from pathlib import Path
import pandas as pd


# Project paths
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def read_ticket_file(file_path, sheet_name=None):
    """
    Read an Excel or CSV ticket dataset.

    Returns:
        df: Original dataset as a Pandas DataFrame
        metadata: Information about the uploaded file

    Does not rename or modify source columns.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    # CSV ingestion
    if extension == ".csv":

        encodings = [
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin1"
        ]

        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding
                )
                break

            except UnicodeDecodeError:
                continue

        if df is None:
            raise ValueError(
                "Unable to decode CSV file."
            )

        metadata = {
            "file_name": file_path.name,
            "file_type": "CSV",
            "sheet_name": None,
            "available_sheets": [],
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist()
        }

    # Excel ingestion
    else:

        excel = pd.ExcelFile(file_path)

        available_sheets = excel.sheet_names

        if not available_sheets:
            raise ValueError(
                "Excel file contains no worksheets."
            )

        selected_sheet = (
            sheet_name
            if sheet_name is not None
            else available_sheets[0]
        )

        if selected_sheet not in available_sheets:
            raise ValueError(
                f"Sheet '{selected_sheet}' not found. "
                f"Available sheets: {available_sheets}"
            )

        df = pd.read_excel(
            excel,
            sheet_name=selected_sheet
        )

        metadata = {
            "file_name": file_path.name,
            "file_type": "EXCEL",
            "sheet_name": selected_sheet,
            "available_sheets": available_sheets,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": df.columns.tolist()
        }

    if df.empty:
        raise ValueError(
            "The selected dataset contains no records."
        )

    return df, metadata


def inspect_excel_files():

    print("\n========== TYZO UNIVERSAL FILE INSPECTION ==========\n")

    if not RAW_DATA_DIR.exists():
        print("Raw data directory not found!")
        return

    files = [
        file for file in RAW_DATA_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        print("No supported files found!")
        return

    for file_path in files:

        print("\n-----------------------------------")
        print(f"FILE: {file_path.name}")
        print("-----------------------------------")

        try:

            if file_path.suffix.lower() in {".xlsx", ".xlsm"}:

                excel = pd.ExcelFile(file_path)

                print("Sheets:", excel.sheet_names)

                for sheet in excel.sheet_names:

                    df, metadata = read_ticket_file(
                        file_path,
                        sheet_name=sheet
                    )

                    print(f"\nSheet: {sheet}")
                    print("Rows:", metadata["total_rows"])
                    print("Columns:", metadata["total_columns"])
                    print("Column names:", metadata["columns"])

            else:

                df, metadata = read_ticket_file(file_path)

                print("\nFormat:", metadata["file_type"])
                print("Rows:", metadata["total_rows"])
                print("Columns:", metadata["total_columns"])
                print("Column names:", metadata["columns"])

        except Exception as error:

            print("Error:", error)


if __name__ == "__main__":
    inspect_excel_files()
