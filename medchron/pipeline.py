from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher

import spacy
import streamlit as st

from .dates import find_dates, format_date
from .ingestion import split_sentences
from .models import DateMatch, PageText
from .rules import CATEGORY_OPTIONS, CATEGORY_PRIORITY, LEGACY_CATEGORY_MAP, MEDICAL_CATEGORY_RULES, NON_MEDICAL_EVENT_KEYWORDS, PROVIDER_PATTERNS
from .text_utils import normalize_whitespace

@st.cache_data(show_spinner=False)
def extract_chronology_rows(pages: list[PageText], max_chars: int) -> list[dict]:
    rows: list[dict] = []
    chars_seen = 0

    for page in pages:
        if chars_seen >= max_chars:
            break
        chars_seen += len(page.text)
        sentences = split_sentences(page.text)

        for sentence_index, sentence in enumerate(sentences):
            if should_skip_non_medical_sentence(sentence):
                continue
            provider_context = nearby_provider_context(sentences, sentence_index)
            for date_match in find_dates(sentence):
                row = build_chronology_row(page, sentence, date_match, row_number=len(rows) + 1, provider_context=provider_context)
                rows.append(row)

    rows.sort(key=lambda row: (row["date_sort"], row["document"], row["page"], row["summary"]))
    return add_treatment_gap_flags(deduplicate_chronology_rows(rows))


def nearby_provider_context(sentences: list[str], sentence_index: int) -> str:
    nearby_indexes = [sentence_index - 1, sentence_index + 1]
    for nearby_index in nearby_indexes:
        if 0 <= nearby_index < len(sentences):
            provider = extract_provider(sentences[nearby_index])
            if provider != "Needs review":
                return provider
    return ""


def build_chronology_row(
    page: PageText,
    sentence: str,
    date_match: DateMatch,
    row_number: int,
    provider_context: str,
) -> dict:
    provider = extract_provider(sentence)
    provider_source = "same sentence"
    if provider == "Needs review" and provider_context and date_match.precision == "YMD":
        provider = provider_context
        provider_source = "nearby context"
    elif provider == "Needs review":
        provider_source = "not found"

    return {
        "id": row_number,
        "review_status": "Needs review",
        "date": format_date(date_match.date, date_match.precision),
        "date_precision": date_match.precision,
        "date_precision_note": friendly_date_precision(date_match.precision),
        "date_sort": date_match.date.isoformat(),
        "date_context": date_match.context,
        "date_meaning": friendly_date_context(date_match.context),
        "provider": provider,
        "provider_source": provider_source,
        "provider_note": friendly_provider_source(provider_source),
        "category": classify_medical_category(sentence),
        "summary": summarize_event_sentence(sentence, date_match),
        "source_snippet": sentence,
        "document": page.document_name,
        "page": page.page_number,
        "extraction_method": page.extraction_method,
        "confidence": estimate_confidence(sentence, date_match, provider_source),
        "importance": "Normal",
        "gap_flag": "",
    }


def should_skip_non_medical_sentence(sentence: str) -> bool:
    lower_sentence = sentence.lower()
    if any(keyword in lower_sentence for keyword in NON_MEDICAL_EVENT_KEYWORDS):
        return True
    return False


def classify_medical_category(sentence: str) -> str:
    lower_sentence = sentence.lower()
    for category in CATEGORY_PRIORITY:
        keywords = MEDICAL_CATEGORY_RULES[category]
        if any(category_keyword_matches(lower_sentence, keyword) for keyword in keywords):
            return category
    return "Medical Event"


def category_keyword_matches(lower_sentence: str, keyword: str) -> bool:
    # Use token boundaries so short abbreviations like "ER" or "PT" do not
    # accidentally match inside unrelated words such as "therapy" or "regular".
    normalized_keyword = keyword.lower()
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
    return bool(re.search(pattern, lower_sentence))


def extract_provider(sentence: str) -> str:
    for pattern in PROVIDER_PATTERNS:
        match = pattern.search(sentence)
        if match:
            return clean_provider_name(match.group(0))
    return "Needs review"


def clean_provider_name(provider: str) -> str:
    provider = provider.strip(" ,.;:-")
    provider = re.sub(r"^(at|by|with|from)\s+", "", provider, flags=re.I)
    return provider


def summarize_event_sentence(sentence: str, date_match: DateMatch) -> str:
    raw_date = date_match.raw_text
    summary = re.sub(rf"\b(?:on|by|in|through|from|starting|ending|effective)\s+{re.escape(raw_date)}\b", "", sentence, flags=re.I)
    summary = summary.replace(raw_date, "")
    summary = re.sub(r"\s{2,}", " ", summary)
    summary = re.sub(r"\s+([,.;:])", r"\1", summary)
    summary = re.sub(r"\b(on|by|in|through|from|starting|ending|effective)\s+(?=at\b)", "", summary, flags=re.I)
    summary = re.sub(r"^(on|by|in|through|from|starting|ending|effective)\s+", "", summary, flags=re.I)
    summary = summary.strip(" ,.-")
    if date_match.context == "range_start":
        summary = f"Treatment period began: {summary}"
    elif date_match.context == "range_end":
        summary = f"Treatment period ended: {summary}"
    return summary[:320]


def friendly_date_precision(precision: str) -> str:
    labels = {
        "YMD": "Exact date",
        "YM": "Month only",
        "Y": "Year only",
    }
    return labels.get(precision, "Needs review")


def friendly_date_context(context: str) -> str:
    labels = {
        "point": "Event date",
        "range_start": "Treatment start",
        "range_end": "Treatment end",
    }
    return labels.get(context, "Event date")


def friendly_provider_source(provider_source: str) -> str:
    labels = {
        "same sentence": "Found in event",
        "nearby context": "Inferred nearby - verify",
        "not found": "Missing - review",
    }
    return labels.get(provider_source, "Needs review")


def estimate_confidence(sentence: str, date_match: DateMatch, provider_source: str) -> str:
    score = 0
    if date_match.precision == "YMD":
        score += 2
    elif date_match.precision == "YM":
        score += 1
    if provider_source == "same sentence":
        score += 1
    if classify_medical_category(sentence) != "Medical Event":
        score += 1

    if provider_source == "not found":
        score -= 1
    elif provider_source == "nearby context":
        score -= 1

    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def deduplicate_chronology_rows(rows: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, int]] = set()
    unique_rows: list[dict] = []

    for row in rows:
        key = (row["date"], row["source_snippet"], row["page"])
        if key in seen:
            continue
        seen.add(key)
        row["id"] = len(unique_rows) + 1
        row["event_number"] = len(unique_rows) + 1
        unique_rows.append(row)

    return unique_rows


def add_treatment_gap_flags(rows: list[dict]) -> list[dict]:
    previous_date: datetime | None = None
    previous_precision: str | None = None

    for row in rows:
        current_date = datetime.fromisoformat(row["date_sort"])
        if previous_date is None:
            row["gap_flag"] = ""
        elif row.get("date_context") == "range_end":
            row["gap_flag"] = "Treatment period end"
        elif previous_precision != "YMD" or row.get("date_precision") != "YMD":
            row["gap_flag"] = ""
        else:
            gap_days = (current_date - previous_date).days
            if gap_days >= 90:
                row["gap_flag"] = f"{gap_days} day gap"
            elif gap_days >= 60:
                row["gap_flag"] = f"{gap_days} day gap"
            elif gap_days >= 30:
                row["gap_flag"] = f"{gap_days} day gap"
            else:
                row["gap_flag"] = ""
        previous_date = current_date
        previous_precision = row.get("date_precision")

    return rows


def add_duplicate_flags(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["duplicate_flag"] = ""
        row["duplicate_group"] = ""
        row["duplicate_note"] = ""

    duplicate_group = 1
    grouped_indexes: set[int] = set()

    for index, row in enumerate(rows):
        if index in grouped_indexes:
            continue
        similar_indexes = [index]
        for other_index in range(index + 1, len(rows)):
            if other_index in grouped_indexes:
                continue
            if rows_are_similar(row, rows[other_index]):
                similar_indexes.append(other_index)

        if len(similar_indexes) > 1:
            group_name = f"D{duplicate_group}"
            for similar_index in similar_indexes:
                rows[similar_index]["duplicate_flag"] = "Possible duplicate"
                rows[similar_index]["duplicate_group"] = group_name
                rows[similar_index]["duplicate_note"] = "Same date with similar wording/provider/category"
                grouped_indexes.add(similar_index)
            duplicate_group += 1

    return rows


def rows_are_similar(row: dict, other_row: dict) -> bool:
    if row.get("date") != other_row.get("date"):
        return False
    if row.get("date_precision") != other_row.get("date_precision"):
        return False

    summary_ratio = SequenceMatcher(
        None,
        normalize_for_similarity(row.get("summary", "")),
        normalize_for_similarity(other_row.get("summary", "")),
    ).ratio()
    token_overlap = similarity_token_overlap(row.get("summary", ""), other_row.get("summary", ""))

    same_provider = providers_look_related(row.get("provider", ""), other_row.get("provider", ""))
    same_category = row.get("category") == other_row.get("category")
    repeat_cue = has_repeat_cue(row.get("source_snippet", "")) or has_repeat_cue(other_row.get("source_snippet", ""))

    return (
        summary_ratio >= 0.72
        or token_overlap >= 0.55
        or (summary_ratio >= 0.55 and (same_provider or same_category))
        or (repeat_cue and same_provider)
    )


def normalize_for_similarity(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\b(the|patient|was|were|with|and|for|this|that|noted)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def similarity_token_overlap(text: str, other_text: str) -> float:
    tokens = meaningful_tokens(text)
    other_tokens = meaningful_tokens(other_text)
    if not tokens or not other_tokens:
        return 0.0
    return len(tokens & other_tokens) / min(len(tokens), len(other_tokens))


def meaningful_tokens(text: str) -> set[str]:
    stop_words = {
        "the", "patient", "was", "were", "with", "and", "for", "this", "that",
        "noted", "from", "after", "because", "summary", "repeats", "note",
        "employer", "adjuster", "performed", "reported",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stop_words
    }


def providers_look_related(provider: str, other_provider: str) -> bool:
    if provider == "Needs review" or other_provider == "Needs review":
        return False
    provider_tokens = meaningful_tokens(provider.replace("Dr.", ""))
    other_tokens = meaningful_tokens(other_provider.replace("Dr.", ""))
    return bool(provider_tokens & other_tokens)


def has_repeat_cue(text: str) -> bool:
    return bool(re.search(r"\b(repeats|summary|again states|also states)\b", text, flags=re.I))


