"""Laboratory import parsers for CSV, FHIR JSON and text-based PDF reports.

PDF extraction is deliberately conservative: only clearly structured name/value
lines are imported, every PDF-derived result is marked ``needs_review``, and a
missing date is an error rather than an invented value. Scanned image-only PDFs
are not OCR'd in the MVP.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Biomarker
from app.schemas import LabCreate

MAX_CSV_BYTES = 2_000_000
MAX_PDF_BYTES = 12_000_000
MAX_FHIR_BYTES = 8_000_000

HEADER_ALIASES = {
    "code": ["code", "biomarker", "biomarker_code", "test", "test_code", "analyte"],
    "name": ["name", "biomarker_name", "test_name", "analyte_name"],
    "value": ["value", "result", "result_value", "measurement"],
    "unit": ["unit", "units", "result_unit"],
    "date": ["date", "measured_at", "measurement_date", "collection_date", "reported_at"],
    "ref_low": ["ref_low", "reference_low", "low", "range_low"],
    "ref_high": ["ref_high", "reference_high", "high", "range_high"],
    "ref_text": ["ref_text", "reference", "reference_range", "range"],
    "source": ["source", "laboratory", "lab"],
    "method": ["method", "assay"],
    "notes": ["notes", "comment"],
}

NAME_ALIASES = {
    "alanine aminotransferase": "alt",
    "alt": "alt",
    "sgpt": "alt",
    "aspartate aminotransferase": "ast",
    "ast": "ast",
    "sgot": "ast",
    "alkaline phosphatase": "alp",
    "alk phos": "alp",
    "alp": "alp",
    "gamma glutamyl transferase": "ggt",
    "gamma-glutamyl transferase": "ggt",
    "ggt": "ggt",
    "total bilirubin": "bilirubin",
    "bilirubin": "bilirubin",
    "albumin": "albumin",
    "creatinine": "creatinine",
    "egfr": "egfr",
    "estimated gfr": "egfr",
    "blood urea nitrogen": "bun",
    "bun": "bun",
    "cystatin c": "cystatin_c",
    "urine albumin to creatinine ratio": "urine_acr",
    "urine albumin-creatinine ratio": "urine_acr",
    "glucose": "glucose",
    "fasting glucose": "glucose",
    "hemoglobin a1c": "hba1c",
    "hba1c": "hba1c",
    "a1c": "hba1c",
    "insulin": "insulin",
    "total cholesterol": "total_cholesterol",
    "cholesterol": "total_cholesterol",
    "ldl cholesterol": "ldl",
    "ldl": "ldl",
    "ldl-c": "ldl",
    "hdl cholesterol": "hdl",
    "hdl": "hdl",
    "triglycerides": "triglycerides",
    "apolipoprotein b": "apoB",
    "apob": "apoB",
    "high sensitivity crp": "hs_crp",
    "hs-crp": "hs_crp",
    "hscrp": "hs_crp",
    "c-reactive protein": "hs_crp",
    "crp": "hs_crp",
    "esr": "esr",
    "erythrocyte sedimentation rate": "esr",
    "hemoglobin": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "hgb": "hemoglobin",
    "hematocrit": "hematocrit",
    "white blood cell count": "wbc",
    "wbc": "wbc",
    "red blood cell count": "rbc",
    "rbc": "rbc",
    "platelets": "platelets",
    "platelet count": "platelets",
    "ferritin": "ferritin",
    "tsh": "tsh",
    "thyroid stimulating hormone": "tsh",
    "free t4": "free_t4",
    "free thyroxine": "free_t4",
    "free t3": "free_t3",
    "testosterone": "testosterone",
    "estradiol": "estradiol",
    "cortisol": "cortisol",
    "vitamin d": "vitamin_d",
    "25-hydroxyvitamin d": "vitamin_d",
    "vitamin b12": "vitamin_b12",
    "b12": "vitamin_b12",
    "sodium": "sodium",
    "potassium": "potassium",
    "calcium": "calcium",
    "magnesium": "magnesium",
}


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _parse_datetime(value: str) -> datetime | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    attempts = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y",
        "%b %d %Y",
    ]
    for fmt in attempts:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


def _parse_ref_range(text: str) -> tuple[float | None, float | None]:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None, None
    low, high = float(match.group(1)), float(match.group(2))
    if low >= high:
        return None, None
    return low, high


def _resolve_code(db: Session, raw_code: str | None, raw_name: str | None) -> str | None:
    candidates = [raw_code, raw_name]
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = candidate.strip()
        if not cleaned:
            continue
        direct = db.scalar(select(Biomarker).where(Biomarker.code == cleaned))
        if direct:
            return direct.code
        mapped = NAME_ALIASES.get(_norm(cleaned))
        if mapped:
            return mapped
        by_name = db.scalar(select(Biomarker).where(Biomarker.name.ilike(cleaned)))
        if by_name:
            return by_name.code
    return None


def _make_lab(
    db: Session,
    row: dict[str, str],
    *,
    default_source: str,
) -> tuple[LabCreate | None, str | None]:
    code = _resolve_code(db, row.get("code"), row.get("name"))
    if not code:
        return None, f"Unknown biomarker '{row.get('name') or row.get('code')}'."
    value = row.get("value", "").strip().replace(",", "")
    if not value or re.match(r"^[<>]", value):
        return None, f"{code}: a numeric value is required (got '{row.get('value', '')}')."
    try:
        numeric = float(value)
    except ValueError:
        return None, f"{code}: value '{row.get('value')}' is not numeric."
    unit = (row.get("unit") or "").strip()
    if not unit:
        return None, f"{code}: unit is missing. POLIS does not assume a unit."
    measured = _parse_datetime(row.get("date", ""))
    if not measured:
        return None, f"{code}: measurement date is missing or not ISO-formatted."
    ref_low = row.get("ref_low", "").strip()
    ref_high = row.get("ref_high", "").strip()
    ref_text = row.get("ref_text", "").strip()
    try:
        low = float(ref_low) if ref_low else None
        high = float(ref_high) if ref_high else None
    except ValueError:
        low, high = _parse_ref_range(ref_text)
    if low is None and high is None and ref_text:
        low, high = _parse_ref_range(ref_text)
    try:
        payload = LabCreate(
            code=code,
            value=numeric,
            unit=unit,
            measured_at=measured,
            ref_low=low,
            ref_high=high,
            ref_text=ref_text or (f"{low}–{high}" if low is not None and high is not None else None),
            source=(row.get("source") or default_source).strip()[:160],
            method=(row.get("method") or None),
            notes=(row.get("notes") or None),
        )
    except Exception as exc:
        return None, f"{code}: {exc}"
    return payload, None


def parse_csv(db: Session, content: bytes, filename: str) -> tuple[list[LabCreate], list[str], list[str]]:
    if len(content) > MAX_CSV_BYTES:
        return [], [f"CSV exceeds the {MAX_CSV_BYTES // 1_000_000} MB MVP limit."], []
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["CSV must be UTF-8 encoded."], []
    sample = text[:4096]
    delimiter = ","
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        pass
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        return [], ["CSV has no header row."], []
    mapping: dict[str, str] = {}
    normalized_headers = {_norm(header): header for header in reader.fieldnames if header}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if _norm(alias) in normalized_headers:
                mapping[canonical] = normalized_headers[_norm(alias)]
                break
    if "value" not in mapping or ("code" not in mapping and "name" not in mapping):
        return [], ["CSV needs value and biomarker code/name columns (and a unit and date)."], []
    if "unit" not in mapping:
        return [], ["CSV needs a unit column. POLIS never guesses units."], []
    if "date" not in mapping:
        return [], ["CSV needs a measurement date column. POLIS never guesses dates."], []

    accepted: list[LabCreate] = []
    errors: list[str] = []
    warnings: list[str] = []
    for index, raw in enumerate(reader, start=2):
        if index > 5002:
            errors.append("Import limited to 5,000 rows.")
            break
        if not raw or all(not (value or "").strip() for value in raw.values()):
            continue
        row = {canonical: (raw.get(header) or "").strip() for canonical, header in mapping.items()}
        payload, error = _make_lab(db, row, default_source=f"CSV upload: {filename}")
        if error:
            errors.append(f"Row {index}: {error}")
            continue
        accepted.append(payload)
    if len(accepted) > 1000:
        warnings.append("Large import: results are marked unverified and should be reviewed before interpretation.")
    return accepted, errors, warnings


def parse_fhir(db: Session, content: bytes, filename: str) -> tuple[list[LabCreate], list[str], list[str]]:
    if len(content) > MAX_FHIR_BYTES:
        return [], [f"FHIR JSON exceeds the {MAX_FHIR_BYTES // 1_000_000} MB limit."], []
    try:
        document = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], ["FHIR import must be valid UTF-8 JSON."], []
    resources: list[dict] = []
    if document.get("resourceType") == "Bundle":
        resources = [entry.get("resource", {}) for entry in document.get("entry", []) if entry.get("resource")]
    elif document.get("resourceType") == "Observation":
        resources = [document]
    else:
        return [], ["Expected a FHIR Bundle or Observation resource."], []

    accepted: list[LabCreate] = []
    errors: list[str] = []
    warnings: list[str] = []
    subjects: set[str] = set()
    for resource in resources:
        if resource.get("resourceType") != "Observation":
            continue
        subject = (resource.get("subject") or {}).get("reference")
        if subject:
            subjects.add(subject)
        codings = (resource.get("code") or {}).get("coding") or []
        code = codings[0].get("code") if codings else None
        display = codings[0].get("display") if codings else None
        resolved = _resolve_code(db, code, display or (resource.get("code") or {}).get("text"))
        if not resolved:
            warnings.append(f"Skipped Observation with unknown code '{code or display}'.")
            continue
        quantity = resource.get("valueQuantity") or {}
        value = quantity.get("value")
        unit = quantity.get("unit") or quantity.get("code")
        if value is None or not unit:
            warnings.append(f"Skipped {resolved}: no numeric valueQuantity with unit.")
            continue
        measured_raw = resource.get("effectiveDateTime") or (resource.get("effectivePeriod") or {}).get("start")
        measured = _parse_datetime(str(measured_raw)) if measured_raw else None
        if not measured:
            errors.append(f"Skipped {resolved}: no usable effective date.")
            continue
        references = (resource.get("referenceRange") or [{}])[0]
        low = (references.get("low") or {}).get("value")
        high = (references.get("high") or {}).get("value")
        low_unit = (references.get("low") or {}).get("unit")
        high_unit = (references.get("high") or {}).get("unit")
        ref_text = references.get("text")
        if (low_unit and low_unit != unit) or (high_unit and high_unit != unit):
            # Do not convert reference units silently; retain only the text.
            low = None
            high = None
            ref_text = ref_text or "FHIR reference range units differed from the observation unit; not imported as numeric interval"
            warnings.append(f"{resolved}: reference range units differ; numeric interval not imported.")
        try:
            payload = LabCreate(
                code=resolved,
                value=float(value),
                unit=unit,
                measured_at=measured,
                ref_low=float(low) if low is not None else None,
                ref_high=float(high) if high is not None else None,
                ref_text=ref_text,
                source=f"FHIR import: {filename}",
                method=None,
                notes=resource.get("note", [{}])[0].get("text") if resource.get("note") else None,
            )
            accepted.append(payload)
        except (ValueError, TypeError) as exc:
            errors.append(f"Skipped {resolved}: invalid FHIR value ({exc}).")
    if len(subjects) > 1:
        warnings.append("The FHIR Bundle contains observations for multiple subject references. Only import data you are authorised to use.")
    warnings.append("FHIR imports are marked unverified. POLIS has not validated the source system or patient identity matching.")
    return accepted, errors, warnings


LEGACY_PDF_PATTERN = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 ()\-/]{1,45}?)\s+"
    r"(?P<value>-?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[A-Za-zµμ%][A-Za-z0-9µμ%./^²³\-]*)?\s*"
    r"(?:\(?\s*(?P<low>\d+(?:\.\d+)?)\s*[-–]\s*(?P<high>\d+(?:\.\d+)?)\s*\)?)?\s*$"
)
DATE_PATTERN = re.compile(r"(20\d{2}[-/]\d{2}[-/]\d{2}|\d{2}\s+[A-Z][a-z]{2}\s+20\d{2})")


def parse_pdf(db: Session, content: bytes, filename: str) -> tuple[list[LabCreate], list[str], list[str]]:
    if len(content) > MAX_PDF_BYTES:
        return [], [f"PDF exceeds the {MAX_PDF_BYTES // 1_000_000} MB MVP limit."], []
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        return [], ["PDF parsing support is not installed."], []
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages[:20])
    except Exception:
        return [], ["The PDF could not be read. It may be encrypted or corrupted."], []
    if len(text.strip()) < 10:
        return [], ["No extractable text found. Scanned or image-only PDFs require OCR, which is not enabled in this MVP. Use CSV or manual entry."], []

    date_match = DATE_PATTERN.search(text)
    measured = _parse_datetime(date_match.group(1)) if date_match else None
    accepted: list[LabCreate] = []
    errors: list[str] = []
    warnings: list[str] = []
    if not measured:
        return [], ["A report date was not found in the PDF text. POLIS does not guess a measurement date; use manual entry or a CSV with an explicit date."], []

    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) < 5 or not any(char.isdigit() for char in cleaned):
            continue
        match = LEGACY_PDF_PATTERN.match(cleaned)
        if not match:
            continue
        name = match.group("name").strip()
        code = _resolve_code(db, None, name)
        if not code:
            continue
        unit = match.group("unit")
        if not unit:
            continue
        value = float(match.group("value"))
        low = float(match.group("low")) if match.group("low") else None
        high = float(match.group("high")) if match.group("high") else None
        try:
            accepted.append(
                LabCreate(
                    code=code,
                    value=value,
                    unit=unit,
                    measured_at=measured,
                    ref_low=low,
                    ref_high=high,
                    ref_text=f"{low}–{high}" if low is not None and high is not None else None,
                    source=f"PDF upload: {filename}",
                    method=None,
                    notes="Auto-extracted from PDF text; verify against the original report.",
                )
            )
        except (ValueError, TypeError):
            errors.append(f"Could not validate extracted {name} value.")
    if not accepted:
        return [], ["No structured biomarker rows could be extracted. Scanned PDFs and complex layouts are not reliably parsed; use CSV or manual entry."], warnings
    warnings.append("PDF extraction is heuristic. Every imported value is marked needs_review; verify unit, date, and interval against the original report.")
    return accepted, errors, warnings
