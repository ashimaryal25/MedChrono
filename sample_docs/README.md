# Sample Documents

`fake_medical_record.pdf` is a synthetic medical-record-style PDF for testing the chronology workflow.

It contains no real patient information. Use it to test:

- PDF upload
- page-level text extraction
- event extraction
- source page rendering
- highlighted source text in the verification panel

`stress_test_medical_record.pdf` is a larger synthetic record for testing the table against messier chronology behavior:

- repeated same-date events
- month-only and year-only dates
- numeric dates
- treatment start/end language
- treatment gaps
- provider inference
- non-treatment administrative notes
