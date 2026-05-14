from __future__ import annotations

import csv
import re
from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
from docx import Document

def build_csv_export(rows: list[dict], columns: list[str] | None = None) -> bytes:
    columns = columns or export_columns()
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[export_column_labels()[column] for column in columns])
    writer.writeheader()
    for row in rows:
        writer.writerow({export_column_labels()[column]: format_export_value(row, column) for column in columns})
    return output.getvalue().encode("utf-8")


def build_excel_export(rows: list[dict], columns: list[str] | None = None) -> bytes:
    columns = columns or export_columns()
    output = BytesIO()
    export_frame = pd.DataFrame(
        [
            {export_column_labels()[column]: format_export_value(row, column) for column in columns}
            for row in rows
        ]
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_frame.to_excel(writer, index=False, sheet_name="Chronology")
    return output.getvalue()


def build_word_export(case_name: str, rows: list[dict], columns: list[str] | None = None) -> bytes:
    columns = columns or [
        "event_number",
        "date",
        "provider",
        "category",
        "summary",
        "source_citation",
        "gap_flag",
        "review_status",
    ]
    document = Document()
    approved_rows = [row for row in rows if row.get("review_status") == "Approved"]
    report_rows = approved_rows if approved_rows else rows
    generated_on = datetime.now().strftime("%B %d, %Y")

    document.add_heading(case_name, level=1)
    document.add_paragraph("Medical Chronology Review Report")
    document.add_paragraph(f"Generated: {generated_on}")
    document.add_paragraph("Draft work product. Verify all source citations before final use.")

    stats = document.add_paragraph()
    stats.add_run("Summary: ").bold = True
    stats.add_run(
        f"{len(rows)} extracted events; "
        f"{sum(1 for row in rows if row.get('review_status') == 'Approved')} approved; "
        f"{sum(1 for row in rows if row.get('review_status') == 'Needs review')} needs review; "
        f"{sum(1 for row in rows if 'day gap' in row.get('gap_flag', ''))} treatment gaps; "
        f"{sum(1 for row in rows if row.get('duplicate_flag'))} possible duplicate rows."
    )

    if approved_rows:
        document.add_paragraph("The table below includes approved chronology rows.")
    else:
        document.add_paragraph("No rows are approved yet, so this draft includes all non-rejected rows from the selected export set.")

    table = document.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    for index, column in enumerate(columns):
        table.rows[0].cells[index].text = export_column_labels()[column]

    for row in report_rows:
        cells = table.add_row().cells
        for index, column in enumerate(columns):
            cells[index].text = format_export_value(row, column)

    gap_rows = [row for row in rows if "day gap" in row.get("gap_flag", "")]
    if gap_rows:
        document.add_heading("Treatment Gap Notes", level=2)
        for row in gap_rows:
            document.add_paragraph(
                f"{row.get('date', '')}: {row.get('gap_flag', '')} before this event. "
                f"Source: {row.get('document', '')}, p. {row.get('page', '')}.",
                style="List Bullet",
            )

    duplicate_rows = [row for row in rows if row.get("duplicate_flag")]
    if duplicate_rows:
        document.add_heading("Possible Duplicate Notes", level=2)
        for row in duplicate_rows:
            document.add_paragraph(
                f"Event {row.get('event_number', '')} marked {row.get('duplicate_flag', '')} "
                f"in group {row.get('duplicate_group', '')}. {row.get('duplicate_note', '')}",
                style="List Bullet",
            )

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def export_columns() -> list[str]:
    return list(export_column_labels())


def export_column_labels() -> dict[str, str]:
    return {
        "event_number": "Event #",
        "date": "Date",
        "date_precision_note": "Date precision",
        "date_meaning": "Date meaning",
        "provider": "Provider / facility",
        "provider_note": "Provider status",
        "category": "Category",
        "summary": "Event summary",
        "source_citation": "Source citation",
        "document": "Document",
        "page": "Page",
        "extraction_method": "Source type",
        "source_snippet": "Source snippet",
        "confidence": "Confidence",
        "importance": "Importance",
        "gap_flag": "Treatment gap",
        "duplicate_flag": "Duplicate flag",
        "duplicate_group": "Duplicate group",
        "duplicate_note": "Duplicate reason",
        "review_status": "Review status",
    }


def format_export_value(row: dict, column: str) -> str:
    if column == "source_citation":
        return f"{row.get('document', '')}, p. {row.get('page', '')}"
    return str(row.get(column, ""))


def safe_export_name(case_name: str, extension: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", case_name).strip("_") or "chronology"
    return f"{safe_name}_medical_chronology.{extension}"


