from __future__ import annotations

import streamlit as st

from .exports import build_csv_export, build_excel_export, build_word_export, export_column_labels, safe_export_name

def render_exports(case_name: str, rows: list[dict]) -> None:
    st.subheader("Exports")
    st.markdown(
        '<div class="section-note">Choose exactly which rows and columns should leave the workspace. Word is for a reviewed report; Excel/CSV are for working tables.</div>',
        unsafe_allow_html=True,
    )
    export_rows = render_export_row_selector(rows)
    selected_columns = render_export_column_selector()

    csv_col, excel_col, word_col = st.columns(3)
    with csv_col:
        st.download_button(
            "Download CSV",
            data=build_csv_export(export_rows, selected_columns),
            file_name=safe_export_name(case_name, "csv"),
            mime="text/csv",
            width="stretch",
        )
    with excel_col:
        st.download_button(
            "Download Excel",
            data=build_excel_export(export_rows, selected_columns),
            file_name=safe_export_name(case_name, "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with word_col:
        st.download_button(
            "Download Word chronology",
            data=build_word_export(case_name, export_rows, selected_columns),
            file_name=safe_export_name(case_name, "docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )


def render_export_row_selector(rows: list[dict]) -> list[dict]:
    export_mode = st.radio(
        "Rows to export",
        options=["Approved only", "All except rejected", "Selected rows"],
        index=1,
        horizontal=True,
        help="Use approved-only for final work product; selected rows is useful for custom reports.",
    )
    default_rows = filter_export_rows(rows, export_mode)
    if export_mode != "Selected rows":
        st.caption(f"{len(default_rows)} row(s) selected for export.")
        return default_rows

    selectable_rows = [row for row in rows if row["review_status"] != "Rejected"]
    row_options = {
        export_row_label(row): row.get("event_number", row.get("id"))
        for row in selectable_rows
    }
    selected_labels = st.multiselect(
        "Select event rows",
        options=list(row_options),
        default=list(row_options),
        help="Rejected rows are hidden from this picker.",
    )
    selected_numbers = {row_options[label] for label in selected_labels}
    selected_rows = [
        row
        for row in selectable_rows
        if row.get("event_number", row.get("id")) in selected_numbers
    ]
    st.caption(f"{len(selected_rows)} row(s) selected for export.")
    return selected_rows


def render_export_column_selector() -> list[str]:
    label_by_key = export_column_labels()
    default_columns = [
        "event_number",
        "date",
        "provider",
        "category",
        "summary",
        "source_citation",
        "gap_flag",
        "review_status",
    ]
    selected_labels = st.multiselect(
        "Columns to export",
        options=list(label_by_key.values()),
        default=[label_by_key[column] for column in default_columns],
        help="Applies to CSV, Excel, and the main Word chronology table.",
    )
    key_by_label = {label: key for key, label in label_by_key.items()}
    selected_columns = [key_by_label[label] for label in selected_labels]
    if not selected_columns:
        st.warning("Select at least one export column.")
        return default_columns
    return selected_columns


def export_row_label(row: dict) -> str:
    summary = row.get("summary", "")
    if len(summary) > 80:
        summary = f"{summary[:77]}..."
    return f"Event {row.get('event_number', row.get('id'))} | {row.get('date', '')} | {summary}"


def filter_export_rows(rows: list[dict], export_mode: str) -> list[dict]:
    if export_mode == "Approved only":
        return [row for row in rows if row["review_status"] == "Approved"]
    return [row for row in rows if row["review_status"] != "Rejected"]


