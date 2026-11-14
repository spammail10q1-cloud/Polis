"""POLIS AI: grounded health-data explanation.

The deterministic engine is the default. It classifies the question, assembles
facts from the user's own records, retrieves a curated evidence set, and
composes an answer with citations and explicit unknowns. It never invents lab
values, variants, interactions or citations. An optional external LLM may
rewrite prose over the same context, with strict validation and fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.biology import PATHWAYS, SYSTEMS
from app.models import HealthProfile, Medication, PharmacogenomicPhenotype, User, WearableMeasurement
from app.schemas import AnswerBlock, AssistantAnswer, ChatTurn
from app.services import evidence as evidence_service
from app.services import llm
from app.services.drugs import active_exposures, search
from app.services.insights import build_insights
from app.services.labs import _aware, build_trends, latest_by_code
from app.services.pgx import GENE_INFO, phenotype_map
from app.services.twin import build_overview, wearable_averages

DISCLAIMER = (
    "POLIS AI explains recorded data and retrieved evidence. It is not a clinician, does not provide a diagnosis, "
    "does not prescribe or change medicines, and cannot rule out serious illness. For urgent symptoms, "
    "contact local emergency services."
)
SYNTHETIC_NOTICE = "This is a demonstration profile. All personal health data shown are synthetic and are not real patient information."

BRANDS = {
    "plavix": "clopidogrel",
    "lopressor": "metoprolol",
    "toprol": "metoprolol",
    "prilosec": "omeprazole",
    "zocor": "simvastatin",
    "lipitor": "atorvastatin",
    "coumadin": "warfarin",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "prograf": "tacrolimus",
    "diflucan": "fluconazole",
    "paxil": "paroxetine",
    "biaxin": "clarithromycin",
    "rifadin": "rifampin",
    "imuran": "azathioprine",
    "synthroid": "levothyroxine",
    "tylenol": None,
}

LIVER_CODES = ["alt", "ast", "alp", "ggt", "bilirubin", "albumin"]
KIDNEY_CODES = ["creatinine", "egfr", "bun", "cystatin_c", "urine_acr"]
LIPID_CODES = ["total_cholesterol", "ldl", "hdl", "triglycerides", "apoB"]

EMERGENCY_RE = re.compile(
    r"(chest pain|crushing chest|can'?t breathe|cannot breathe|severe bleeding|anaphylaxis|"
    r"throat (is )?swelling|face droop|slurred speech|suicid|kill myself|end my life|overdose|"
    r"unconscious|passed out|stroke right now|heart attack right now)",
    re.IGNORECASE,
)
INJECTION_RE = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions|system prompt|developer message|"
    r"reveal (your )?(instructions|prompt)|jailbreak|act as a doctor)",
    re.IGNORECASE,
)
CHANGE_RE = re.compile(
    r"(should i (stop|start|take|use|skip|double|increase|decrease)|can i (stop|start|skip|increase|decrease|take)|"
    r"is it safe to (stop|skip|take)|what (is|'s)?\s*(the\s*)?dose|how much (should|do) i take|change my dose|"
    r"adjust my dose|double my dose|stop my|start taking|take an extra|\bdose\b.{0,40}\b(should|take|change|adjust|start))",
    re.IGNORECASE,
)


@dataclass
class Draft:
    intent: str
    blocks: list[AnswerBlock]
    summary: str
    followups: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    used_ids: list[str] = field(default_factory=list)
    retrieved: list[dict] = field(default_factory=list)
    context_used: list[str] = field(default_factory=list)


def _date(value: datetime | str | None) -> str:
    if not value:
        return "unknown date"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    value = _aware(value)
    age = (datetime.now(UTC) - value).days
    return f"{value.strftime('%d %b %Y')} ({age} days ago)"


def _citation_ids(selected: list[tuple]) -> list[str]:
    return [source.id for source, _score, _debug in selected]


def _select_evidence(
    retrieved: list[tuple], preferred_ids: list[str], fallback: int = 3
) -> list[tuple]:
    by_id = {source.id: (source, score, debug) for source, score, debug in retrieved}
    selected = [by_id[source_id] for source_id in preferred_ids if source_id in by_id]
    if not selected:
        selected = list(retrieved[:fallback])
    return selected[:4]


def _retrieval_payload(retrieved: list[tuple]) -> list[dict]:
    return [
        {
            "id": source.id,
            "title": source.title,
            "organization": source.organization,
            "score": round(score, 4),
            "components": debug,
            "verification_required": True,
        }
        for source, score, debug in retrieved
    ]


def _active_med_names(db: Session, user_id: str) -> list[dict]:
    return [
        {
            "name": medication.name,
            "dose": exposure.dose_text,
            "frequency": exposure.frequency,
            "reason": exposure.reason,
            "is_synthetic": exposure.is_synthetic,
        }
        for exposure, medication in active_exposures(db, user_id)
    ]


def _find_medications(db: Session, message: str) -> list[Medication]:
    text = message.lower()
    catalog = list(db.scalars(select(Medication)).all())
    matches: list[Medication] = []
    for term, med_id in BRANDS.items():
        if term in text and med_id:
            med = next((item for item in catalog if item.id == med_id), None)
            if med:
                matches.append(med)
    for medication in catalog:
        terms = {
            medication.id.lower(),
            medication.generic_name.lower(),
            medication.name.lower(),
            medication.name.lower().split()[0],
        }
        terms = {term for term in terms if len(term) >= 5}
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            matches.append(medication)
    deduped: dict[str, Medication] = {med.id: med for med in matches}
    return list(deduped.values())


def _wearable_window(db: Session, user_id: str) -> dict:
    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(WearableMeasurement.user_id == user_id)
            .order_by(WearableMeasurement.recorded_at.desc())
        ).all()
    )
    result: dict = {}
    for metric in ["sleep_duration", "hrv", "resting_hr"]:
        values = [row for row in rows if row.metric == metric]
        recent = [row.value for row in values if _aware(row.recorded_at) >= now - timedelta(days=14)]
        previous = [
            row.value
            for row in values
            if now - timedelta(days=28) <= _aware(row.recorded_at) < now - timedelta(days=14)
        ]
        if recent:
            result[metric] = {
                "recent_avg": round(sum(recent) / len(recent), 2),
                "previous_avg": round(sum(previous) / len(previous), 2) if previous else None,
                "count": len(recent),
                "unit": values[0].unit,
                "source": values[0].source,
            }
    return result


def _age(profile: HealthProfile | None) -> int | None:
    if not profile or not profile.date_of_birth:
        return None
    try:
        dob = datetime.strptime(profile.date_of_birth, "%Y-%m-%d")
    except ValueError:
        return None
    return (datetime.now(UTC).date() - dob.date()).days // 365


def _data_gaps(db: Session, user_id: str) -> list[str]:
    labs = latest_by_code(db, user_id)
    pgx = phenotype_map(db, user_id)
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))
    active = _active_med_names(db, user_id)
    gaps: list[str] = []
    if not profile:
        return ["No health profile has been created."]
    if not profile.date_of_birth:
        gaps.append("Date of birth is missing, limiting age-dependent interpretation.")
    if not profile.weight_kg:
        gaps.append("Body weight is missing, limiting anthropometric scaling.")
    if not profile.pregnancy_status:
        gaps.append("Pregnancy status is not recorded; pregnancy safety cannot be assessed.")
    if not profile.allergies:
        gaps.append("No allergy history is recorded.")
    if not active:
        gaps.append("No active medication list is recorded; interaction screening is incomplete.")
    if len(labs) < 10:
        gaps.append(f"Only {len(labs)} distinct laboratory markers are available.")
    for code in ["alt", "egfr", "hba1c", "ldl", "hs_crp"]:
        if code not in labs:
            gaps.append(f"{code.upper()} is not available.")
    if any(entry["freshness"]["stale"] for entry in []):
        pass
    expected_genes = {gene["symbol"] for gene in GENE_INFO}
    missing_genes = sorted(expected_genes - set(pgx))
    if missing_genes:
        gaps.append("No curated phenotype is available for: " + ", ".join(missing_genes) + ".")
    gaps.extend(
        [
            "No clinician- or pharmacy-confirmed medication list is connected.",
            "No home blood-pressure series is connected.",
            "No spirometry or pulmonary function testing is available.",
            "No continuous glucose monitoring is available.",
            "No microbiome, metabolomics, or proteomics data are available.",
        ]
    )
    return gaps


def _facts(db: Session, user: User) -> dict:
    labs = latest_by_code(db, user.id)
    pgx = phenotype_map(db, user.id)
    phenotype_rows = {
        row.gene: row
        for row in db.scalars(
            select(PharmacogenomicPhenotype).where(PharmacogenomicPhenotype.user_id == user.id)
        ).all()
    }
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
    meds = _active_med_names(db, user.id)
    wearables = _wearable_window(db, user.id)
    twin = build_overview(db, user.id)
    lab_facts = []
    for code, (result, biomarker) in labs.items():
        lab_facts.append(
            {
                "code": code,
                "name": biomarker.name,
                "value": result.value,
                "unit": result.unit,
                "ref_low": result.ref_low,
                "ref_high": result.ref_high,
                "measured_at": _aware(result.measured_at).isoformat(),
                "source": result.source,
                "is_synthetic": result.is_synthetic,
            }
        )
    synthetic = bool(profile and profile.is_synthetic)
    return {
        "profile": {
            "name": user.name,
            "age": _age(profile),
            "sex_at_birth": profile.sex_at_birth if profile else None,
            "conditions": profile.conditions if profile else [],
            "allergies": profile.allergies if profile else [],
            "is_synthetic": synthetic,
        },
        "latest_labs": lab_facts,
        "pharmacogenomics": [
            {
                "gene": row["gene"],
                "diplotype": row["diplotype"],
                "phenotype": row["phenotype"],
                "interpretation": row["interpretation"],
                "limitations": row["limitations"],
                "is_synthetic": row["is_synthetic"],
                "medications": phenotype_rows[row["gene"]].medications if row["gene"] in phenotype_rows else [],
            }
            for row in pgx.values()
        ],
        "active_medications": meds,
        "wearable_estimates": wearables,
        "data_completeness_percent": twin.overall_completeness,
        "synthetic": synthetic,
    }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _emergency_answer() -> Draft:
    blocks = [
        AnswerBlock(
            type="callout",
            tone="danger",
            title="This may be a medical emergency",
            text=(
                "Do not wait for POLIS. Call your local emergency number now (for example, 112 in Europe, "
                "911 in the United States) or go to the nearest emergency department. If you are with someone "
                "who is unresponsive or having difficulty breathing, call emergency services immediately."
            ),
            citations=[],
        ),
        AnswerBlock(
            type="text",
            title="If you are having thoughts of suicide",
            text=(
                "Please contact local emergency services or a crisis line right now and tell someone you trust. "
                "In the United States you can call or text 988. This app cannot provide crisis care."
            ),
            citations=[],
        ),
    ]
    return Draft(
        intent="emergency",
        blocks=blocks,
        summary="Urgent symptoms require emergency care, not an AI response.",
        followups=[],
        missing=[],
        context_used=[],
        retrieved=[],
    )


def _injection_answer() -> Draft:
    blocks = [
        AnswerBlock(
            type="callout",
            tone="warning",
            title="I can't change my safety rules",
            text=(
                "I can't act as a clinician, ignore grounding requirements, reveal internal instructions, or "
                "provide prescribing advice. I can explain your recorded data and cite trusted sources. What "
                "health question would you like to explore?"
            ),
            citations=[],
        )
    ]
    return Draft(
        intent="safety_boundary",
        blocks=blocks,
        summary="POLIS AI cannot change its safety rules or reveal internal instructions.",
        followups=[
            "Which of my genetic variants affect medication metabolism?",
            "What information is missing from my health profile?",
            "Why is my ALT trend changing?",
        ],
        context_used=[],
    )


def _liver_answer(db: Session, user: User, message: str) -> Draft:
    labs = latest_by_code(db, user.id)
    trends = {trend.code: trend for trend in build_trends(db, user.id)}
    retrieved = evidence_service.retrieve(
        db,
        "abnormal liver chemistries ALT AST ALP bilirubin evaluation reference interval",
        tags=["liver", "ALT", "ACG"],
        limit=5,
    )
    selected = _select_evidence(retrieved, ["acg-liver-chemistries-2017"], fallback=2)
    citation_ids = _citation_ids(selected)
    rows = []
    for code, (result, biomarker) in labs.items():
        if code not in LIVER_CODES:
            continue
        status = "normal"
        if result.ref_high is not None and result.value > result.ref_high:
            status = "above interval"
        elif result.ref_low is not None and result.value < result.ref_low:
            status = "below interval"
        elif result.ref_low is None and result.ref_high is None:
            status = "no interval"
        rows.append(
            {
                "Marker": biomarker.name,
                "Latest": f"{result.value:g} {result.unit}",
                "Laboratory interval": f"{result.ref_low if result.ref_low is not None else 'Not available'}–{result.ref_high if result.ref_high is not None else 'Not available'}",
                "Status": status,
                "Measured": _date(result.measured_at),
            }
        )
    alt_trend = trends.get("alt")
    alt_text = ""
    alt = labs.get("alt")
    if alt:
        result, _ = alt
        alt_text = (
            f"Your latest ALT is {result.value:g} {result.unit} on {_date(result.measured_at)}. "
            f"The reporting laboratory interval is {result.ref_low}–{result.ref_high} {result.unit}. "
        )
        if alt_trend and alt_trend.previous is not None and alt_trend.absolute_change is not None:
            direction = "increased" if alt_trend.absolute_change > 0 else "decreased"
            alt_text += (
                f"Across {len(alt_trend.points)} recorded measurements, the latest ALT {direction} by "
                f"{abs(alt_trend.absolute_change):g} {alt_trend.unit} compared with the previous result."
            )
    blocks = [
        AnswerBlock(
            type="text",
            title="What the recorded liver markers show",
            text=(
                alt_text
                + " ALT is a hepatocellular enzyme. The result is above this laboratory's interval, but a single "
                "value does not diagnose liver disease or identify a cause."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(
            type="table",
            title="Latest liver chemistry panel",
            rows=rows,
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="What could influence a change like this",
            items=[
                "Many medicines can affect liver enzymes, but a temporal association does not prove causation.",
                "Alcohol intake, metabolic factors, recent viral illness, and muscle injury can influence ALT and AST.",
                "Laboratory assay changes and biological variation can move results without a change in health.",
                "This profile's synthetic data show a modest rise over several months; it does not establish a cause or a diagnosis.",
            ],
            citations=citation_ids,
        ),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="What POLIS cannot determine",
            text=(
                "There is no imaging, viral hepatitis serology, autoimmune marker, fibrosis assessment, or "
                "clinician examination in this profile. POLIS cannot tell you why the ALT is elevated, whether "
                "a medicine is responsible, or whether you should change any treatment. Bring these results to a "
                "qualified clinician for evaluation."
            ),
            citations=citation_ids,
        ),
    ]
    gaps = [
        "No liver imaging, fibrosis assessment, or hepatology evaluation.",
        "No viral hepatitis serology or autoimmune liver markers.",
        "No structured alcohol or medication-adherence history beyond self-report.",
    ]
    return Draft(
        intent="liver_alt",
        blocks=blocks,
        summary=(
            f"Your latest ALT is {alt[0].value:g} {alt[0].unit}, above the laboratory interval. This is an observation, "
            "not a diagnosis; the available data cannot establish a cause."
            if alt
            else "No liver chemistry results are available in this profile."
        ),
        followups=[
            "What should I ask my doctor about these liver results?",
            "Which of my current medications are processed by the liver?",
            "What information is missing from my health profile?",
        ],
        missing=gaps,
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Latest laboratory results", "Liver marker trend", "Synthetic demonstration profile"],
    )


def _trend_answer(db: Session, user: User) -> Draft:
    trends = build_trends(db, user.id)
    repeated = [trend for trend in trends if len(trend.points) > 1]
    rows = []
    for trend in trends:
        latest_point = trend.points[-1]
        previous_point = trend.points[-2] if len(trend.points) > 1 else None
        rows.append(
            {
                "Marker": trend.name,
                "Previous": f"{previous_point.value:g} {trend.unit}" if previous_point else "No prior value",
                "Latest": f"{trend.latest:g} {trend.unit}" if trend.latest is not None else "Not available",
                "Change": f"{trend.absolute_change:+g} {trend.unit}" if trend.absolute_change is not None else "Not available",
                "Latest date": latest_point.date.strftime("%d %b %Y"),
                "Laboratory interval": f"{latest_point.ref_low if latest_point.ref_low is not None else 'Not available'}–{latest_point.ref_high if latest_point.ref_high is not None else 'Not available'}",
            }
        )
    retrieved = evidence_service.retrieve(
        db,
        "laboratory trend reference interval interpretation liver cholesterol",
        tags=["liver", "cholesterol", "guideline"],
        limit=5,
    )
    selected = _select_evidence(
        retrieved, ["acg-liver-chemistries-2017", "aha-acc-cholesterol-2018"], fallback=2
    )
    citation_ids = _citation_ids(selected)
    blocks = [
        AnswerBlock(
            type="text",
            title="Comparison of your latest and previous results",
            text=(
                f"{len(repeated)} biomarkers have more than one recorded measurement. The table compares the two most "
                "recent values. Reference intervals are laboratory-specific; POLIS does not merge values across "
                "different laboratories or units."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="table", title="Latest recorded changes", rows=rows, citations=citation_ids),
        AnswerBlock(
            type="callout",
            tone="info",
            title="Trends are not causality",
            text=(
                "A change over time can reflect biological variation, assay variation, treatment, lifestyle, or illness. "
                "A trend alone cannot establish what caused it. The intervals shown belong to the reporting laboratory "
                "for each result."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="compare_labs",
        blocks=blocks,
        summary=f"Compared {len(trends)} laboratory markers with available history; {len(repeated)} have at least two measurements.",
        followups=[
            "Why is my ALT higher than last time?",
            "What should I ask my doctor about these results?",
            "Which measurements are missing a trend?",
        ],
        missing=["Some markers have only one measurement, so no trend can be inferred."],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["All synthetic laboratory results", "Laboratory-specific reference intervals"],
    )


def _genetics_answer(db: Session, user: User) -> Draft:
    pgx = phenotype_map(db, user.id)
    from app.models import PharmacogenomicPhenotype

    rows_raw = list(
        db.scalars(
            select(PharmacogenomicPhenotype)
            .where(PharmacogenomicPhenotype.user_id == user.id)
            .order_by(PharmacogenomicPhenotype.gene)
        ).all()
    )
    table_rows = []
    bullets = []
    for row in rows_raw:
        relevant = [med["name"] for med in row.medications][:3]
        table_rows.append(
            {
                "Gene": row.gene,
                "Diplotype": row.diplotype,
                "Phenotype": row.phenotype,
                "Evidence": row.evidence_level,
                "Medication context": ", ".join(relevant) or "None listed",
            }
        )
        bullets.append(
            f"{row.gene}: {row.phenotype} ({row.diplotype}). Relevant medicines include {', '.join(relevant) or 'none listed'}."
        )
    retrieved = evidence_service.retrieve(
        db,
        "CYP2D6 CYP2C19 CYP2C9 SLCO1B1 TPMT DPYD UGT1A1 pharmacogenomic phenotype CPIC PharmVar",
        tags=["CYP2D6", "CYP2C19", "pharmacogenomics", "CPIC", "PharmVar"],
        limit=6,
    )
    selected = _select_evidence(
        retrieved,
        ["pharmvar-cyp2d6", "cpic-cyp2c19-phenotypes", "cpic-gene-drug-index"],
        fallback=3,
    )
    citation_ids = _citation_ids(selected)
    gaps = [
        "The synthetic panel reports curated diplotypes; it is not an accredited clinical test.",
        "CYP2D6 copy-number variation, hybrid genes, and rare alleles were not independently assayed.",
        "No phenotype is available for genes outside the curated panel.",
        "Genotype does not capture drug dose, interactions, organ function, adherence, or clinical context.",
    ]
    blocks = [
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Synthetic pharmacogenomic demonstration",
            text=(
                "These are curated synthetic results created for the POLIS demo. They are not a clinical genetic "
                "test and must never be used to make medication decisions. A clinical result requires an accredited "
                "laboratory and professional interpretation."
            ),
            citations=[],
        ),
        AnswerBlock(
            type="text",
            title="How to read these results",
            text=(
                f"{len(rows_raw)} pharmacogenes have a curated interpretation. A phenotype such as 'intermediate "
                "metabolizer' describes predicted enzyme function from a diplotype; it is not a measurement of enzyme "
                "activity and not a diagnosis. Relevance depends on the specific medicine, dose, interactions, and "
                "organ function."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(
            type="table",
            title="Curated pharmacogenomic phenotypes",
            rows=table_rows,
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="Medication-relevant highlights",
            items=[
                "CYP2C19 *1/*2 (intermediate) is relevant to clopidogrel activation and to proton-pump inhibitor exposure.",
                "CYP2D6 *1/*4 (intermediate) is relevant to metoprolol and other CYP2D6 substrates.",
                "SLCO1B1 *1/*5 (decreased function) has its strongest statin evidence for simvastatin; the current statin is atorvastatin.",
                "TPMT *1/*3A and UGT1A1 *1/*28 are relevant only in specific specialist contexts; no simulation is offered.",
            ],
            citations=citation_ids,
        ),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Limitations",
            text=" ".join(gaps),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="genetics",
        blocks=blocks,
        summary=(
            f"The demonstration profile has curated phenotypes for {len(rows_raw)} pharmacogenes. "
            "CYP2C19 and CYP2D6 are intermediate metabolizers, and SLCO1B1 is decreased function. "
            "These are synthetic results, not clinical findings."
        ),
        followups=[
            "Which of my genetic variants are relevant to my current medications?",
            "What would a clinician need before using a pharmacogenomic result?",
            "Is clopidogrel relevant to my CYP2C19 result?",
        ],
        missing=gaps,
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Curated synthetic pharmacogenomic panel", "Variant annotations", "Phenotype limitations"],
    )


def _medication_answer(db: Session, user: User, medication: Medication, question: str) -> Draft:
    pgx = phenotype_map(db, user.id)
    labs = latest_by_code(db, user.id)
    active = active_exposures(db, user.id)
    active_ids = {med.id for _exposure, med in active}
    from app.services.drugs import interaction_pairs_for_medication

    interactions = interaction_pairs_for_medication(db, user.id, medication.id)
    relevant_genes = [pathway.get("gene") for pathway in medication.enzyme_pathways if pathway.get("gene")]
    retrieved = evidence_service.retrieve(
        db,
        f"{medication.name} {' '.join(relevant_genes)} mechanism metabolism absorption distribution elimination",
        tags=[medication.id, *relevant_genes, "drug metabolism"],
        limit=6,
    )
    selected = _select_evidence(retrieved, medication.evidence_refs, fallback=3)
    citation_ids = _citation_ids(selected)
    gene_lines = []
    for gene in relevant_genes:
        row = pgx.get(gene)
        if row:
            gene_lines.append(f"{gene}: {row['phenotype']} ({row['diplotype']}); this is synthetic curated data and an illustrative activity factor is used in What If?.")
        else:
            gene_lines.append(f"{gene}: no curated phenotype available. POLIS would treat this as unknown, not normal.")
    if not gene_lines:
        gene_lines.append("No pharmacogene in the curated panel is a major pathway for this medicine.")
    interaction_lines = [
        f"{item['other_medication']}: {item['severity']}: {item['effect']} ({item['source_title']})"
        for item in interactions
    ] or ["No curated interaction was detected with the current synthetic medication list. Absence of a flag is not proof of safety."]
    alt = labs.get("alt")
    egfr = labs.get("egfr")
    kidney_line = (
        f"Laboratory eGFR is {egfr[0].value:g} {egfr[0].unit} ({_date(egfr[0].measured_at)})."
        if egfr
        else "No eGFR is available."
    )
    liver_line = (
        f"Latest ALT is {alt[0].value:g} {alt[0].unit} ({_date(alt[0].measured_at)}), laboratory interval {alt[0].ref_low}–{alt[0].ref_high}."
        if alt
        else "No ALT is available."
    )
    route_text = ", ".join(medication.route_options) or "not specified"
    blocks = [
        AnswerBlock(
            type="text",
            title=f"How {medication.name} is handled by the body",
            text=medication.mechanism_summary,
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="ADME at a high level",
            items=[
                f"Absorption: administered by {route_text} route. Formulation-specific absorption is not modeled.",
                f"Distribution: systemic distribution depends on protein binding, tissue perfusion, and transporters; POLIS does not have person-specific values for these.",
                f"Metabolism: {', '.join(pathway.get('role', 'metabolism') for pathway in medication.enzyme_pathways) or 'no major curated CYP pathway'}.",
                f"Elimination: renal fraction of clearance is {medication.renal_fraction if medication.renal_fraction is not None else 'not specified'}; {kidney_line}",
                f"Liver context: {liver_line}",
            ],
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="Your pharmacogenomic context",
            items=gene_lines,
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="Interaction signals requiring professional review",
            items=interaction_lines,
            citations=citation_ids,
        ),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="What this does not mean",
            text=(
                "This explanation does not tell you whether the medicine is effective or safe for you, and it does "
                "not recommend a dose. "
                + (
                    "A formal simulation is available in the What If? workspace, where uncertainty and missing data are shown explicitly. "
                    if medication.is_simulation_eligible
                    else "POLIS deliberately does not simulate this medicine because a simplified model could mislead."
                )
                + " Any decision about starting, stopping, or changing a medicine belongs with a qualified clinician or pharmacist."
            ),
            citations=citation_ids,
        ),
    ]
    current = medication.id in active_ids
    summary = (
        f"{medication.name}: {medication.drug_class}. "
        + ("Listed as a current medication. " if current else "Not listed as a current medication. ")
        + f"{len(interactions)} curated interaction signal(s) were found with the recorded active medications."
    )
    return Draft(
        intent="medication_mechanism",
        blocks=blocks,
        summary=summary,
        followups=[
            f"What would the What If? simulation use for {medication.name}?",
            "What should I ask my pharmacist about this medicine?",
            "Which of my current medications are CYP substrates or inhibitors?",
        ],
        missing=[
            "No measured drug concentrations are available.",
            "Protein binding, transporter activity, and pharmacodynamic response are not measured.",
            "The medication list is self-reported synthetic data and has not been confirmed by a pharmacy.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=[
            "Curated drug mechanism and labeling",
            "Synthetic pharmacogenomic panel",
            "Latest liver and kidney markers",
            "Active synthetic medication list",
        ],
    )


def _what_if_answer(db: Session, user: User, medication: Medication | None) -> Draft:
    if not medication:
        return Draft(
            intent="what_if",
            blocks=[
                AnswerBlock(
                    type="text",
                    title="Which medicine would you like to explore?",
                    text=(
                        "The What If? workspace can examine a curated set of medicines using your synthetic genetics, "
                        "liver markers, kidney function, current medication list, and retrieved evidence. Tell me the "
                        "medicine name or choose it directly in What If?. It will not calculate a dose or predict a clinical outcome."
                    ),
                    citations=[],
                ),
                AnswerBlock(
                    type="bullets",
                    title="Supported demonstration medicines",
                    items=[
                        "Metoprolol: CYP2D6 substrate",
                        "Omeprazole: CYP2C19 substrate and inhibitor",
                        "Clopidogrel: CYP2C19-dependent prodrug (pathway index only)",
                        "Simvastatin: CYP3A4 and SLCO1B1 context",
                        "Warfarin: CYP2C9 context, PK only; no INR prediction",
                        "Tacrolimus: CYP3A5/CYP3A4 context, PK only",
                        "Ibuprofen, fluconazole, paroxetine, clarithromycin, rifampin",
                    ],
                    citations=[],
                ),
            ],
            summary="A medicine is needed before a What If? analysis can begin.",
            followups=["What if I take clopidogrel?", "What if I take simvastatin?", "Why doesn't POLIS simulate azathioprine?"],
            missing=[],
            context_used=[],
        )
    relevant_genes = [pathway.get("gene") for pathway in medication.enzyme_pathways if pathway.get("gene")]
    retrieved = evidence_service.retrieve(
        db,
        f"{medication.name} simulation pharmacokinetics pharmacogenomics evidence uncertainty",
        tags=[medication.id, *relevant_genes],
        limit=5,
    )
    selected = _select_evidence(retrieved, medication.evidence_refs, fallback=3)
    citation_ids = _citation_ids(selected)
    pgx = phenotype_map(db, user.id)
    pgx_lines = [
        f"{gene}: {pgx[gene]['phenotype']} ({pgx[gene]['diplotype']})"
        for gene in relevant_genes
        if gene in pgx
    ]
    blocks = [
        AnswerBlock(
            type="text",
            title=f"What If?: {medication.name}",
            text=(
                f"{medication.name} is a {medication.drug_class}. "
                + (
                    "POLIS can run an experimental pathway index for this prodrug, but it cannot predict antiplatelet effect or bleeding risk. "
                    if medication.simulation_model == "pathway_index"
                    else "POLIS can run an experimental one-compartment exposure visualization. "
                )
                + "It will not produce a dose, a target level, or a treatment recommendation."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="Personal factors the workspace would use",
            items=[
                f"Curated pharmacogenomics: {', '.join(pgx_lines) if pgx_lines else 'relevant results are unavailable and would be labelled unknown'}.",
                "Latest liver markers, with mild abnormalities explicitly not converted into a quantitative clearance claim.",
                "Latest eGFR and creatinine; missing values would be labelled population assumptions.",
                "Synthetic active medication list for curated interaction screening.",
                "Curated labeling and guideline evidence; missing information remains visible.",
            ],
            citations=citation_ids,
        ),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Experimental boundary",
            text=(
                "Open What If? to run the model. The output is an educational estimate with uncertainty bounds, not a "
                "clinical prediction. No simulation can replace professional review, and some medicines are intentionally not simulated."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="what_if",
        blocks=blocks,
        summary=f"What If? can run an experimental {medication.simulation_model.replace('_', ' ')} analysis for {medication.name}, with explicit uncertainty and missing data.",
        followups=[
            f"What interactions does {medication.name} have with my current medicines?",
            f"How does my body process {medication.name}?",
            "What information is missing for this simulation?",
        ],
        missing=[
            "No measured drug concentrations are available.",
            "No clinical outcome data (e.g., INR, platelet function, blood pressure) are available.",
            "The What If? model is experimental and not clinically validated.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Medication catalog", "Synthetic pharmacogenomics", "Synthetic laboratory data", "Curated evidence"],
    )


def _change_answer(db: Session, user: User, message: str) -> Draft:
    meds = _find_medications(db, message)
    med = meds[0] if meds else None
    retrieved = evidence_service.retrieve(
        db,
        "medication safety pharmacist review stopping changing dose prescriber",
        tags=["pharmacogenomics", "drug interaction"],
        limit=4,
    )
    selected = _select_evidence(retrieved, [], fallback=2)
    citation_ids = _citation_ids(selected)
    if med:
        med_context = f"This question mentions {med.name}."
        interactions = __import__("app.services.drugs", fromlist=["interaction_pairs_for_medication"]).interaction_pairs_for_medication(db, user.id, med.id)
        interaction_text = (
            "Curated signals with your recorded medicines: "
            + "; ".join(f"{item['other_medication']} ({item['severity']})" for item in interactions)
            + "."
            if interactions
            else "No curated interaction was found with the recorded synthetic medicines, but absence of a flag is not proof of safety."
        )
    else:
        med_context = "I could not map the medicine in your question to the curated formulary."
        interaction_text = "POLIS would need the exact medicine name and current medication list to screen interactions."
    blocks = [
        AnswerBlock(
            type="callout",
            tone="danger",
            title="I can't advise starting, stopping, or changing a medicine",
            text=(
                "That decision requires a clinician who knows your full history, examination findings, and indication. "
                "POLIS does not prescribe, recommend a dose, or tell you to stop treatment. Do not change a medicine "
                "based on this app. For urgent side effects, seek urgent medical care."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(
            type="text",
            title="What POLIS can do",
            text=(
                f"{med_context} It can explain the medicine's biology, surface recorded pharmacogenomic and organ-function "
                "context, flag curated interactions for professional review, and help you prepare questions. "
                f"{interaction_text}"
            ),
            citations=citation_ids,
        ),
        AnswerBlock(
            type="bullets",
            title="Questions to bring to your prescriber or pharmacist",
            items=[
                "What is this medicine treating, and what outcome are we monitoring?",
                "Do my kidney function, liver markers, or genetic results change how you want to monitor me?",
                "Are any of my current medicines, supplements, or recent illnesses relevant?",
                "What side effects or warning signs should prompt urgent contact?",
                "If we change therapy, how should the transition be managed?",
            ],
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="medication_change_request",
        blocks=blocks,
        summary="POLIS cannot advise medication changes; it can provide context and questions for professional review.",
        followups=[
            "What interactions are recorded with my medicines?",
            "How is this medicine processed by my body?",
            "What should I ask my pharmacist?",
        ],
        missing=[
            "The indication, examination findings, and clinician assessment are not available to POLIS.",
            "The medication list is user-reported and synthetic in this demo.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Medication catalog", "Curated interaction evidence"],
    )


def _lipid_answer(db: Session, user: User) -> Draft:
    labs = latest_by_code(db, user.id)
    trends = {trend.code: trend for trend in build_trends(db, user.id)}
    retrieved = evidence_service.retrieve(
        db,
        "LDL cholesterol ApoB cardiovascular risk statin guideline reference interval",
        tags=["LDL", "cholesterol", "ApoB", "guideline"],
        limit=5,
    )
    selected = _select_evidence(retrieved, ["aha-acc-cholesterol-2018"], fallback=2)
    citation_ids = _citation_ids(selected)
    rows = []
    for code in LIPID_CODES:
        pair = labs.get(code)
        if not pair:
            continue
        result, biomarker = pair
        status = "above interval" if result.ref_high is not None and result.value > result.ref_high else "within/available"
        rows.append(
            {
                "Marker": biomarker.name,
                "Latest": f"{result.value:g} {result.unit}",
                "Laboratory interval": f"{result.ref_low if result.ref_low is not None else 'Not available'}–{result.ref_high if result.ref_high is not None else 'Not available'}",
                "Status": status,
                "Measured": _date(result.measured_at),
            }
        )
    ldl = labs.get("ldl")
    trend = trends.get("ldl")
    trend_text = ""
    if trend and len(trend.points) > 1:
        trend_text = (
            f" The recorded LDL series moved from {trend.points[0].value:g} to {trend.latest:g} {trend.unit}; "
            "a downward trend can reflect treatment, diet, weight change, or variation."
        )
    blocks = [
        AnswerBlock(
            type="text",
            title="Lipid context",
            text=(
                (f"The latest LDL is {ldl[0].value:g} {ldl[0].unit} against a laboratory upper limit of {ldl[0].ref_high:g} {ldl[0].unit}." if ldl and ldl[0].ref_high else "Lipid results are available.")
                + trend_text
                + " Cardiovascular risk is multifactorial; a single LDL value is not a treatment decision."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="table", title="Latest lipid panel", rows=rows, citations=citation_ids),
        AnswerBlock(
            type="callout",
            tone="info",
            title="What is not available",
            text=(
                "No 10-year atherosclerotic risk calculation, blood-pressure series, smoking exposure data beyond self-report, "
                "or clinician risk discussion is in the profile. POLIS does not set a lipid target or advise changing statin therapy."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="lipids",
        blocks=blocks,
        summary="The available lipid panel includes an LDL above the reporting laboratory interval; this is risk context, not a treatment decision.",
        followups=[
            "What should I ask my doctor about my cholesterol?",
            "How does atorvastatin work?",
            "Compare my latest blood results with the previous test.",
        ],
        missing=["No comprehensive cardiovascular risk assessment.", "No blood-pressure series or Lp(a) measurement."],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Synthetic lipid panel", "LDL trend", "Laboratory reference intervals"],
    )


def _kidney_answer(db: Session, user: User) -> Draft:
    labs = latest_by_code(db, user.id)
    trends = {trend.code: trend for trend in build_trends(db, user.id)}
    retrieved = evidence_service.retrieve(
        db,
        "eGFR creatinine cystatin C albuminuria kidney function KDIGO interpretation",
        tags=["eGFR", "kidney", "KDIGO"],
        limit=4,
    )
    selected = _select_evidence(retrieved, ["kdigo-2024-ckd"], fallback=2)
    citation_ids = _citation_ids(selected)
    rows = []
    for code in KIDNEY_CODES:
        pair = labs.get(code)
        if not pair:
            rows.append({"Marker": code, "Latest": "Not available", "Interval": "Not available", "Measured": "Not available"})
            continue
        result, biomarker = pair
        rows.append(
            {
                "Marker": biomarker.name,
                "Latest": f"{result.value:g} {result.unit}",
                "Interval": f"{result.ref_low if result.ref_low is not None else 'Not available'}–{result.ref_high if result.ref_high is not None else 'Not available'}",
                "Measured": _date(result.measured_at),
            }
        )
    egfr = labs.get("egfr")
    trend = trends.get("egfr")
    trend_text = ""
    if egfr and trend and len(trend.points) > 1:
        first = trend.points[0]
        trend_text = f" The recorded eGFR series ranges from {first.value:g} to {trend.latest:g} {trend.unit}."
    blocks = [
        AnswerBlock(
            type="text",
            title="Kidney filtration context",
            text=(
                (f"Your latest laboratory eGFR is {egfr[0].value:g} {egfr[0].unit} ({_date(egfr[0].measured_at)})." if egfr else "No eGFR result is available.")
                + trend_text
                + " eGFR is a population estimate of filtration, not a direct measurement of kidney function."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="table", title="Latest kidney markers", rows=rows, citations=citation_ids),
        AnswerBlock(
            type="callout",
            tone="info",
            title="What this does not establish",
            text=(
                "A stable eGFR does not rule out kidney disease. Albuminuria, blood pressure, medications, hydration, "
                "muscle mass, and acute illness all matter. A single value cannot diagnose or exclude kidney disease."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="kidney",
        blocks=blocks,
        summary="Kidney filtration markers are available; eGFR is a population estimate and does not by itself diagnose kidney disease.",
        followups=[
            "Which medications are cleared by the kidneys?",
            "What information is missing from my kidney assessment?",
            "What should I ask my doctor about my kidney results?",
        ],
        missing=[
            "No repeated albuminuria confirmation or blood-pressure series.",
            "No clinical assessment of hydration, muscle mass, or acute illness.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Synthetic laboratory results", "Kidney marker trends"],
    )


def _sleep_answer(db: Session, user: User) -> Draft:
    window = _wearable_window(db, user.id)
    retrieved = evidence_service.retrieve(
        db,
        "sleep duration wearable estimates adults CDC health",
        tags=["sleep", "wearables"],
        limit=4,
    )
    selected = _select_evidence(retrieved, ["cdc-sleep"], fallback=2)
    citation_ids = _citation_ids(selected)
    sleep = window.get("sleep_duration")
    hrv = window.get("hrv")
    resting = window.get("resting_hr")
    items = []
    if sleep:
        change = (
            f" The previous 14-day average was {sleep['previous_avg']:.1f} h."
            if sleep.get("previous_avg")
            else ""
        )
        items.append(f"Sleep: {sleep['recent_avg']:.1f} h per night over {sleep['count']} device-estimated nights.{change}")
    if hrv:
        items.append(f"HRV: {hrv['recent_avg']:.1f} ms (14-day device average).")
    if resting:
        items.append(f"Resting heart rate: {resting['recent_avg']:.0f} bpm (14-day device average).")
    if not items:
        items.append("No recent wearable measurements are available.")
    items.extend(
        [
            "The device is a synthetic Oura sample import. Sleep stages and HRV are proprietary estimates, not polysomnography or ECG.",
            "One short night is not a health conclusion. A persistent pattern, daytime impairment, or loud snoring with pauses should be discussed with a clinician.",
        ]
    )
    blocks = [
        AnswerBlock(
            type="text",
            title="Recent sleep and recovery estimates",
            text=(
                "These are consumer-device estimates from the last 14 days. They can show patterns but do not diagnose a sleep disorder."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="bullets", title="What the data show", items=items, citations=citation_ids),
        AnswerBlock(
            type="callout",
            tone="info",
            title="Measurement limitation",
            text=(
                "Wearable sleep staging can misclassify wake and sleep stages. No sleep diary, polysomnography, or "
                "daytime symptom data are available in this profile."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="sleep",
        blocks=blocks,
        summary="Wearable estimates show a recent sleep pattern; this is not a diagnosis or a validated sleep assessment.",
        followups=[
            "What information is missing from my health profile?",
            "Which measurements connect sleep to metabolism?",
            "How does POLIS distinguish device estimates from laboratory results?",
        ],
        missing=[
            "No sleep diary or polysomnography.",
            "No daytime symptom or screening questionnaire data.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Synthetic wearable time series", "14-day and prior-14-day averages"],
    )


def _missing_answer(db: Session, user: User) -> Draft:
    gaps = _data_gaps(db, user.id)
    twin = build_overview(db, user.id)
    full_systems = [system.name for system in twin.systems if system.status == "available"]
    partial_systems = [system.name for system in twin.systems if system.status in {"partial", "missing"}]
    blocks = [
        AnswerBlock(
            type="text",
            title="What POLIS has and does not have",
            text=(
                f"Overall data completeness across the ten body systems is {twin.overall_completeness}%. This is a "
                "coverage measure, not a health score. Systems with the most complete direct data: "
                f"{', '.join(full_systems) or 'none'}. Systems limited by missing or indirect data: "
                f"{', '.join(partial_systems) or 'none'}."
            ),
            citations=[],
        ),
        AnswerBlock(
            type="bullets",
            title="Important gaps in this demonstration profile",
            items=gaps[:14],
            citations=[],
        ),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Missing information is information",
            text=(
                "POLIS does not fill gaps with population averages without labelling them. Missing data reduce what can "
                "be concluded, and adding measurements does not automatically improve interpretation. Prioritise data "
                "that a clinician would actually use for your question."
            ),
            citations=[],
        ),
    ]
    return Draft(
        intent="missing_data",
        blocks=blocks,
        summary=f"Identified {len(gaps)} meaningful data gaps. Completeness is {twin.overall_completeness}% and is not a health score.",
        followups=[
            "Which of my genetic results have limitations?",
            "What would make a pharmacogenomic result clinically interpretable?",
            "What should I ask my doctor about these results?",
        ],
        missing=gaps,
        used_ids=[],
        retrieved=[],
        context_used=["Digital twin completeness", "Profile metadata", "Synthetic data inventory"],
    )


def _ask_doctor_answer(db: Session, user: User) -> Draft:
    insights = build_insights(db, user.id)
    pgx = phenotype_map(db, user.id)
    questions = []
    if "alt" in latest_by_code(db, user.id):
        questions.append("My ALT is above the laboratory interval and has risen over several measurements. What evaluation and follow-up do you recommend?")
    if "ldl" in latest_by_code(db, user.id):
        questions.append("My LDL is above the laboratory interval on atorvastatin. What is my cardiovascular risk context and treatment goal?")
    if "CYP2C19" in pgx:
        questions.append("My curated CYP2C19 result is intermediate metabolizer. Is that relevant to my omeprazole, and would it matter if clopidogrel were ever considered?")
    if "CYP2D6" in pgx:
        questions.append("My curated CYP2D6 result is intermediate metabolizer. Could it affect metoprolol or other medicines I take?")
    if "SLCO1B1" in pgx:
        questions.append("My SLCO1B1 result is decreased function. Is simvastatin relevant to me, and does it change how you view atorvastatin?")
    questions.extend(
        [
            "Which of these results would you want repeated, and when?",
            "What information is missing from my record that would change your assessment?",
            "What symptoms or changes should prompt me to contact you urgently?",
        ]
    )
    retrieved = evidence_service.retrieve(
        db,
        "liver cholesterol pharmacogenomics clinician discussion questions guideline",
        tags=["liver", "cholesterol", "pharmacogenomics", "guideline"],
        limit=5,
    )
    selected = _select_evidence(
        retrieved,
        ["acg-liver-chemistries-2017", "aha-acc-cholesterol-2018", "cpic-clopidogrel-2022"],
        fallback=3,
    )
    citation_ids = _citation_ids(selected)
    blocks = [
        AnswerBlock(
            type="text",
            title="Questions grounded in your recorded data",
            text=(
                "These are discussion prompts, not recommendations. They are based on the synthetic demonstration record "
                "and the limitations of the available evidence. A clinician may reasonably prioritise them differently."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="bullets", title="For your next appointment", items=questions[:8], citations=citation_ids),
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Keep clinical decisions with your care team",
            text=(
                "Do not start, stop, or change any medication based on these questions or on POLIS. Emergency symptoms "
                "require emergency services, not an appointment."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="ask_doctor",
        blocks=blocks,
        summary=f"Prepared {min(len(questions), 8)} questions based on your recorded liver, lipid, pharmacogenomic, and medication context.",
        followups=[
            "Explain my ALT result in plain language.",
            "Which of my genetic variants are relevant to my medicines?",
            "What information is missing from my health profile?",
        ],
        missing=["The clinician's examination, indication, and full history are not available to POLIS."],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=[insight.title for insight in insights[:4]] + ["Synthetic data limitations"],
    )


def _pathway_answer(db: Session, user: User) -> Draft:
    pgx = phenotype_map(db, user.id)
    labs = latest_by_code(db, user.id)
    genes = set(pgx)
    relevant_pathways = []
    for pathway in PATHWAYS:
        overlap = genes.intersection(set(pathway["genes"]))
        if overlap:
            relevant_pathways.append((pathway, sorted(overlap)))
    selected_pathways = relevant_pathways[:4]
    rows = []
    for pathway, overlap in selected_pathways:
        rows.append(
            {
                "Pathway": pathway["name"],
                "Organs/systems": ", ".join(pathway["organs"]),
                "Your genes": ", ".join(overlap) or "None listed",
                "Evidence": pathway["evidence_level"],
            }
        )
    retrieved = evidence_service.retrieve(
        db,
        "hepatic drug metabolism CYP enzymes pathways liver kidney CLOCK circadian",
        tags=["CYP2D6", "CYP2C19", "metabolism", "pharmacokinetics"],
        limit=5,
    )
    selected = _select_evidence(
        retrieved, ["pbpk-review-2013", "fda-ddi-guidance", "cpic-gene-drug-index"], fallback=3
    )
    citation_ids = _citation_ids(selected)
    blocks = [
        AnswerBlock(
            type="text",
            title="How the recorded measurements connect",
            text=(
                "POLIS uses a small curated knowledge graph of genes, enzymes, organs, biomarkers, medicines, and pathways. "
                "A connection in the graph is not proof that one measured thing caused another. The pathways below are "
                "selected because your curated genetic results participate in them."
            ),
            citations=citation_ids,
        ),
        AnswerBlock(type="table", title="Relevant biological pathways", rows=rows, citations=citation_ids),
        AnswerBlock(
            type="bullets",
            title="Concrete examples",
            items=[
                "CYP2D6 and metoprolol: the enzyme pathway affects metoprolol metabolism; genotype is one input, not a full response prediction.",
                "CYP2C19, omeprazole, and clopidogrel: omeprazole is metabolized by and inhibits CYP2C19; clopidogrel requires CYP2C19 activation.",
                "SLCO1B1 and statins: hepatic uptake transport affects simvastatin exposure more strongly than atorvastatin exposure.",
                "eGFR and renal clearance: kidney filtration scales the renal fraction of elimination for renally cleared medicines.",
            ],
            citations=citation_ids,
        ),
        AnswerBlock(
            type="callout",
            tone="info",
            title="Causal language is restricted",
            text=(
                "These are mechanistic relationships, not estimates of causal effect in you. The current graph is small, "
                "does not represent flux or tissue concentrations, and is separate from the experimental simulation."
            ),
            citations=citation_ids,
        ),
    ]
    return Draft(
        intent="pathways",
        blocks=blocks,
        summary=f"Identified {len(selected_pathways)} curated pathways connected to your synthetic pharmacogenomic results.",
        followups=[
            "How does the liver process omeprazole?",
            "Which of my lab measurements reflect kidney clearance?",
            "What information is missing to model these pathways?",
        ],
        missing=[
            "The knowledge graph is a small curated starter set, not a complete biological network.",
            "No enzyme activity, transporter flux, or tissue concentration measurements are available.",
        ],
        used_ids=citation_ids,
        retrieved=_retrieval_payload(retrieved),
        context_used=["Curated biological knowledge graph", "Synthetic pharmacogenomic results"],
    )


def _overview_answer(db: Session, user: User) -> Draft:
    insights = build_insights(db, user.id)
    lab_count = len(latest_by_code(db, user.id))
    pgx_count = len(phenotype_map(db, user.id))
    meds = _active_med_names(db, user.id)
    twin = build_overview(db, user.id)
    blocks = [
        AnswerBlock(
            type="text",
            title="A data-grounded overview",
            text=(
                f"The demonstration profile contains {lab_count} distinct laboratory markers, {pgx_count} curated "
                f"pharmacogenomic phenotypes, {len(meds)} active medications, and wearable sample data. Overall data "
                f"completeness is {twin.overall_completeness}%. POLIS intentionally does not produce an overall health "
                "score or diagnosis."
            ),
            citations=[],
        )
    ]
    top = insights[:4]
    for insight in top:
        blocks.append(
            AnswerBlock(
                type="text",
                title=insight.title,
                text=insight.summary,
                citations=[citation.id for citation in insight.sources],
            )
        )
    blocks.append(
        AnswerBlock(
            type="callout",
            tone="warning",
            title="Interpretation boundary",
            text=(
                "These observations come from synthetic data. They show what POLIS can surface, not what is true about "
                "a real person. For a specific question, ask about a marker, medicine, gene, or data gap."
            ),
            citations=[],
        )
    )
    used_ids = {citation.id for insight in top for citation in insight.sources}
    return Draft(
        intent="overview",
        blocks=blocks,
        summary=f"A high-level view of {lab_count} laboratory markers, {pgx_count} pharmacogenomic results, and {len(meds)} active medications. No health score is produced.",
        followups=[
            "Why is my ALT higher than last time?",
            "Which genetic variants affect medication metabolism?",
            "What information is missing from my profile?",
            "What if I take clopidogrel?",
        ],
        missing=["Synthetic demonstration data only.", "No clinical diagnosis or overall health score is generated."],
        used_ids=sorted(used_ids),
        retrieved=[],
        context_used=["Synthetic laboratory results", "Pharmacogenomics", "Medication list", "Wearable estimates"],
    )


def _fallback_answer(db: Session, user: User, message: str) -> Draft:
    gaps = _data_gaps(db, user.id)
    blocks = [
        AnswerBlock(
            type="text",
            title="I don't have enough information to answer that reliably",
            text=(
                "That is a valid outcome. POLIS AI only answers when it can ground the response in your recorded data "
                "and a retrieved, citable source. I will not invent a lab value, variant, interaction, citation, or "
                "clinical recommendation. I also cannot provide a diagnosis or medication advice."
            ),
            citations=[],
        ),
        AnswerBlock(
            type="bullets",
            title="Questions I can answer with this demonstration profile",
            items=[
                "Why is my ALT higher than last time?",
                "Which of my genetic variants are relevant to medication metabolism?",
                "What information is missing from my health profile?",
                "Compare my latest blood results with the previous test.",
                "What should I ask my doctor about these results?",
                "Which biological pathways connect these measurements?",
                "Explain how my body processes omeprazole or metoprolol.",
                "What if I take clopidogrel?",
            ],
            citations=[],
        ),
        AnswerBlock(
            type="callout",
            tone="info",
            title="Safety note",
            text=DISCLAIMER,
            citations=[],
        ),
    ]
    return Draft(
        intent="insufficient_information",
        blocks=blocks,
        summary="I don't have enough information to answer that reliably with grounded sources and your recorded data.",
        followups=[
            "What information is missing from my health profile?",
            "What can you tell me about my ALT result?",
            "Which genetic variants affect medication metabolism?",
        ],
        missing=gaps[:6],
        used_ids=[],
        retrieved=[],
        context_used=["Limited demonstration dataset"],
    )


# ---------------------------------------------------------------------------
# Classification and orchestration
# ---------------------------------------------------------------------------


def classify_intent(message: str, medications: list[Medication]) -> str:
    text = message.lower()
    if EMERGENCY_RE.search(text):
        return "emergency"
    if INJECTION_RE.search(text):
        return "safety_boundary"
    if CHANGE_RE.search(text):
        return "medication_change_request"
    if "what if" in text:
        return "what_if"
    if any(term in text for term in ["missing", "incomplete", "data gap", "what information", "not recorded"]):
        return "missing_data"
    if any(term in text for term in ["genetic", "variant", "dna", "pharmacogenomic", "pharmacogenetic", "metabolizer", "cyp2d6", "cyp2c19", "cyp2c9", "slco1b1", "tpmt", "dpyd", "ugt1a1"]):
        return "genetics"
    if "doctor" in text and any(term in text for term in ["ask", "question", "discuss"]):
        return "ask_doctor"
    if "pathway" in text or "connect" in text:
        return "pathways"
    if medications:
        return "medication_mechanism"
    if any(term in text for term in ["sleep", "wearable", "hrv", "recovery"]):
        return "sleep"
    if any(term in text for term in ["kidney", "renal", "egfr", "creatinine"]):
        return "kidney"
    if any(term in text for term in ["liver", "alt", "ast", "bilirubin", "alkaline phosphatase"]):
        return "liver_alt"
    if any(term in text for term in ["ldl", "cholesterol", "lipid", "triglyceride"]):
        return "lipids"
    if any(term in text for term in ["compare", "previous", "last time", "trend", "since last", "changed since"]):
        return "compare_labs"
    if any(term in text for term in ["overview", "how am i", "summary", "my health", "what do you know"]):
        return "overview"
    return "general"


def _llm_rewrite(draft: Draft, *, question: str, facts: dict, db: Session, history: list[ChatTurn] | None = None) -> Draft | None:
    if not llm.enabled():
        return None
    evidence_payload = [
        {
            "id": entry["id"],
            "title": entry["title"],
            "organization": entry["organization"],
            "published_at": entry.get("published_at"),
            "evidence_level": entry.get("evidence_level"),
            "snippet": entry.get("snippet", ""),
        }
        for entry in draft.retrieved
    ]
    if not evidence_payload:
        return None
    parsed = llm.generate_json(
        question=question,
        personal_context=facts,
        evidence=evidence_payload,
        intent=draft.intent,
        history=[{"role": turn.role, "content": turn.content} for turn in (history or [])],
    )
    if not parsed:
        return None
    raw_blocks = parsed.get("blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        return None
    allowed_ids = {entry["id"] for entry in draft.retrieved}
    blocks: list[AnswerBlock] = []
    used: list[str] = []
    try:
        for raw in raw_blocks[:8]:
            raw = dict(raw)
            citations = [cid for cid in raw.get("citations", []) if cid in allowed_ids]
            used.extend(citations)
            raw["citations"] = citations
            if raw.get("type") not in {"text", "bullets", "callout", "table"}:
                raw["type"] = "text"
            blocks.append(AnswerBlock(**raw))
    except Exception:
        return None
    if not blocks:
        return None
    answer = parsed.get("answer") if isinstance(parsed.get("answer"), str) else draft.summary
    followups = [item for item in parsed.get("follow_up_questions", []) if isinstance(item, str)][:4]
    missing = draft.missing
    return Draft(
        intent=draft.intent,
        blocks=blocks,
        summary=answer[:1200],
        followups=followups or draft.followups,
        missing=missing,
        used_ids=list(dict.fromkeys(used)),
        retrieved=draft.retrieved,
        context_used=draft.context_used + ["External model synthesis over retrieved sources (grounding validated)"],
    )


def answer_chat(db: Session, user: User, message: str, history: list[ChatTurn]) -> AssistantAnswer:
    # Resolve short follow-up questions against the previous user turn. The
    # displayed answer remains grounded in the current data; this only prevents
    # anaphoric questions such as "why?" from losing their subject.
    effective_message = message
    if history:
        previous_user = next((turn.content for turn in reversed(history) if turn.role == "user"), None)
        follow_markers = {"why", "how", "and", "what", "that", "it", "more", "explain", "really", "so"}
        words = [word.strip("?.!,").lower() for word in message.split()]
        has_domain_term = any(
            term in message.lower()
            for term in [
                "alt", "ast", "liver", "kidney", "sleep", "genetic", "cyp", "medication",
                "drug", "cholesterol", "ldl", "missing", "pathway", "doctor", "egfr",
            ]
        )
        if previous_user and len(words) <= 6 and not has_domain_term and follow_markers.intersection(words):
            effective_message = f"{previous_user} {message}"

    medications = _find_medications(db, effective_message)
    intent = classify_intent(effective_message, medications)

    if intent == "emergency":
        draft = _emergency_answer()
    elif intent == "safety_boundary":
        draft = _injection_answer()
    elif intent == "medication_change_request":
        draft = _change_answer(db, user, effective_message)
    elif intent == "what_if":
        draft = _what_if_answer(db, user, medications[0] if medications else None)
    elif intent == "missing_data":
        draft = _missing_answer(db, user)
    elif intent == "compare_labs":
        draft = _trend_answer(db, user)
    elif intent == "genetics":
        draft = _genetics_answer(db, user)
    elif intent == "ask_doctor":
        draft = _ask_doctor_answer(db, user)
    elif intent == "pathways":
        draft = _pathway_answer(db, user)
    elif intent == "sleep":
        draft = _sleep_answer(db, user)
    elif intent == "kidney":
        draft = _kidney_answer(db, user)
    elif intent == "liver_alt":
        draft = _liver_answer(db, user, effective_message)
    elif intent == "lipids":
        draft = _lipid_answer(db, user)
    elif intent == "medication_mechanism" and medications:
        draft = _medication_answer(db, user, medications[0], effective_message)
    elif intent == "overview":
        draft = _overview_answer(db, user)
    else:
        draft = _fallback_answer(db, user, effective_message)

    facts = _facts(db, user)
    if intent not in {"emergency", "safety_boundary", "medication_change_request"}:
        rewritten = _llm_rewrite(draft, question=message, facts=facts, db=db, history=history)
        if rewritten:
            draft = rewritten
            engine = "POLIS AI · grounded external model"
        else:
            engine = "POLIS AI · deterministic grounded synthesis"
    else:
        engine = "POLIS AI · safety rules"

    used_ids = list(dict.fromkeys(draft.used_ids + [cid for block in draft.blocks for cid in block.citations]))
    citations = evidence_service.citations(db, used_ids)
    known_citation_ids = {citation.id for citation in citations}
    for block in draft.blocks:
        block.citations = [cid for cid in block.citations if cid in known_citation_ids]
    used_ids = [cid for cid in used_ids if cid in known_citation_ids]

    blocks = list(draft.blocks)
    if facts.get("synthetic") and intent not in {"emergency", "safety_boundary"}:
        blocks.insert(
            0,
            AnswerBlock(
                type="callout",
                tone="info",
                title="Demonstration data",
                text=SYNTHETIC_NOTICE,
                citations=[],
            ),
        )

    return AssistantAnswer(
        answer=draft.summary,
        blocks=blocks,
        citations=citations,
        context_used=list(dict.fromkeys(draft.context_used + ["Demonstration profile (synthetic)"])),
        missing_information=list(dict.fromkeys(draft.missing)),
        follow_up_questions=draft.followups,
        engine=engine,
        intent=draft.intent,
        disclaimer=DISCLAIMER,
        evidence_retrieval=draft.retrieved,
    )


def explain_entity(db: Session, user: User, entity: str) -> AssistantAnswer:
    """Explain a biomarker, gene, medication, or system using the same grounded path."""
    query = entity.strip()
    if not query:
        return answer_chat(db, user, "What information is missing from my health profile?", [])
    return answer_chat(db, user, f"Explain {query} in my health context", [])
