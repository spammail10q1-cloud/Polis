"""Evidence-linked observations for the overview and insights pages.

These are generated from the user's own records at request time. They are
observations, not diagnoses, risk scores, or treatment recommendations.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HealthProfile
from app.schemas import InsightOut
from app.services import evidence as evidence_service
from app.services.labs import latest_by_code
from app.services.pgx import phenotype_map
from app.services.twin import wearable_averages


def _date(entry: dict | None) -> str:
    if not entry:
        return "unknown date"
    value = entry.get("measured_at")
    return value.strftime("%d %b %Y") if value else "unknown date"


def build_insights(db: Session, user_id: str) -> list[InsightOut]:
    labs = latest_by_code(db, user_id)
    pgx = phenotype_map(db, user_id)
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user_id))
    w_avg = wearable_averages(db, user_id, days=14)

    def citation_list(ids: list[str]):
        return evidence_service.citations(db, ids)

    insights: list[InsightOut] = []

    alt = labs.get("alt")
    if alt:
        result, biomarker = alt
        ref_high = result.ref_high
        percent_above = ((result.value - ref_high) / ref_high * 100) if ref_high else None
        insights.append(
            InsightOut(
                id="insight-alt-trend",
                title="ALT is above the reporting laboratory interval",
                summary=(
                    f"The latest ALT is {result.value:g} {result.unit}"
                    + (f", about {percent_above:.0f}% above the laboratory upper limit" if percent_above else "")
                    + ". Previous synthetic results in this demonstration profile show a gradual rise. "
                    "A single enzyme value is not a diagnosis and does not identify a cause."
                ),
                category="Liver",
                tone="warning",
                evidence=(
                    "The ACG guideline on abnormal liver chemistries recommends evaluating the pattern "
                    "(hepatocellular, cholestatic, or mixed) and clinical context rather than interpreting an isolated value. "
                    "ALT can be influenced by many factors, including medicines, alcohol, metabolic conditions, and transient illness."
                ),
                sources=citation_list(["acg-liver-chemistries-2017"]),
                data_basis=[
                    f"ALT {result.value:g} {result.unit} on {_date({'measured_at': result.measured_at})}",
                    f"Laboratory interval {result.ref_low}–{result.ref_high} {result.unit}",
                    f"Source: {result.source} (synthetic)",
                ],
                limitations=(
                    "The model has no imaging, viral serology, autoimmune markers, or medication-adherence data. "
                    "This observation must not be used to attribute the elevation to a medication or to stop any medicine."
                ),
            )
        )

    ldl = labs.get("ldl")
    if ldl:
        result, biomarker = ldl
        status_text = "above" if result.ref_high and result.value > result.ref_high else "within"
        insights.append(
            InsightOut(
                id="insight-lipids",
                title=f"LDL cholesterol is {status_text} the laboratory interval",
                summary=(
                    f"The latest LDL is {result.value:g} {result.unit}"
                    + (f" against a laboratory upper limit of {result.ref_high:g} {result.unit}" if result.ref_high else "")
                    + ". A trend is available in Biomarkers. Cardiovascular risk is multifactorial and is not determined by this value alone."
                ),
                category="Cardiovascular",
                tone="warning" if status_text == "above" else "info",
                evidence=(
                    "The AHA/ACC cholesterol guideline uses a risk-based approach that integrates LDL cholesterol, "
                    "other risk-enhancing factors, and clinician–patient discussion. It does not treat a single "
                    "laboratory threshold as sufficient for a medication decision."
                ),
                sources=citation_list(["aha-acc-cholesterol-2018"]),
                data_basis=[
                    f"LDL {result.value:g} {result.unit} on {_date({'measured_at': result.measured_at})}",
                    f"Laboratory upper limit {result.ref_high or 'not supplied'} {result.unit}",
                    "Statin therapy is listed as an active medication (self-reported, synthetic).",
                ],
                limitations=(
                    "No Lp(a), full risk-factor panel, blood pressure series, or 10-year risk calculation is available. "
                    "POLIS does not set lipid targets or recommend treatment changes."
                ),
            )
        )

    cyp2c19 = pgx.get("CYP2C19")
    if cyp2c19:
        insights.append(
            InsightOut(
                id="insight-cyp2c19",
                title="CYP2C19 intermediate metabolizer result has medication context",
                summary=(
                    "The synthetic curated result is CYP2C19 *1/*2, reported as intermediate metabolizer. "
                    "This is pharmacogenomic context, not a disease finding. It becomes directly relevant if clopidogrel "
                    "is being considered, particularly alongside a CYP2C19 inhibitor such as omeprazole."
                ),
                category="Pharmacogenomics",
                tone="info",
                evidence=(
                    "CPIC provides genotype-based guidance for CYP2C19 and clopidogrel: poor and intermediate metabolizers "
                    "may have reduced activation of the prodrug, and an alternative P2Y12 inhibitor may be considered when "
                    "not contraindicated. Omeprazole is listed as an active medication and inhibits CYP2C19. "
                    "Current omeprazole use is not automatically inappropriate; the relevance depends on whether clopidogrel is used or planned."
                ),
                sources=citation_list(["cpic-clopidogrel-2022", "fda-omeprazole-label"]),
                data_basis=[
                    f"CYP2C19 {cyp2c19['diplotype']} → {cyp2c19['phenotype']}",
                    "Omeprazole 20 mg daily is on the synthetic active medication list.",
                    "Clopidogrel is not on the current synthetic medication list.",
                ],
                limitations=(
                    "The demonstration diplotype is curated synthetic data. Rare alleles and phasing were not independently "
                    "confirmed. Antiplatelet decisions require indication, bleeding risk, ischemic risk, and specialist review."
                ),
            )
        )

    slco1b1 = pgx.get("SLCO1B1")
    if slco1b1:
        insights.append(
            InsightOut(
                id="insight-slco1b1",
                title="SLCO1B1 decreased-function result is relevant to statin exposure",
                summary=(
                    "The synthetic curated result is SLCO1B1 *1/*5, reported as decreased function. "
                    "The evidence is strongest for simvastatin; atorvastatin is listed as the current statin, "
                    "and SLCO1B1 effects on atorvastatin are smaller and less certain."
                ),
                category="Pharmacogenomics",
                tone="info",
                evidence=(
                    "The CPIC SLCO1B1 guideline associates decreased-function genotypes with higher simvastatin exposure "
                    "and myopathy risk, with prescribing considerations for simvastatin. It does not support an automatic "
                    "change to atorvastatin or a dose recommendation from a simplified model."
                ),
                sources=citation_list(["cpic-slco1b1-simvastatin", "fda-atorvastatin-label"]),
                data_basis=[
                    f"SLCO1B1 {slco1b1['diplotype']} → {slco1b1['phenotype']}",
                    "Atorvastatin 20 mg nightly is on the synthetic active medication list.",
                    "No muscle symptoms or creatine kinase result is recorded.",
                ],
                limitations=(
                    "The synthetic panel assessed rs4149056 only. Statin-associated muscle symptoms require clinical assessment; "
                    "POLIS does not diagnose myopathy or recommend changing a statin."
                ),
            )
        )

    egfr = labs.get("egfr")
    if egfr:
        result, biomarker = egfr
        insights.append(
            InsightOut(
                id="insight-kidney",
                title="Kidney filtration markers are stable in the available data",
                summary=(
                    f"Laboratory-reported eGFR is {result.value:g} {result.unit} with cystatin C also within its interval. "
                    "The available measurements have been stable across the demonstration series. This is not a complete "
                    "kidney assessment and does not rule out kidney disease."
                ),
                category="Kidneys",
                tone="info",
                evidence=(
                    "KDIGO guidance uses eGFR together with albuminuria and clinical context for kidney risk evaluation. "
                    "eGFR is a population estimate with limitations at extremes of muscle mass and in acute illness."
                ),
                sources=citation_list(["kdigo-2024-ckd"]),
                data_basis=[
                    f"eGFR {result.value:g} {result.unit} on {_date({'measured_at': result.measured_at})}",
                    "Urine albumin-to-creatinine ratio 8 mg/g (laboratory interval ≤30).",
                    "Creatinine 0.88 mg/dL and cystatin C 0.82 mg/L on the same synthetic panel.",
                ],
                limitations=(
                    "A spot urine albumin measurement can vary. No blood pressure series or repeated confirmatory "
                    "albuminuria testing is connected. Stable values are not reassurance that kidney disease is absent."
                ),
            )
        )

    sleep = w_avg.get("sleep_duration")
    if sleep:
        insights.append(
            InsightOut(
                id="insight-sleep",
                title="Recent sleep duration is below seven hours on average",
                summary=(
                    f"The 14-day wearable average is {sleep['average']:.1f} hours per night across {sleep['count']} "
                    "device-estimated nights. Short sleep is associated with metabolic, cardiovascular, immune, and "
                    "mood effects, but the direction of cause and effect is not established for an individual."
                ),
                category="Sleep & recovery",
                tone="info",
                evidence=(
                    "CDC public health guidance notes that most adults need at least seven hours of sleep per night. "
                    "Consumer wearables estimate sleep duration and stages and are not polysomnography."
                ),
                sources=citation_list(["cdc-sleep"]),
                data_basis=[
                    f"14-day average sleep {sleep['average']:.1f} h (range {sleep['min']:.1f}–{sleep['max']:.1f} h)",
                    "Device: Oura Ring synthetic sample import.",
                    f"HRV 14-day average {w_avg.get('hrv', {}).get('average', 'not available')} ms (device estimate)",
                ],
                limitations=(
                    "Wearable sleep staging can misclassify sleep and wake. No sleep diary, polysomnography, or "
                    "daytime symptom data are available. Persistent sleep concerns warrant clinical discussion."
                ),
            )
        )

    missing_data = [
        "No spirometry or pulmonary function data",
        "No home blood-pressure series",
        "No continuous glucose monitoring",
        "No medication list confirmation from a clinician or pharmacy",
    ]
    insights.append(
        InsightOut(
            id="insight-data-gaps",
            title="Several data gaps limit what POLIS can interpret",
            summary=(
                "The demonstration profile is rich in laboratory and wearable data but lacks validated pulmonary, "
                "hemodynamic, and continuous metabolic measurements. More data does not automatically mean better "
                "interpretation; data relevance and quality matter."
            ),
            category="Data quality",
            tone="neutral",
            evidence=(
                "POLIS reports completeness rather than a fabricated health score. Missing data are shown explicitly, and "
                "any population assumption used in a simulation is labelled as such."
            ),
            sources=[],
            data_basis=missing_data,
            limitations=(
                "Data completeness is not clinical quality. Adding measurements without clinical context or validated "
                "collection methods can increase false reassurance rather than improve understanding."
            ),
        )
    )

    return insights
