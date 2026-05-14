from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PageText:
    document_name: str
    page_number: int
    text: str
    extraction_method: str = "PDF text"


@dataclass(frozen=True)
class DateMatch:
    raw_text: str
    date: datetime
    precision: str
    start: int
    end: int
    context: str = "point"
