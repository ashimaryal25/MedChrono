from __future__ import annotations

import re
import shutil
from io import BytesIO

import spacy
import streamlit as st
from pypdf import PdfReader

from .models import PageText
from .text_utils import normalize_whitespace

try:
    import pytesseract
    from pdf2image import convert_from_bytes
except ImportError:
    pytesseract = None
    convert_from_bytes = None

def extract_pages_from_pdf(pdf_bytes: bytes, document_name: str, max_pages: int, ocr_enabled: bool) -> list[PageText]:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[PageText] = []
    pages_to_read = min(len(reader.pages), max_pages)
    pages_needing_ocr: list[int] = []

    for page_index in range(pages_to_read):
        text = reader.pages[page_index].extract_text() or ""
        if text.strip():
            pages.append(
                PageText(
                    document_name=document_name,
                    page_number=page_index + 1,
                    text=normalize_whitespace(text),
                    extraction_method="PDF text",
                )
            )
        else:
            pages_needing_ocr.append(page_index + 1)

    if pages_needing_ocr and ocr_enabled:
        pages.extend(extract_ocr_pages(pdf_bytes, document_name, pages_needing_ocr))
    elif pages_needing_ocr:
        st.info(f"{len(pages_needing_ocr)} page(s) had no embedded text. Enable OCR to process scanned pages.")

    return sorted(pages, key=lambda page: page.page_number)


def extract_ocr_pages(pdf_bytes: bytes, document_name: str, page_numbers: list[int]) -> list[PageText]:
    if not ocr_runtime_is_available():
        st.warning(
            "Some pages appear scanned, but OCR is not ready. Install Tesseract and Poppler, "
            "then rerun the app to OCR scanned pages."
        )
        return []

    ocr_pages: list[PageText] = []
    for page_number in page_numbers:
        try:
            images = convert_from_bytes(pdf_bytes, first_page=page_number, last_page=page_number, dpi=220)
        except Exception as exc:
            st.warning(f"OCR could not read page {page_number}. Check Poppler/Tesseract setup. Details: {exc}")
            continue
        if not images:
            continue
        text = pytesseract.image_to_string(images[0]) or ""
        if text.strip():
            ocr_pages.append(
                PageText(
                    document_name=document_name,
                    page_number=page_number,
                    text=normalize_whitespace(text),
                    extraction_method="OCR",
                )
            )
    return ocr_pages


def ocr_runtime_is_available() -> bool:
    return (
        pytesseract is not None
        and convert_from_bytes is not None
        and shutil.which("tesseract") is not None
    )


def parse_sample_pages(text: str, document_name: str) -> list[PageText]:
    page_chunks = re.split(r"\[Page\s+(\d+)\]", text)
    if len(page_chunks) == 1:
        return [PageText(document_name=document_name, page_number=1, text=normalize_whitespace(text), extraction_method="Sample text")]

    pages: list[PageText] = []
    for index in range(1, len(page_chunks), 2):
        page_number = int(page_chunks[index])
        page_text = normalize_whitespace(page_chunks[index + 1])
        if page_text:
            pages.append(PageText(document_name=document_name, page_number=page_number, text=page_text, extraction_method="Sample text"))
    return pages


def trim_pages_to_character_limit(pages: list[PageText], max_chars: int) -> list[PageText]:
    trimmed_pages: list[PageText] = []
    chars_used = 0

    for page in pages:
        remaining_chars = max_chars - chars_used
        if remaining_chars <= 0:
            break
        page_text = page.text[:remaining_chars]
        trimmed_pages.append(PageText(page.document_name, page.page_number, page_text, page.extraction_method))
        chars_used += len(page_text)

    return trimmed_pages


@st.cache_resource(show_spinner=False)
def load_sentence_splitter():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def split_sentences(text: str) -> list[str]:
    # PDF extractors often insert hard line breaks in the middle of a sentence.
    # Join useful content before sentence splitting so dates like
    # "through March 24,\n2023" stay attached, while page headers and metadata
    # do not get merged into the first dated event on the page.
    content_lines = [line.strip() for line in text.splitlines() if keep_content_line(line)]
    clean_text = normalize_whitespace(" ".join(content_lines))
    doc = load_sentence_splitter()(clean_text)
    return [sentence.text.strip() for sentence in doc.sents if sentence.text.strip()]


def keep_content_line(line: str) -> bool:
    clean_line = line.strip()
    if not clean_line:
        return False
    if re.match(r"^\[?Page\s+\d+\]?\s*(?:-|$)", clean_line, flags=re.I):
        return False
    if re.search(r"\bPage\s+\d+\s*$", clean_line, flags=re.I) and not re.search(r"\b\d{4}\b", clean_line):
        return False
    if re.match(r"^(Provider|Patient|Claim Type|DOB|Date of Birth|MRN|Record ID)\s*:", clean_line, flags=re.I):
        return False
    if "not real phi" in clean_line.lower() or "fake sample medical record" in clean_line.lower():
        return False
    return True


