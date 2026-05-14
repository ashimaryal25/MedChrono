from __future__ import annotations

import base64
import re
from io import BytesIO

import fitz
import streamlit as st
import streamlit.components.v1 as components

from .text_utils import normalize_whitespace

def render_source_viewer(rows: list[dict]) -> None:
    st.subheader("Source verification")
    if not rows:
        st.info("No events to verify.")
        return

    row_labels = [
        f"{row['id']}. {row['date']} - page {row['page']} - {row['summary'][:70]}"
        for row in rows
        if row["review_status"] != "Rejected"
    ]
    if not row_labels:
        st.info("All rows are rejected. Change a row's review status to verify its source.")
        return
    selected_label = st.selectbox("Select event to verify", row_labels)
    selected_id = int(selected_label.split(".", 1)[0])
    selected_row = next(row for row in rows if row["id"] == selected_id)

    event_col, document_col = st.columns([0.36, 0.64])
    with event_col:
        st.markdown(
            f"""
            <div class="source-review-card">
                <strong>Event {selected_row.get('event_number', selected_row.get('id'))}</strong><br/>
                {selected_row.get('date', '')}<br/>
                <div class="source-meta">
                    <div><strong>Provider</strong><br/>{selected_row.get('provider', '')}</div>
                    <div><strong>Category</strong><br/>{selected_row.get('category', '')}</div>
                    <div><strong>Source</strong><br/>{selected_row.get('document', '')}, p. {selected_row.get('page', '')}</div>
                    <div><strong>Status</strong><br/>{selected_row.get('provider_note', 'Unknown')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if "day gap" in selected_row.get("gap_flag", ""):
            st.warning(f"Treatment gap before this event: {selected_row['gap_flag']}")
        elif selected_row.get("gap_flag"):
            st.info(selected_row["gap_flag"])
        st.text_area("Extracted source text", value=selected_row["source_snippet"], height=190, disabled=True)

    with document_col:
        render_pdf_source_document(selected_row)


def render_pdf_source_document(row: dict) -> None:
    pdf_sources = st.session_state.get("pdf_sources", {})
    pdf_bytes = pdf_sources.get(row["document"])
    if not pdf_bytes:
        st.info("Upload a PDF to view a scrollable highlighted document. Sample/pasted text can only show the extracted source snippet.")
        return

    rendered_pages = render_full_document_with_highlight(
        pdf_bytes=pdf_bytes,
        row=row,
    )
    if rendered_pages is None:
        st.caption("Could not render this PDF document.")
        return

    page_images, highlight_found = rendered_pages
    caption = f"Scrollable PDF source - page {row.get('page', '')}"
    if not highlight_found:
        caption += " - exact highlight not found"
    st.caption(caption)
    st.markdown(
        f'<div class="document-page-count">Showing full document: {len(page_images)} page(s). Only the cited page is re-rendered when you switch events.</div>',
        unsafe_allow_html=True,
    )
    render_scrollable_document_viewer(page_images, cited_page_number=int(row["page"]))


def render_scrollable_document_viewer(page_images: list[tuple[int, bytes]], cited_page_number: int) -> None:
    page_markup = []
    for page_number, image_bytes in page_images:
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        cited_class = " cited-page" if page_number == cited_page_number else ""
        cited_badge = '<span class="cited-badge">cited page</span>' if page_number == cited_page_number else ""
        page_markup.append(
            f"""
            <section class="doc-page{cited_class}" id="page-{page_number}">
                <div class="page-label">Page {page_number} {cited_badge}</div>
                <img src="data:image/png;base64,{encoded_image}" />
            </section>
            """
        )

    html = f"""
    <style>
        .document-viewer {{
            height: 720px;
            overflow-y: auto;
            background: #eef3f8;
            border: 1px solid #cfd9e6;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            scroll-behavior: smooth;
        }}
        .doc-page {{
            max-width: 850px;
            margin: 0 auto 22px auto;
        }}
        .doc-page img {{
            width: 100%;
            display: block;
            background: #ffffff;
            border: 1px solid #d7e3f2;
            border-radius: 8px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
        }}
        .page-label {{
            color: #475569;
            font: 600 13px system-ui, -apple-system, Segoe UI, sans-serif;
            margin: 0 0 7px 2px;
        }}
        .cited-page {{
            scroll-margin-top: 14px;
        }}
        .cited-badge {{
            display: inline-block;
            margin-left: 8px;
            padding: 2px 8px;
            border-radius: 999px;
            background: #fff3c4;
            color: #7a5600;
            font-size: 12px;
            border: 1px solid #f5d76e;
        }}
    </style>
    <div class="document-viewer" id="document-viewer">
        {''.join(page_markup)}
    </div>
    <script>
        const viewer = document.getElementById("document-viewer");
        const cited = document.getElementById("page-{cited_page_number}");
        if (viewer && cited) {{
            viewer.scrollTop = cited.offsetTop - viewer.offsetTop - 12;
        }}
    </script>
    """
    components.html(html, height=745, scrolling=False)


def render_full_document_with_highlight(pdf_bytes: bytes, row: dict) -> tuple[list[tuple[int, bytes]], bool] | None:
    try:
        cited_page_number = int(row["page"])
        base_pages = render_pdf_page_images(pdf_bytes)
        highlighted_page = render_highlighted_pdf_page_image(
            pdf_bytes=pdf_bytes,
            page_number=cited_page_number,
            source_snippet=row.get("source_snippet", ""),
            date_text=row.get("date", ""),
        )
    except Exception:
        return None

    if highlighted_page is None:
        return base_pages, False

    highlighted_image, highlight_found = highlighted_page
    page_images = [
        (page_number, highlighted_image if page_number == cited_page_number else image_bytes)
        for page_number, image_bytes in base_pages
    ]
    return page_images, highlight_found


@st.cache_data(show_spinner=False, max_entries=4)
def render_pdf_page_images(pdf_bytes: bytes) -> list[tuple[int, bytes]]:
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_images: list[tuple[int, bytes]] = []
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.12, 1.12), alpha=False)
        page_images.append((page_index + 1, pixmap.tobytes("png")))
    pdf.close()
    return page_images


@st.cache_data(show_spinner=False, max_entries=128)
def render_highlighted_pdf_page_image(
    pdf_bytes: bytes,
    page_number: int,
    source_snippet: str,
    date_text: str,
) -> tuple[bytes, bool] | None:
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = pdf[page_number - 1]
    highlight_rects = find_source_rectangles(page, source_snippet, date_text)
    for rect in highlight_rects:
        annotation = page.add_highlight_annot(rect)
        annotation.set_colors(stroke=(1, 0.82, 0.05))
        annotation.update()

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.12, 1.12), alpha=False)
    image_bytes = pixmap.tobytes("png")
    pdf.close()
    return image_bytes, bool(highlight_rects)


def render_highlighted_document_pages(pdf_bytes: bytes, row: dict) -> tuple[list[tuple[int, bytes]], bool] | None:
    try:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None

    cited_page_number = int(row["page"])
    rendered_page_numbers = visible_source_page_numbers(cited_page_number, len(pdf))
    highlight_found = False
    page_images: list[tuple[int, bytes]] = []

    for page_number in rendered_page_numbers:
        page = pdf[page_number - 1]
        if page_number == cited_page_number:
            highlight_rects = find_source_rectangles(page, row.get("source_snippet", ""), row.get("date", ""))
            highlight_found = bool(highlight_rects)
            for rect in highlight_rects:
                annotation = page.add_highlight_annot(rect)
                annotation.set_colors(stroke=(1, 0.82, 0.05))
                annotation.update()
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        page_images.append((page_number, pixmap.tobytes("png")))

    pdf.close()
    return page_images, highlight_found


def visible_source_page_numbers(cited_page_number: int, total_pages: int) -> list[int]:
    start_page = max(1, cited_page_number - 1)
    end_page = min(total_pages, cited_page_number + 1)
    return list(range(start_page, end_page + 1))


def build_highlighted_pdf_document(pdf_bytes: bytes, row: dict) -> tuple[bytes, bool] | None:
    try:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = pdf[int(row["page"]) - 1]
    except Exception:
        return None

    highlight_rects = find_source_rectangles(page, row.get("source_snippet", ""), row.get("date", ""))
    for rect in highlight_rects:
        annotation = page.add_highlight_annot(rect)
        annotation.set_colors(stroke=(1, 0.82, 0.05))
        annotation.update()

    output = BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue(), bool(highlight_rects)


def render_highlighted_pdf_page(
    pdf_bytes: bytes,
    page_number: int,
    source_snippet: str,
    date_text: str,
) -> tuple[bytes, bool] | None:
    try:
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = pdf[page_number - 1]
    except Exception:
        return None

    highlight_rects = find_source_rectangles(page, source_snippet, date_text)
    for rect in highlight_rects:
        annotation = page.add_highlight_annot(rect)
        annotation.set_colors(stroke=(1, 0.85, 0.1))
        annotation.update()

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    image_bytes = pixmap.tobytes("png")
    pdf.close()
    return image_bytes, bool(highlight_rects)


def find_source_rectangles(page, source_snippet: str, date_text: str):
    search_terms = build_source_search_terms(source_snippet, date_text)
    for term in search_terms:
        rects = page.search_for(term, quads=False)
        if rects:
            return rects
    return []


def build_source_search_terms(source_snippet: str, date_text: str) -> list[str]:
    cleaned_snippet = normalize_whitespace(source_snippet)
    terms = [cleaned_snippet]

    if len(cleaned_snippet) > 90:
        terms.append(cleaned_snippet[:90])
    if date_text:
        terms.append(date_text)

    words = [word for word in re.findall(r"[A-Za-z0-9.-]+", cleaned_snippet) if len(word) > 3]
    if len(words) >= 6:
        terms.append(" ".join(words[:8]))

    deduped_terms: list[str] = []
    for term in terms:
        if term and term not in deduped_terms:
            deduped_terms.append(term)
    return deduped_terms


