from __future__ import annotations

import re

SAMPLE_MEDICAL_RECORD = """[Page 1]
On January 12, 2023, the patient presented to City Emergency Department after a workplace fall.
The patient reported lower back pain and right shoulder pain. X-rays showed no acute fracture.
The patient was discharged with ibuprofen and advised to follow up with orthopedics.

[Page 2]
On February 3, 2023, the patient was evaluated by OrthoCare Associates for persistent lumbar pain.
Dr. Patel diagnosed lumbar strain and recommended physical therapy twice weekly for six weeks.
Work restrictions included no lifting over 10 pounds and no prolonged standing.

[Page 3]
Physical therapy started on February 10, 2023 at Metro Rehab Clinic.
The patient attended therapy visits through March 24, 2023 with gradual improvement.
An MRI performed on April 5, 2023 showed mild L4-L5 disc bulge without nerve compression.

[Page 4]
On May 2, 2023, Dr. Patel noted continued pain but improved range of motion.
The patient was released to modified duty and prescribed naproxen.
On June 14, 2023, the patient reported increased pain after returning to work.

[Page 5]
On August 1, 2023, the patient reached maximum medical improvement.
Dr. Patel assigned a 5 percent impairment rating and released the patient to full duty."""


MONTH_PATTERN = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?"
)
YEAR_PATTERN = r"(?:18|19|20|21)\d{2}"
ORDINAL_DAY_PATTERN = r"\d{1,2}(?:st|nd|rd|th)?"

DATE_PATTERNS = [
    ("YMD", re.compile(rf"\b(?:{MONTH_PATTERN})\.?\s+{ORDINAL_DAY_PATTERN},?\s+{YEAR_PATTERN}\b", re.I)),
    ("YMD", re.compile(rf"\b{ORDINAL_DAY_PATTERN}\s+(?:{MONTH_PATTERN})\.?,?\s+{YEAR_PATTERN}\b", re.I)),
    ("YMD", re.compile(rf"\b{YEAR_PATTERN}-\d{{1,2}}-\d{{1,2}}\b")),
    ("YMD", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-](?:\d{2}|\d{4})\b")),
    ("YM", re.compile(rf"\b(?:{MONTH_PATTERN})\.?\s+{YEAR_PATTERN}\b", re.I)),
    ("Y", re.compile(rf"\b{YEAR_PATTERN}\b")),
]

DATEPARSER_SETTINGS = {
    "DATE_ORDER": "MDY",
    "PREFER_DAY_OF_MONTH": "first",
    "PREFER_MONTH_OF_YEAR": "first",
    "REQUIRE_PARTS": ["year"],
    "RETURN_AS_TIMEZONE_AWARE": False,
}

# These are legal-review categories, not clinical billing codes. The goal is to
# help a paralegal, legal nurse, or claims reviewer scan the chronology quickly.
MEDICAL_CATEGORY_RULES = {
    "Injury / Incident": [
        "accident", "injury", "injured", "fall", "fell", "slipped", "collision",
        "motor vehicle", "mva", "workplace", "loading dock", "lifting boxes",
    ],
    "Emergency / Urgent Care": [
        "emergency", "emergency department", "er", "urgent care", "triage",
        "ambulance", "ems", "discharged from the emergency",
    ],
    "Hospitalization": [
        "admitted", "admission", "hospitalized", "inpatient", "observation unit",
        "overnight stay", "hospital course",
    ],
    "Discharge": [
        "discharged", "discharge instructions", "released from hospital",
        "sent home", "stable for discharge",
    ],
    "Primary / Occupational Medicine": [
        "primary care", "pcp", "family medicine", "occupational medicine",
        "workwell", "employee health", "clinic visit",
    ],
    "Specialist Evaluation": [
        "orthopedic", "orthopedics", "orthocare", "spinecare", "neurology",
        "neurosurgery", "pain management", "evaluated by", "consultation",
        "specialist", "dr.",
    ],
    "Symptoms / Complaints": [
        "reported pain", "complained of", "complaints of", "persistent pain",
        "worsening pain", "increased pain", "numbness", "tingling", "weakness",
        "limited range of motion", "swelling", "headache", "dizziness",
    ],
    "Diagnosis": [
        "diagnosed", "diagnosis", "assessment", "impression",
        "diagnoses included", "diagnostic impression",
    ],
    "Diagnostic Imaging": [
        "x-ray", "x-rays", "xray", "xrays", "mri", "ct scan", "cat scan",
        "ultrasound", "imaging", "radiology", "radiograph", "arthrogram",
        "disc", "nerve compression",
    ],
    "Diagnostic Testing": [
        "emg", "nerve conduction", "ncs", "eeg", "ekg", "ecg", "pulmonary function",
        "functional capacity evaluation", "fce",
    ],
    "Lab Work": [
        "lab", "laboratory", "blood work", "cbc", "urinalysis", "toxicology",
        "culture", "metabolic panel",
    ],
    "Physical Therapy / Rehab": [
        "physical therapy", "pt", "therapy", "rehab", "rehabilitation",
        "home exercise", "range of motion", "strengthening",
    ],
    "Chiropractic Care": [
        "chiropractic", "chiropractor", "adjustment", "spinal manipulation",
    ],
    "Medication": [
        "prescribed", "prescription", "ibuprofen", "naproxen", "meloxicam",
        "gabapentin", "opioid", "hydrocodone", "oxycodone", "muscle relaxer",
        "medication", "medications", "refill",
    ],
    "Injection / Procedure": [
        "injection", "epidural", "steroid injection", "nerve block",
        "radiofrequency ablation", "rfa", "trigger point", "procedure",
    ],
    "Surgery": [
        "surgery", "surgical", "operation", "operative", "arthroscopy",
        "fusion", "laminectomy", "discectomy", "repair", "open reduction",
    ],
    "Treatment Plan / Referral": [
        "recommended", "ordered", "referred", "referral", "treatment plan",
        "plan included", "authorization", "scheduled for", "follow up with",
    ],
    "Follow-up": [
        "follow up", "follow-up", "reevaluation", "recheck", "return visit",
        "next appointment",
    ],
    "Work Status / Restrictions": [
        "work restriction", "work restrictions", "modified duty", "full duty",
        "light duty", "off work", "no lifting", "returning to work",
        "released to", "return to work", "removed the patient from work",
        "removed from work", "prolonged standing",
    ],
    "Disability / Leave": [
        "temporary total disability", "ttd", "temporary partial disability",
        "tpd", "disability", "leave of absence", "fmla", "unable to work",
    ],
    "Impairment / MMI": [
        "maximum medical improvement", "mmi", "impairment rating",
        "permanent impairment", "whole person impairment", "permanent partial",
    ],
    "Missed Appointment / Compliance": [
        "missed appointment", "no show", "no-show", "cancelled appointment",
        "failed to attend", "noncompliant", "non-compliant",
    ],
    "Prior History": [
        "prior history", "past medical history", "preexisting", "pre-existing",
        "previous injury", "prior back pain", "prior intermittent", "baseline",
        "before the accident", "without regular treatment",
    ],
    "Administrative / Records": [
        "claim summary", "adjuster summary", "employer note", "records review",
        "billing review", "final narrative report", "faxed", "medical records",
        "authorization request",
    ],
    "Mental Health": [
        "depression", "anxiety", "ptsd", "psychological", "psychiatric",
        "counseling", "therapy session", "behavioral health",
    ],
    "Dental / Vision": [
        "dental", "dentist", "tooth", "teeth", "vision", "ophthalmology",
        "optometry", "eye exam",
    ],
}

CATEGORY_PRIORITY = [
    "Impairment / MMI",
    "Surgery",
    "Injection / Procedure",
    "Work Status / Restrictions",
    "Disability / Leave",
    "Missed Appointment / Compliance",
    "Prior History",
    "Administrative / Records",
    "Diagnostic Imaging",
    "Diagnostic Testing",
    "Lab Work",
    "Hospitalization",
    "Emergency / Urgent Care",
    "Discharge",
    "Treatment Plan / Referral",
    "Physical Therapy / Rehab",
    "Chiropractic Care",
    "Medication",
    "Diagnosis",
    "Symptoms / Complaints",
    "Primary / Occupational Medicine",
    "Specialist Evaluation",
    "Follow-up",
    "Mental Health",
    "Dental / Vision",
    "Injury / Incident",
]

LEGACY_CATEGORY_MAP = {
    "Emergency Visit": "Emergency / Urgent Care",
    "Specialist Visit": "Specialist Evaluation",
    "Physical Therapy": "Physical Therapy / Rehab",
    "Work Status": "Work Status / Restrictions",
    "Impairment/MMI": "Impairment / MMI",
}

CATEGORY_OPTIONS = list(MEDICAL_CATEGORY_RULES) + ["Medical Event"]

NON_MEDICAL_EVENT_KEYWORDS = [
    "billing review",
    "faxed the",
    "no appointment occurred",
    "no documented treatment between",
    "should not be treated as a medical treatment event",
]

PROVIDER_PATTERNS = [
    re.compile(r"\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"),
    re.compile(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4}\s+(?:Hospital|Clinic|Associates|Department|Rehab|Care|Center|Institute|Orthopedics|Therapy|Medicine|Imaging)\b"),
    re.compile(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,4}\s+(?:Emergency Department|Physical Therapy|Pain Management)\b"),
]


