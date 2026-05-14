from __future__ import annotations

import re
import warnings
from datetime import datetime
from typing import Iterable

import dateparser
from dateparser.search import search_dates

from .models import DateMatch
from .rules import DATEPARSER_SETTINGS, DATE_PATTERNS, MONTH_PATTERN, ORDINAL_DAY_PATTERN, YEAR_PATTERN

def find_dates(sentence: str) -> list[DateMatch]:
    matches: list[DateMatch] = []
    occupied_spans: list[tuple[int, int]] = []

    for precision, pattern in DATE_PATTERNS:
        for regex_match in pattern.finditer(sentence):
            span = regex_match.span()
            if overlaps_existing_span(span, occupied_spans):
                continue

            raw_date = regex_match.group(0)
            parsed_date = parse_date(raw_date, precision)
            if parsed_date is None:
                continue

            matches.append(DateMatch(raw_date, parsed_date, precision, span[0], span[1], infer_date_context(sentence, span[0])))
            occupied_spans.append(span)

    if matches:
        return sorted(matches, key=lambda match: match.start)

    return find_dateparser_fallback_dates(sentence)


def overlaps_existing_span(span: tuple[int, int], occupied_spans: Iterable[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied_spans)


def parse_date(raw_date: str, precision: str) -> datetime | None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        parsed = dateparser.parse(raw_date, settings=DATEPARSER_SETTINGS)
    if parsed is None:
        return None

    if precision == "Y":
        return parsed.replace(month=1, day=1)
    if precision == "YM":
        return parsed.replace(day=1)
    return parsed


def find_dateparser_fallback_dates(sentence: str) -> list[DateMatch]:
    found_dates = search_dates(sentence, settings=DATEPARSER_SETTINGS) or []
    matches: list[DateMatch] = []

    for raw_date, parsed_date in found_dates:
        # Avoid turning relative follow-up language like "in 2 weeks" or page
        # numbers into fake chronology dates based on today's date.
        if not re.search(YEAR_PATTERN, raw_date):
            continue

        precision = infer_precision_from_text(raw_date)
        parsed_date = parse_date(raw_date, precision)
        if parsed_date is None:
            continue

        start = sentence.lower().find(raw_date.lower())
        end = start + len(raw_date) if start >= 0 else start
        matches.append(DateMatch(raw_date, parsed_date, precision, start, end, infer_date_context(sentence, start)))

    return matches


def infer_precision_from_text(raw_date: str) -> str:
    text = raw_date.strip()

    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-](?:\d{2}|\d{4})\b", text):
        return "YMD"
    if re.search(rf"\b{YEAR_PATTERN}-\d{{1,2}}-\d{{1,2}}\b", text):
        return "YMD"
    if re.search(rf"\b(?:{MONTH_PATTERN})\.?\s+{ORDINAL_DAY_PATTERN},?\s+{YEAR_PATTERN}\b", text, re.I):
        return "YMD"
    if re.search(rf"\b{ORDINAL_DAY_PATTERN}\s+(?:{MONTH_PATTERN})\.?,?\s+{YEAR_PATTERN}\b", text, re.I):
        return "YMD"
    if re.search(rf"\b(?:{MONTH_PATTERN})\.?\s+{YEAR_PATTERN}\b", text, re.I):
        return "YM"
    return "Y"


def infer_date_context(sentence: str, date_start: int) -> str:
    prefix = sentence[max(0, date_start - 24) : date_start].lower()
    if re.search(r"\b(through|until|to|ending|ended|throughout)\s+$", prefix):
        return "range_end"
    if re.search(r"\b(from|starting|started|beginning|began|since)\s+$", prefix):
        return "range_start"
    return "point"


def format_date(date: datetime, precision: str) -> str:
    if precision == "YMD":
        return f"{date.strftime('%B')} {date.day}, {date.year}"
    if precision == "YM":
        return date.strftime("%B %Y")
    return date.strftime("%Y")


