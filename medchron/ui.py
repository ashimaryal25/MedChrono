from __future__ import annotations

import pandas as pd
import streamlit as st

from .ingestion import extract_pages_from_pdf, parse_sample_pages, trim_pages_to_character_limit
from .models import PageText
from .pipeline import (
    add_duplicate_flags,
    classify_medical_category,
    extract_chronology_rows,
    friendly_date_context,
    friendly_date_precision,
    friendly_provider_source,
)
from .rules import CATEGORY_OPTIONS, SAMPLE_MEDICAL_RECORD
from .source_viewer import render_source_viewer
from .export_ui import render_exports

def main() -> None:
    st.set_page_config(page_title="MedChronology Workspace", layout="wide")
    inject_app_styles()
    render_app_header()
    render_support_notes()

    max_pages, max_chars, ocr_enabled = render_sidebar()
    case_name, pages = render_case_input(max_pages=max_pages, max_chars=max_chars, ocr_enabled=ocr_enabled)

    if not pages:
        st.markdown(
            '<div class="empty-state">Upload a medical-record PDF or keep the sample enabled to generate a cited chronology.</div>',
            unsafe_allow_html=True,
        )
        return

    render_generation_panel(case_name=case_name, pages=pages, max_chars=max_chars)

    if "chronology_rows" in st.session_state:
        render_chronology_workspace(st.session_state["case_name"], st.session_state["chronology_rows"])


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                linear-gradient(180deg, #f6f8fb 0%, #ffffff 38%),
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.09), transparent 30%);
            color: #172033;
        }
        .block-container {padding-top: 1.5rem; max-width: 1380px;}
        h1, h2, h3 {letter-spacing: 0;}
        .app-hero {
            background: linear-gradient(135deg, #102033 0%, #173b55 52%, #1e5b57 100%);
            color: #f8fafc;
            border-radius: 14px;
            padding: 28px 32px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 0 14px 36px rgba(15, 23, 42, 0.14);
        }
        .app-hero h1 {
            font-size: 2.4rem;
            line-height: 1.05;
            margin: 0 0 10px 0;
            color: #ffffff;
        }
        .app-hero p {
            max-width: 780px;
            margin: 0;
            color: #d9e7ef;
            font-size: 1.02rem;
        }
        .hero-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 18px;
        }
        .hero-badge {
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.22);
            color: #f8fafc;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.82rem;
        }
        .workflow-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 22px 0;
        }
        .workflow-step {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }
        .workflow-step strong {
            display: block;
            color: #0f2737;
            margin-bottom: 4px;
        }
        .workflow-step span {
            color: #64748b;
            font-size: 0.9rem;
        }
        .input-panel, .action-panel {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 12px;
            padding: 18px 20px;
            margin: 14px 0 18px 0;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }
        .intake-shell {
            background: #ffffff;
            border: 1px solid #d7e3f2;
            border-radius: 14px;
            padding: 22px;
            margin: 14px 0 18px 0;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
        }
        .source-card {
            background: #f8fbff;
            border: 1px solid #d7e3f2;
            border-radius: 12px;
            padding: 14px 16px;
            margin: 8px 0 12px 0;
        }
        .source-card strong {
            display: block;
            color: #0f2737;
            margin-bottom: 4px;
        }
        .source-card span {
            color: #64748b;
            font-size: 0.92rem;
        }
        .panel-heading {
            color: #0f2737;
            font-weight: 700;
            font-size: 1.05rem;
            margin-bottom: 2px;
        }
        .panel-copy {
            color: #64748b;
            margin-bottom: 12px;
            font-size: 0.92rem;
        }
        .intake-help {
            background: #f8fbff;
            border: 1px solid #d7e3f2;
            border-radius: 10px;
            color: #456174;
            padding: 11px 13px;
            margin: 10px 0 8px 0;
            font-size: 0.93rem;
        }
        .empty-state {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            border-radius: 10px;
            padding: 16px 18px;
            margin-top: 12px;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 12px;
            padding: 15px 16px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stMetric"] label {color: #475569;}
        .section-note {
            background: #f8fbff;
            border: 1px solid #d7e3f2;
            border-left: 4px solid #1e7a6d;
            border-radius: 10px;
            padding: 12px 14px;
            color: #334155;
            margin: 0.5rem 0 1rem 0;
        }
        .duplicate-card {
            background: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .source-review-card {
            background: #ffffff;
            border: 1px solid #d7e3f2;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
            margin-bottom: 12px;
        }
        .source-review-card strong {
            color: #0f2737;
        }
        .source-meta {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 12px;
        }
        .source-meta div {
            background: #f8fbff;
            border: 1px solid #e0e8f2;
            border-radius: 8px;
            padding: 8px 10px;
            color: #334155;
            font-size: 0.9rem;
        }
        .pdf-frame-wrap {
            border: 1px solid #cfd9e6;
            border-radius: 12px;
            overflow: hidden;
            background: #f8fafc;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        }
        .document-page-count {
            color: #64748b;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        div[data-testid="stImage"] img {
            border: 1px solid #d7e3f2;
            border-radius: 10px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
        }
        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }
        .stButton > button[kind="primary"] {
            background: #e24c4b;
            border-color: #e24c4b;
            border-radius: 9px;
            padding: 0.65rem 1.1rem;
            font-weight: 700;
        }
        .stButton > button[kind="primary"]:hover {
            background: #cf3d3c;
            border-color: #cf3d3c;
        }
        div[data-testid="stTextInput"] label,
        div[data-testid="stFileUploader"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stCheckbox"] label {
            color: #243447;
            font-weight: 650;
        }
        div[data-testid="stTextInput"] input {
            background: #ffffff;
            border: 1px solid #cfd9e6;
            border-radius: 10px;
            min-height: 48px;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
            font-size: 1rem;
        }
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextInput"] input:focus-visible {
            border-color: #1e7a6d;
            outline: none;
            box-shadow: 0 0 0 3px rgba(30, 122, 109, 0.14);
        }
        div[data-testid="stTextInput"] input:invalid {
            border-color: #cfd9e6;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="InputInstructions"] {
            display: none;
        }
        div[data-testid="stFileUploader"] section {
            background: #f8fbff;
            border: 1.5px dashed #9fb4cc;
            border-radius: 12px;
            min-height: 86px;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stFileUploader"] section:hover {
            border-color: #1e7a6d;
            background: #f5fffc;
        }
        div[data-testid="stFileUploader"] button {
            border-radius: 9px;
            border-color: #b8c5d4;
            background: #ffffff;
            color: #172033;
            font-weight: 650;
        }
        div[data-testid="stFileUploader"] small {
            color: #64748b;
        }
        div[data-testid="stTextArea"] textarea {
            background: #ffffff;
            border: 1px solid #cfd9e6;
            border-radius: 12px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            line-height: 1.55;
        }
        div[data-testid="stRadio"] {
            background: #f8fbff;
            border: 1px solid #d7e3f2;
            border-radius: 12px;
            padding: 12px 16px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            min-height: 86px;
        }
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #1e7a6d;
            box-shadow: 0 0 0 3px rgba(30, 122, 109, 0.14);
        }
        div[data-testid="stTabs"] button p {
            font-weight: 650;
        }
        @media (max-width: 900px) {
            .workflow-strip {grid-template-columns: 1fr;}
            .app-hero {padding: 22px 20px;}
            .app-hero h1 {font-size: 1.9rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <h1>MedChronology Workspace</h1>
            <p>Turn medical-record PDFs into a cited, editable chronology table for legal and claims review.</p>
            <div class="hero-badges">
                <span class="hero-badge">Source-cited rows</span>
                <span class="hero-badge">Duplicate review</span>
                <span class="hero-badge">Treatment gaps</span>
                <span class="hero-badge">Word + Excel export</span>
            </div>
        </div>
        <div class="workflow-strip">
            <div class="workflow-step"><strong>1. Upload</strong><span>PDF or sample record</span></div>
            <div class="workflow-step"><strong>2. Extract</strong><span>Dates, events, providers</span></div>
            <div class="workflow-step"><strong>3. Review</strong><span>Edit, approve, merge duplicates</span></div>
            <div class="workflow-step"><strong>4. Export</strong><span>Word report or Excel table</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[int, int, bool]:
    st.sidebar.header("Processing")
    max_pages = st.sidebar.slider("PDF page limit", min_value=1, max_value=200, value=50)
    max_chars = st.sidebar.slider(
        "Text character limit",
        min_value=10_000,
        max_value=500_000,
        value=150_000,
        step=10_000,
    )
    ocr_enabled = st.sidebar.checkbox(
        "Try OCR for scanned pages",
        value=True,
        help="Requires Tesseract and Poppler installed on the machine.",
    )
    st.sidebar.divider()
    st.sidebar.markdown("**MVP focus**")
    st.sidebar.markdown("Cited medical chronology, human review, Word/Excel export.")
    return max_pages, max_chars, ocr_enabled


def render_support_notes() -> None:
    with st.expander("What this prototype supports", expanded=False):
        st.markdown(
            """
- **Date precision:** labels dates as exact date, month only, or year only.
- **Multiple sources:** supports multiple PDFs, pasted text, or a mixed PDF-plus-text record set.
- **Source citations:** every extracted row keeps document name, page number, source snippet, and text source.
- **PDF source viewer:** source verification opens only the document tied to the selected event and highlights the extracted source when it can be located.
- **Provider inference:** providers found in nearby sentences are marked as `nearby context` and should be verified.
- **Legal-review categories:** events are grouped into practical chronology categories like injury, diagnosis, imaging, therapy, work status, MMI, prior history, missed appointments, and administrative records.
- **Treatment-period language:** phrases like `through March 24, 2023` are treated as treatment-period endpoints, not treatment gaps.
- **Treatment gaps:** flags 30+ day gaps only between point-in-time events.
- **Review workflow:** AI-drafted rows start as `Needs review`; users can approve or reject before export.
- **Exports:** CSV, Excel, and Word chronology exports are available.
- **OCR:** text PDFs work directly; scanned PDFs need Tesseract and Poppler installed.
            """
        )


def render_case_input(max_pages: int, max_chars: int, ocr_enabled: bool) -> tuple[str, list[PageText]]:
    st.session_state["pdf_sources"] = {}
    st.markdown(
        """
        <div class="intake-shell">
            <div class="panel-heading">Case Intake</div>
            <div class="panel-copy">Name the matter, then choose the record source for this chronology run.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    case_col, source_col, spacer_col = st.columns([0.38, 0.36, 0.26])
    with case_col:
        case_name = st.text_input(
            "Matter name",
            value="Sample Workers' Comp Matter",
            placeholder="e.g., Lopez v. Acme Warehouse",
        )
    with source_col:
        source_type = st.radio(
            "Record source",
            options=["Sample record", "Upload PDFs", "Paste text", "Mixed sources"],
            horizontal=True,
            label_visibility="visible",
        )
    with spacer_col:
        st.empty()

    if source_type == "Upload PDFs":
        upload_col, _ = st.columns([0.58, 0.42])
        with upload_col:
            st.markdown(
                '<div class="source-card"><strong>Upload medical-record PDFs</strong><span>Use this for record packets split across multiple PDF files. Source verification will open only the PDF tied to the selected row.</span></div>',
                unsafe_allow_html=True,
            )
            uploaded_pdfs = st.file_uploader(
                "Medical-record PDFs",
                type=["pdf"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )
        if not uploaded_pdfs:
            return case_name, []

        pages = extract_pages_from_uploaded_pdfs(uploaded_pdfs, max_pages=max_pages, ocr_enabled=ocr_enabled)
        show_loaded_sources_summary(pages, max_chars)
        return case_name, trim_pages_to_character_limit(pages, max_chars)

    if source_type == "Paste text":
        paste_col, _ = st.columns([0.62, 0.38])
        with paste_col:
            st.markdown(
                '<div class="source-card"><strong>Paste medical-record text</strong><span>Use this when you already copied text out of records or want to test specific date/event language.</span></div>',
                unsafe_allow_html=True,
            )
            pasted_text = st.text_area("Paste medical-record text", height=260)
        return case_name, parse_sample_pages(pasted_text, document_name="Pasted Text") if pasted_text.strip() else []

    if source_type == "Mixed sources":
        mixed_col, _ = st.columns([0.66, 0.34])
        with mixed_col:
            st.markdown(
                '<div class="source-card"><strong>Combine PDFs and pasted text</strong><span>Use this when a case has PDFs plus notes, letters, copied chart text, or a narrative report pasted from another source.</span></div>',
                unsafe_allow_html=True,
            )
            uploaded_pdfs = st.file_uploader(
                "PDF documents",
                type=["pdf"],
                accept_multiple_files=True,
            )
            text_document_name = st.text_input("Pasted text document name", value="Pasted Notes")
            pasted_text = st.text_area("Optional pasted text document", height=220)

        pages: list[PageText] = []
        if uploaded_pdfs:
            pages.extend(extract_pages_from_uploaded_pdfs(uploaded_pdfs, max_pages=max_pages, ocr_enabled=ocr_enabled))
        if pasted_text.strip():
            pages.extend(parse_sample_pages(pasted_text, document_name=text_document_name.strip() or "Pasted Notes"))
        if not pages:
            return case_name, []
        show_loaded_sources_summary(pages, max_chars)
        return case_name, trim_pages_to_character_limit(pages, max_chars)

    sample_col, _ = st.columns([0.62, 0.38])
    with sample_col:
        st.markdown(
            '<div class="source-card"><strong>Sample record selected</strong><span>Uses synthetic workers comp medical text so you can test the review table without uploading a file.</span></div>',
            unsafe_allow_html=True,
        )
        with st.expander("View or edit sample text", expanded=False):
            sample_text = st.text_area("Sample medical-record text", value=SAMPLE_MEDICAL_RECORD, height=240, label_visibility="collapsed")
    return case_name, parse_sample_pages(sample_text, document_name="Sample Medical Record")


def extract_pages_from_uploaded_pdfs(uploaded_pdfs, max_pages: int, ocr_enabled: bool) -> list[PageText]:
    pages: list[PageText] = []
    used_document_names: set[str] = set()
    pdf_sources: dict[str, bytes] = {}

    for uploaded_pdf in uploaded_pdfs:
        document_name = unique_document_name(uploaded_pdf.name, used_document_names)
        used_document_names.add(document_name)
        pdf_bytes = uploaded_pdf.getvalue()
        pdf_sources[document_name] = pdf_bytes
        pages.extend(
            extract_pages_from_pdf(
                pdf_bytes,
                document_name,
                max_pages=max_pages,
                ocr_enabled=ocr_enabled,
            )
        )

    st.session_state["pdf_sources"] = pdf_sources
    return pages


def unique_document_name(document_name: str, used_names: set[str]) -> str:
    if document_name not in used_names:
        return document_name

    stem, dot, suffix = document_name.rpartition(".")
    stem = stem or document_name
    extension = f".{suffix}" if dot else ""
    counter = 2
    while True:
        candidate = f"{stem} ({counter}){extension}"
        if candidate not in used_names:
            return candidate
        counter += 1


def show_loaded_sources_summary(pages: list[PageText], max_chars: int) -> None:
    total_chars = sum(len(page.text) for page in pages)
    document_count = len({page.document_name for page in pages})
    st.success(f"Loaded {len(pages)} page(s) from {document_count} source document(s).")
    if total_chars > max_chars:
        st.warning(f"Source text was trimmed to {max_chars:,} characters for faster processing.")


def render_generation_panel(case_name: str, pages: list[PageText], max_chars: int) -> None:
    page_count = len(pages)
    char_count = sum(len(page.text) for page in pages)
    source_names = sorted({page.document_name for page in pages})
    source_label = ", ".join(source_names[:2])
    if len(source_names) > 2:
        source_label += f" + {len(source_names) - 2} more"

    st.markdown(
        f"""
        <div class="action-panel">
            <div class="panel-heading">Ready to Generate</div>
            <div class="panel-copy">{page_count} page(s), {char_count:,} characters loaded from {source_label}.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    action_col, note_col = st.columns([0.28, 0.72])
    with action_col:
        if st.button("Generate cited chronology", type="primary", width="stretch"):
            run_chronology_pipeline(case_name=case_name, pages=pages, max_chars=max_chars)
    with note_col:
        st.markdown(
            '<div class="section-note">The output is a draft review table. Approve rows only after checking source snippets or the PDF page.</div>',
            unsafe_allow_html=True,
        )


def run_chronology_pipeline(case_name: str, pages: list[PageText], max_chars: int) -> None:
    with st.spinner("Extracting cited medical events..."):
        rows = extract_chronology_rows(pages, max_chars=max_chars)

    if not rows:
        st.warning("No dated medical events were found. Try records with explicit dates of service.")
        return

    rows = add_duplicate_flags(rows)
    st.session_state["case_name"] = case_name
    st.session_state["chronology_rows"] = rows




def render_chronology_workspace(case_name: str, rows: list[dict]) -> None:
    st.divider()
    rows = ensure_reviewer_fields(rows)
    render_summary(case_name, rows)
    rows = render_duplicate_review_tools(rows)
    st.session_state["chronology_rows"] = rows

    editable_columns = [
        "event_number",
        "review_status",
        "date",
        "date_precision_note",
        "date_meaning",
        "provider",
        "provider_note",
        "category",
        "summary",
        "document",
        "page",
        "extraction_method",
        "confidence",
        "importance",
        "gap_flag",
        "duplicate_flag",
        "duplicate_group",
        "duplicate_note",
    ]

    st.markdown('<div class="panel-heading">Chronology Review Table</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-note">Review the chronology row by row. Edit the visible fields, approve verified events, and use the source tab below to check citations against the original page.</div>',
        unsafe_allow_html=True,
    )
    edited_table = st.data_editor(
        pd.DataFrame(rows)[editable_columns],
        key="chronology_editor",
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        disabled=[
            "event_number",
            "document",
            "page",
            "extraction_method",
            "provider_note",
            "confidence",
            "gap_flag",
            "duplicate_flag",
            "duplicate_group",
            "duplicate_note",
        ],
        column_config={
            "event_number": st.column_config.NumberColumn("Event #", width="small"),
            "review_status": st.column_config.SelectboxColumn(
                "Review",
                options=["Needs review", "Approved", "Rejected"],
                required=True,
            ),
            "date": st.column_config.TextColumn("Date", width="medium"),
            "date_precision_note": st.column_config.TextColumn("Date precision", width="small"),
            "date_meaning": st.column_config.TextColumn("Date meaning", width="small"),
            "provider": st.column_config.TextColumn("Provider / facility", width="medium"),
            "provider_note": st.column_config.TextColumn("Provider status", width="small"),
            "category": st.column_config.SelectboxColumn("Category", options=CATEGORY_OPTIONS),
            "document": st.column_config.TextColumn("Document", width="medium"),
            "page": st.column_config.NumberColumn("Page", width="small"),
            "extraction_method": st.column_config.TextColumn("Source type", width="small"),
            "confidence": st.column_config.SelectboxColumn("Confidence", options=["High", "Medium", "Low"]),
            "importance": st.column_config.SelectboxColumn("Importance", options=["Low", "Normal", "High", "Critical"]),
            "gap_flag": st.column_config.TextColumn("Treatment gap", width="small"),
            "duplicate_flag": st.column_config.TextColumn("Duplicate", width="small"),
            "duplicate_group": st.column_config.TextColumn("Dup group", width="small"),
            "duplicate_note": st.column_config.TextColumn("Duplicate reason", width="medium"),
            "summary": st.column_config.TextColumn("Event summary", width="large"),
        },
    )

    synced_rows = sync_edited_rows(rows, edited_table)
    st.session_state["chronology_rows"] = synced_rows

    source_tab, export_tab, notes_tab = st.tabs(["Review source", "Export", "Workflow notes"])
    with source_tab:
        render_source_viewer(synced_rows)
    with export_tab:
        render_exports(case_name, synced_rows)
    with notes_tab:
        render_workflow_notes()


def ensure_reviewer_fields(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["category"] = normalize_row_category(row)
        row.setdefault("date_precision_note", friendly_date_precision(row.get("date_precision", "")))
        row.setdefault("date_meaning", friendly_date_context(row.get("date_context", "point")))
        row.setdefault("provider_note", friendly_provider_source(row.get("provider_source", "")))
        row.setdefault("duplicate_flag", "")
        row.setdefault("duplicate_group", "")
        row.setdefault("duplicate_note", "")
    return rows


def normalize_row_category(row: dict) -> str:
    category = row.get("category", "")
    if category in CATEGORY_OPTIONS:
        return category
    if category in LEGACY_CATEGORY_MAP:
        return LEGACY_CATEGORY_MAP[category]

    source_text = row.get("source_snippet") or row.get("summary") or ""
    if source_text:
        return classify_medical_category(source_text)
    return "Medical Event"


def render_workflow_notes() -> None:
    st.subheader("Review workflow")
    st.markdown(
        """
1. Check rows with `Needs review`, `Medium/Low` confidence, inferred/missing providers, treatment gaps, or duplicate flags.
2. Open the source panel and verify the cited page/snippet.
3. Edit provider/category/summary if needed.
4. Mark verified rows as `Approved`.
5. Reject duplicate, irrelevant, or incorrect rows.
6. Export the approved chronology when review is complete.
        """
    )
    st.info("For final work product, use the `Approved only` export mode.")


def render_summary(case_name: str, rows: list[dict]) -> None:
    approved_count = sum(1 for row in rows if row["review_status"] == "Approved")
    needs_review_count = sum(1 for row in rows if row["review_status"] == "Needs review")
    high_confidence_count = sum(1 for row in rows if row["confidence"] == "High")
    treatment_gap_count = sum(1 for row in rows if "day gap" in row.get("gap_flag", ""))
    duplicate_count = sum(1 for row in rows if row.get("duplicate_flag"))

    st.markdown(f'<div class="panel-heading">{case_name}</div>', unsafe_allow_html=True)
    col_events, col_approved, col_review, col_confidence, col_gaps, col_duplicates = st.columns(6)
    col_events.metric("Events", len(rows))
    col_approved.metric("Approved", approved_count)
    col_review.metric("Needs review", needs_review_count)
    col_confidence.metric("High confidence", high_confidence_count)
    col_gaps.metric("Treatment gaps", treatment_gap_count)
    col_duplicates.metric("Duplicates", duplicate_count)


def render_duplicate_review_tools(rows: list[dict]) -> list[dict]:
    duplicate_groups = sorted({row.get("duplicate_group") for row in rows if row.get("duplicate_group")})
    if not duplicate_groups:
        return rows

    with st.expander("Possible duplicate events", expanded=True):
        st.markdown(
            '<div class="section-note">Review similar events. Keep the best row, then reject the others or merge their wording manually into the kept row.</div>',
            unsafe_allow_html=True,
        )
        selected_group = st.selectbox("Duplicate group", duplicate_groups)
        group_rows = [row for row in rows if row.get("duplicate_group") == selected_group]

        for row in group_rows:
            st.markdown(
                f"""
                <div class="duplicate-card">
                    <strong>Event {row['event_number']} - {row['date']}</strong><br/>
                    {row['summary']}<br/>
                    <small>{row['document']}, p. {row['page']} | {row['provider']} | {row['review_status']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        keep_options = {f"Keep event {row['event_number']}": row["event_number"] for row in group_rows}
        selected_keep_label = st.selectbox("Row to keep", list(keep_options))
        merge_text = st.checkbox("Append rejected duplicate summaries to kept row", value=False)

        if st.button("Reject other rows in this group"):
            keep_event_number = keep_options[selected_keep_label]
            rows = reject_duplicate_group(rows, selected_group, keep_event_number, merge_text)
            st.session_state["chronology_rows"] = rows
            st.rerun()

    return rows


def reject_duplicate_group(rows: list[dict], group_name: str, keep_event_number: int, merge_text: bool) -> list[dict]:
    kept_row = next((row for row in rows if row["event_number"] == keep_event_number), None)
    rejected_summaries: list[str] = []

    for row in rows:
        if row.get("duplicate_group") != group_name or row["event_number"] == keep_event_number:
            continue
        row["review_status"] = "Rejected"
        rejected_summaries.append(row.get("summary", ""))

    if kept_row and merge_text and rejected_summaries:
        merged_summary = kept_row.get("summary", "")
        for summary in rejected_summaries:
            if summary and summary not in merged_summary:
                merged_summary = f"{merged_summary}; {summary}"
        kept_row["summary"] = merged_summary[:500]
        kept_row["duplicate_flag"] = "Merged duplicate group"
        kept_row["duplicate_note"] = "Rejected duplicate summaries were appended"

    return rows


def sync_edited_rows(original_rows: list[dict], edited_table: pd.DataFrame) -> list[dict]:
    synced_rows: list[dict] = []
    original_by_position = {index: row for index, row in enumerate(original_rows)}

    for index, edited_row in edited_table.iterrows():
        original = original_by_position.get(index, {})
        row = dict(original)
        for column, value in edited_row.items():
            row[column] = "" if pd.isna(value) else value
        row.setdefault("id", len(synced_rows) + 1)
        row.setdefault("event_number", len(synced_rows) + 1)
        row.setdefault("source_snippet", row.get("summary", ""))
        row.setdefault("date_sort", row.get("date", ""))
        row.setdefault("date_precision_note", friendly_date_precision(row.get("date_precision", "")))
        row.setdefault("date_meaning", friendly_date_context(row.get("date_context", "point")))
        row.setdefault("provider_note", friendly_provider_source(row.get("provider_source", "")))
        row.setdefault("duplicate_note", "")
        synced_rows.append(row)

    return synced_rows


