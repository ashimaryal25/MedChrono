# MedChronology Workspace

Prototype for a source-cited medical chronology workflow aimed at PI and workers' compensation teams.

The app turns a medical-record PDF or sample record text into an editable chronology table. Each event keeps the source document, page number, snippet, date precision, provider guess, category, confidence, and review status so a paralegal or legal nurse can verify the draft before export.

## Current MVP Slice

- Multiple PDF upload, pasted text, mixed PDF-plus-text sources, or built-in sample medical record
- Page-level text extraction
- Date-of-service extraction with explicit date precision
- Legal-review categories such as injury, diagnosis, imaging, therapy, procedures, work status, impairment/MMI, prior history, missed appointments, and administrative records
- Provider/facility heuristic extraction
- Editable review table with approve/reject workflow
- Source verification panel with document, page, provider, category, and snippet
- Source verification opens only the document tied to the selected event, with full-document scrolling and highlight support for uploaded PDFs
- Optional OCR path for scanned pages when Tesseract and Poppler are installed
- Treatment gap flags for 30+ day gaps between dated events
- Possible duplicate detection for same-date events with similar summaries
- Duplicate review tools to keep one row and reject or merge related rows
- CSV, Excel, and Word chronology exports
- Professional Word report with case name, generated date, summary stats, approved chronology table, source citations, treatment gap notes, and duplicate notes

## Sample PDF

Use `sample_docs/fake_medical_record.pdf` to test PDF upload, source-page rendering, and highlighted citations. It is synthetic and contains no real patient information.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run semantic_timeline_3.py
```

## Code Structure

`semantic_timeline_3.py` is now only the Streamlit entrypoint. The product code lives in `medchron/`:

- `ui.py` - Streamlit screens and review workflow
- `ingestion.py` - PDF, OCR, pasted text, and multi-source intake
- `pipeline.py` - chronology extraction, providers, categories, gaps, duplicates
- `dates.py` - date parsing, precision, and treatment start/end handling
- `rules.py` - sample record, date patterns, provider patterns, legal-review taxonomy
- `source_viewer.py` - source verification, PDF rendering, highlighting, document scrolling
- `exports.py` and `export_ui.py` - CSV, Excel, Word, row/column export controls
- `models.py` and `text_utils.py` - shared data containers and cleanup helpers

## OCR Setup

Text-based PDFs work with Python dependencies alone. Scanned PDFs need external OCR tools:

- Tesseract OCR
- Poppler

On macOS with Homebrew:

```bash
brew install tesseract poppler
```

On Windows, install Tesseract and Poppler separately, then make sure both are available on `PATH`.

## Product Direction

This is intentionally not a generic timeline generator. The target workflow is:

```text
medical records -> cited draft chronology -> human review/editing -> Word/Excel export
```

Next meaningful additions are stronger provider extraction, persistent case storage, audit trail, user accounts, and a full backend once the review workflow is validated.
