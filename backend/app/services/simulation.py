"""POLIS physiological simulation engine (experimental).

This module implements an explicitly educational one-compartment oral PK
visualization and a prodrug pathway index. It is **not** a PBPK model and it is
not validated for dosing, efficacy, toxicity, or any clinical decision.

Safety invariants enforced here:
* No personalized dose is computed.
* Unsupported medicines return a structured refusal, not an estimate.
* Unknown personal data remains visible as unknown and any population assumption
  is labelled.
* Curated interaction warnings are separate from mechanistic simulation effects.
* Every evidence statement is tied to a retrieved, citable source.
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime

import numpy as np
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HealthProfile, LabResult, Medication, Simulation, User
from app.schemas import SimulationRequest
from app.services import evidence as evidence_service
from app.services.drugs import active_exposures, interaction_pairs_for_medication, resolve_medication
from app.services.labs import _aware, classify_range, latest_by_code
from app.services.pgx import phenotype_map

ENGINE_VERSION = "0.3.0-experimental"
N_SAMPLES = 1600
DISCLAIMER = (
    "POLIS is not a medical device and does not provide medical advice, diagnosis, treatment, or dosing. "
    "This experimental simulation is for education and research exploration only. Never start, stop, or change "
    "a medication based on this output. Discuss any health question with a qualified clinician or pharmacist."
)


class MedicationNotFoundError(LookupError):
    pass


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _age(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None
    return max(0, (datetime.now(UTC) - dob).days // 365)


def _ckd_epi_2021(creatinine_mg_dl: float, age: int, sex_at_birth: str | None) -> float:
    """Race-free CKD-EPI 2021 creatinine equation. Used only when eGFR is absent."""
    female = (sex_at_birth or "").lower() in {"female", "woman", "f"}
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    ratio = creatinine_mg_dl / kappa
    egfr = 142 * (min(ratio, 1) ** alpha) * (max(ratio, 1) ** -1.200) * (0.9938**age)
    if female:
        egfr *= 1.012
    return round(egfr, 1)


def _freshness(measured_at: datetime | None) -> dict:
    if not measured_at:
        return {"date": None, "age_days": None, "stale": True, "label": "Not available"}
    age_days = max(0, (datetime.now(UTC) - _aware(measured_at)).days)
    return {
        "date": _aware(measured_at).isoformat(),
        "age_days": age_days,
        "stale": age_days > 180,
        "label": f"{age_days} days ago" if age_days else "today",
    }


def _labs_snapshot(db: Session, user_id: str) -> dict[str, dict]:
    latest = latest_by_code(db, user_id)
    snapshot = {}
    for code, (result, biomarker) in latest.items():
        snapshot[code] = {
            "value": float(result.value),
            "unit": result.unit,
            "ref_low": result.ref_low,
            "ref_high": result.ref_high,
            "status": classify_range(result.value, result.ref_low, result.ref_high),
            "measured_at": _aware(result.measured_at),
            "freshness": _freshness(result.measured_at),
            "source": result.source,
            "is_synthetic": result.is_synthetic,
            "biomarker": biomarker.name,
        }
    return snapshot


def _hepatic_context(labs: dict[str, dict]) -> dict:
    alt = labs.get("alt")
    ast = labs.get("ast")
    bilirubin = labs.get("bilirubin")
    alp = labs.get("alp")
    info = {
        "alt": alt,
        "ast": ast,
        "bilirubin": bilirubin,
        "alp": alp,
        "severity": "not_assessed",
        "adjustment": 1.0,
        "statement": "No recent ALT, bilirubin, or ALP result is available; hepatic clearance is assumed typical as an explicit population assumption.",
        "used": False,
    }
    if not alt and not bilirubin:
        return info
    severe = False
    moderate = False
    notes = []
    if alt:
        ratio = alt["value"] / alt["ref_high"] if alt["ref_high"] else None
        if ratio is not None and ratio >= 3:
            severe = True
            notes.append(f"ALT is at least 3× its laboratory upper limit ({alt['value']:g} {alt['unit']}).")
        elif ratio is not None and ratio > 1:
            moderate = True
            notes.append(f"ALT is mildly above its laboratory upper limit ({alt['value']:g} {alt['unit']}).")
    if bilirubin and bilirubin["ref_high"] and bilirubin["value"] > 2 * bilirubin["ref_high"]:
        severe = True
        notes.append(f"Total bilirubin is above 2× its laboratory upper limit ({bilirubin['value']:g} {bilirubin['unit']}).")
    if severe:
        info.update(
            severity="marked_abnormality",
            adjustment=0.7,
            used=True,
            statement=(
                "Marked liver-chemistry abnormality is present. The experimental model applies a bounded, "
                "illustrative 30% reduction in hepatic clearance. This is a hypothesis, not a validated "
                "quantitative adjustment; clinical evaluation is required."
                + (" " + " ".join(notes) if notes else "")
            ),
        )
    elif moderate:
        info.update(
            severity="mild_abnormality",
            adjustment=1.0,
            used=False,
            statement=(
                "Liver enzymes are mildly above the reporting laboratory interval, which is non-specific. "
                "The model does not quantitatively reduce clearance for mild isolated elevations. "
                "Clinical evaluation, not this simulation, is needed to interpret the finding."
                + (" " + " ".join(notes) if notes else "")
            ),
        )
    else:
        info.update(
            severity="available_no_marked_abnormality",
            adjustment=1.0,
            used=False,
            statement="Available liver markers do not show a marked abnormality by the model's conservative threshold. This does not assess liver function.",
        )
    return info


def _renal_context(labs: dict[str, dict], profile: HealthProfile | None) -> dict:
    egfr_entry = labs.get("egfr")
    creatinine_entry = labs.get("creatinine")
    age = _age(profile.date_of_birth) if profile else None
    sex = profile.sex_at_birth if profile else None
    if egfr_entry:
        return {
            "value": egfr_entry["value"],
            "unit": egfr_entry["unit"],
            "source": "Laboratory-reported eGFR",
            "measured_at": egfr_entry["measured_at"],
            "freshness": egfr_entry["freshness"],
            "assumption": False,
            "statement": f"Laboratory eGFR {egfr_entry['value']:g} mL/min/1.73m² from {egfr_entry['source']}.",
        }
    if creatinine_entry and age is not None:
        calculated = _ckd_epi_2021(creatinine_entry["value"], age, sex)
        return {
            "value": calculated,
            "unit": "mL/min/1.73m²",
            "source": "Calculated with CKD-EPI 2021 from creatinine, age and sex",
            "measured_at": creatinine_entry["measured_at"],
            "freshness": creatinine_entry["freshness"],
            "assumption": True,
            "statement": (
                f"No laboratory eGFR was available. POLIS calculated an estimate of {calculated:g} mL/min/1.73m² "
                "using CKD-EPI 2021. This remains a population equation estimate with the same limitations as a "
                "laboratory eGFR."
            ),
        }
    return {
        "value": 90.0,
        "unit": "mL/min/1.73m²",
        "source": "Population assumption",
        "measured_at": None,
        "freshness": _freshness(None),
        "assumption": True,
        "statement": "No eGFR or sufficient creatinine data are available. The model assumes eGFR 90 as an explicit population assumption, not personalization.",
    }


def _weight_context(profile: HealthProfile | None) -> dict:
    if profile and profile.weight_kg:
        return {
            "value": profile.weight_kg,
            "source": "Self-reported body weight",
            "assumption": False,
            "statement": f"Body weight {profile.weight_kg:g} kg used for volume and allometric scaling.",
        }
    return {
        "value": 70.0,
        "source": "Population assumption",
        "assumption": True,
        "statement": "Body weight is unavailable. The model assumes 70 kg as an explicit population assumption.",
    }


def _activity_for(gene: str, pgx: dict) -> tuple[float, dict | None, bool]:
    row = pgx.get(gene)
    if not row or row.get("activity_factor") is None:
        return 1.0, row, False
    return float(row["activity_factor"]), row, True


def _ddi_by_gene(interactions: list[dict]) -> dict[str, list[dict]]:
    effects: dict[str, list[dict]] = {}
    for interaction in interactions:
        effect = interaction.get("simulation_effect") or {}
        if not effect or not interaction.get("applies_to_proposed_simulation"):
            continue
        for gene in effect.get("genes", []):
            effects.setdefault(gene, []).append(
                {
                    "factor": float(effect.get("factor", 1.0)),
                    "direction": effect.get("direction"),
                    "label": effect.get("label"),
                    "other_medication": interaction["other_medication"],
                }
            )
    return effects


def _lognormal(rng: np.random.Generator, sigma: float, size: int) -> np.ndarray:
    return np.exp(rng.normal(0, sigma, size))


def _percentiles(values: np.ndarray, decimals: int = 3) -> dict:
    low, median, high = np.percentile(values, [5, 50, 95])
    return {
        "value": round(float(median), decimals),
        "low": round(float(low), decimals),
        "high": round(float(high), decimals),
    }


def _relative_difference_phrase(relative: float, subject: str) -> str:
    delta = (relative - 1) * 100
    if abs(delta) < 8:
        return f"The model estimates near-reference {subject}."
    direction = "higher" if delta > 0 else "lower"
    return f"The model estimates {abs(delta):.0f}% {direction} {subject} than the reference scenario."


def _classify_evidence(evidence_level: str) -> str:
    level = evidence_level.lower()
    if "fda" in level or "guideline" in level or "label" in level:
        return "established_clinical_evidence"
    if "curated" in level:
        return "personalized_evidence"
    if "mechanistic" in level or "hypothesis" in level:
        return "experimental_hypothesis"
    return "supporting_evidence"


def _parameter_sources(med: Medication) -> list[dict]:
    """Expose the illustrative parameter values and their cited origins."""
    config = med.simulation_config or {}
    if med.simulation_model == "pathway_index":
        return [
            {
                "parameter": "Pathway activity weights",
                "value": "CYP2C19 65%, CYP3A4 20%, CYP1A2 15%",
                "source": "Illustrative weights informed by CPIC and FDA labeling; not a validated quantitative model.",
            },
            {
                "parameter": "Index basis",
                "value": config.get("index_basis", "Weighted enzyme activity relative to normal"),
                "source": "POLIS experimental model specification",
            },
        ]
    labels = {
        "half_life_hours": "Elimination half-life",
        "v_per_kg": "Apparent volume per kg",
        "bioavailability": "Oral bioavailability",
        "ka_per_h": "Absorption rate constant",
    }
    output = []
    for key, label in labels.items():
        entry = config.get(key) or {}
        if not entry:
            continue
        value = entry.get("value")
        low = entry.get("low")
        high = entry.get("high")
        rendered = f"{value}"
        if low is not None and high is not None:
            rendered += f" (range {low}–{high})"
        output.append(
            {
                "parameter": label,
                "value": rendered,
                "source": entry.get("source", "Source not recorded"),
            }
        )
    if config.get("reference_note"):
        output.append(
            {
                "parameter": "Reference note",
                "value": config["reference_note"],
                "source": "POLIS model limitation",
            }
        )
    return output


def _sensitivity(
    *,
    model_type: str,
    gene_rows: list[dict],
    remainder: float,
    renal_modifier: float,
    renal_fraction: float,
    egfr_factor: float,
    allometric_cl: float,
    hepatic_factor: float,
    weight: float,
) -> dict:
    """One-at-a-time local sensitivity of the illustrative index.

    This is a model-parameter influence analysis, not a causal effect estimate
    and not a clinical risk model.
    """
    drivers: list[dict] = []

    if model_type == "pathway_index":
        total_weight = sum(row["contribution"] for row in gene_rows) or 1.0
        def index_value(activity_scale: float, target: str | None = None) -> float:
            value = 0.0
            for row in gene_rows:
                scale = activity_scale if row["gene"] == target else 1.0
                value += (row["contribution"] / total_weight) * row["activity_factor"] * scale * row["interaction_factor"]
            return value
        base = index_value(1.0)
        for row in gene_rows:
            low = index_value(0.75, row["gene"])
            high = index_value(1.25, row["gene"])
            effect_low = ((low - base) / base * 100) if base else 0.0
            effect_high = ((high - base) / base * 100) if base else 0.0
            drivers.append(
                {
                    "parameter": f"{row['gene']} activity",
                    "change": "±25%",
                    "effect_low": round(effect_low, 1),
                    "effect_high": round(effect_high, 1),
                    "unit": "% relative index",
                    "known": row["known"],
                }
            )
    else:
        def weighted_activity(scale: float = 1.0, target: str | None = None) -> float:
            value = remainder
            for row in gene_rows:
                multiplier = scale if row["gene"] == target else 1.0
                value += row["contribution"] * row["activity_factor"] * row["interaction_factor"] * multiplier
            return value

        base_activity = weighted_activity()
        base_cl = base_activity * hepatic_factor * renal_modifier * allometric_cl
        base_auc = 1.0 / max(base_cl, 1e-9)
        for row in gene_rows:
            low = weighted_activity(0.75, row["gene"])
            high = weighted_activity(1.25, row["gene"])
            auc_low = 1.0 / max(low * hepatic_factor * renal_modifier * allometric_cl, 1e-9)
            auc_high = 1.0 / max(high * hepatic_factor * renal_modifier * allometric_cl, 1e-9)
            drivers.append(
                {
                    "parameter": f"{row['gene']} activity",
                    "change": "±25%",
                    "effect_low": round((auc_low - base_auc) / base_auc * 100, 1),
                    "effect_high": round((auc_high - base_auc) / base_auc * 100, 1),
                    "unit": "% relative exposure",
                    "known": row["known"],
                }
            )
        # Weight ±15% affects allometric clearance (exponent 0.75).
        low_weight = (weight * 0.85 / 70.0) ** 0.75
        high_weight = (weight * 1.15 / 70.0) ** 0.75
        auc_low = 1.0 / max(base_activity * hepatic_factor * renal_modifier * low_weight, 1e-9)
        auc_high = 1.0 / max(base_activity * hepatic_factor * renal_modifier * high_weight, 1e-9)
        drivers.append(
            {
                "parameter": "Body weight",
                "change": "±15%",
                "effect_low": round((auc_low - base_auc) / base_auc * 100, 1),
                "effect_high": round((auc_high - base_auc) / base_auc * 100, 1),
                "unit": "% relative exposure",
                "known": True,
            }
        )
        if renal_fraction > 0:
            egfr_low = max(0.1, egfr_factor * 0.8)
            egfr_high = min(1.5, egfr_factor * 1.2)
            renal_low = (1 - renal_fraction) + renal_fraction * egfr_low
            renal_high = (1 - renal_fraction) + renal_fraction * egfr_high
            auc_low = 1.0 / max(base_activity * hepatic_factor * renal_low * allometric_cl, 1e-9)
            auc_high = 1.0 / max(base_activity * hepatic_factor * renal_high * allometric_cl, 1e-9)
            drivers.append(
                {
                    "parameter": "Kidney filtration (eGFR)",
                    "change": "±20%",
                    "effect_low": round((auc_low - base_auc) / base_auc * 100, 1),
                    "effect_high": round((auc_high - base_auc) / base_auc * 100, 1),
                    "unit": "% relative exposure",
                    "known": True,
                }
            )

    drivers.sort(key=lambda item: abs(item["effect_high"] - item["effect_low"]), reverse=True)
    return {
        "method": "One-at-a-time deterministic local sensitivity analysis. ±25% enzyme activity, ±15% body weight. Not a causal effect estimate.",
        "drivers": drivers[:5],
        "not_causal": True,
        "note": "Sensitivity shows how strongly the illustrative model depends on an input. It does not show how strongly your health outcome depends on it.",
    }


def _build_pharmacokinetics(med: Medication) -> dict:
    if med.simulation_model == "pathway_index":
        return {
            "absorption": f"{med.name} is administered by the {', '.join(med.route_options) or 'oral'} route. The parent drug is absorbed, but the model does not simulate plasma concentrations.",
            "distribution": "No distribution model is used for the pathway-index output.",
            "metabolism": med.mechanism_summary,
            "elimination": "The active metabolite and downstream elimination are not quantified. The index reflects relative formation potential only.",
            "personalization": "Enzyme activity is weighted by the curated phenotype and any recognised inhibitor. This is a mechanistic index, not measured metabolite exposure.",
        }
    return {
        "absorption": f"The model uses a first-order oral absorption approximation (illustrative ka), not a formulation-specific dissolution model. Route input: {', '.join(med.route_options) or 'oral'}.",
        "distribution": "A single apparent volume of distribution is used, scaled linearly with body weight. Tissue distribution, transporters and protein binding are not represented.",
        "metabolism": med.mechanism_summary,
        "elimination": (
            f"A one-compartment elimination term is derived from a published typical half-life. "
            f"Renal elimination is represented as {med.renal_fraction if med.renal_fraction is not None else 'an unspecified'} fraction of clearance, "
            "scaled by eGFR. This is a simplification, not a mechanistic renal model."
        ),
        "personalization": "Phenotype multipliers are illustrative mechanistic scalings, not validated dosing factors. Curated interactions modify only the proposed drug's modeled pathway and are labelled separately.",
    }


def _question_set(med: Medication, relevant_genes: list[str], interactions: list[dict]) -> list[str]:
    questions = [
        "What information in my health record is incomplete or out of date for assessing this question?",
        "Are any of my current medicines, supplements, or recent illnesses relevant to how this medicine is handled?",
        "What symptoms or measurements would warrant urgent medical attention while taking this medicine?",
        "Does my kidney or liver function change how this medicine should be monitored?",
    ]
    if "clopidogrel" in med.id:
        questions.insert(0, "Given my curated CYP2C19 result and current omeprazole use, could reduced clopidogrel activation matter for my indication?")
        questions.insert(1, "What is my bleeding and thrombotic risk profile, and does my stent or cardiovascular history change the antiplatelet choice?")
    if "metoprolol" in med.id:
        questions.insert(0, "Are my resting heart rate and blood pressure in the range you want with my current metoprolol dose?")
        questions.insert(1, "Given my CYP2D6 result, do you want to assess bradycardia or fatigue differently?")
    if "warfarin" in med.id:
        questions.insert(0, "What is my current INR and target range, and how should this new medicine be monitored?")
    if "tacrolimus" in med.id:
        questions.insert(0, "What is my current tacrolimus trough target, and how will it be monitored?")
    if any(interaction.get("severity") in {"major", "contraindicated"} for interaction in interactions):
        questions.insert(0, "Is the flagged interaction clinically significant for me, and should an alternative medicine be considered?")
    return list(dict.fromkeys(questions))[:6]


def _resolve_output(
    db: Session,
    med: Medication,
    request: SimulationRequest,
    interactions: list[dict],
    allergy_flags: list[dict],
    missing: list[str],
    *,
    synthetic_patient_data: bool,
) -> dict:
    relevant_genes = [pathway.get("gene") for pathway in med.enzyme_pathways if pathway.get("gene")]
    query = f"{med.name} {' '.join(relevant_genes)} mechanism metabolism drug interaction kidney liver"
    retrieved = evidence_service.retrieve(
        db, query, tags=[med.id, *relevant_genes, "guideline", "label"], limit=5
    )
    evidence_out = []
    for source, score, debug in retrieved:
        payload = evidence_service.citation(source).model_dump()
        payload["snippet"] = evidence_service.snippets_for(source, query)
        payload["retrieval_score"] = debug
        evidence_out.append(payload)

    return {
        "status": "not_supported",
        "headline": f"No simulation is available for {med.name}.",
        "reason": (
            f"{med.parameter_note} POLIS does not generate a simplified estimate for medicines where a "
            "reductionist model could mislead. This is a deliberate safety boundary, not an omitted feature."
        ),
        "model": {
            "name": "POLIS simulation engine",
            "version": ENGINE_VERSION,
            "status": "experimental",
            "used": False,
        },
        "medication": {
            "id": med.id,
            "name": med.name,
            "generic_name": med.generic_name,
            "drug_class": med.drug_class,
            "mechanism_summary": med.mechanism_summary,
            "enzyme_pathways": med.enzyme_pathways,
            "warnings": med.warnings,
        },
        "interactions": interactions,
        "allergy_flags": allergy_flags,
        "missing_information": missing,
        "evidence": evidence_out,
        "clinician_questions": _question_set(med, relevant_genes, interactions),
        "safety_flags": [
            {
                "severity": "review",
                "title": "No model output generated",
                "detail": "The request requires specialist interpretation and validated clinical workflows that POLIS does not implement.",
            }
        ],
        "disclaimer": DISCLAIMER,
        "synthetic_data": synthetic_patient_data,
        "reasoning_steps": [
            {"order": 1, "title": "Medication identified", "status": "complete", "detail": f"Matched {med.name} in the local curated formulary.", "evidence_class": "established"},
            {"order": 2, "title": "Simulation eligibility checked", "status": "blocked", "detail": "This medicine is intentionally excluded from the simplified simulator.", "evidence_class": "unknown"},
            {"order": 3, "title": "Evidence retrieved", "status": "complete", "detail": "Authoritative context and clinician questions were assembled without generating a dose or outcome estimate.", "evidence_class": "established"},
        ],
    }


def run_simulation(db: Session, user: User, request: SimulationRequest) -> Simulation:
    med = resolve_medication(db, medication_id=request.medication_id, name=request.medication_name)
    if not med:
        raise MedicationNotFoundError(
            f"'{request.medication_name or request.medication_id}' is not in the curated formulary. "
            "POLIS will not simulate a medicine it cannot identify with a curated evidence base."
        )

    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == user.id))
    pgx = phenotype_map(db, user.id)
    labs = _labs_snapshot(db, user.id)
    weight = _weight_context(profile)
    renal = _renal_context(labs, profile)
    hepatic = _hepatic_context(labs)
    active = active_exposures(db, user.id)
    active_meds = [
        {"name": medication.name, "dose": exposure.dose_text, "frequency": exposure.frequency, "is_synthetic": exposure.is_synthetic}
        for exposure, medication in active
    ]
    interactions = interaction_pairs_for_medication(db, user.id, med.id)
    ddi_by_gene = _ddi_by_gene(interactions)

    relevant_pathways = med.enzyme_pathways or []
    relevant_genes = [pathway.get("gene") for pathway in relevant_pathways if pathway.get("gene")]
    gene_rows = []
    missing: list[str] = []
    assumptions: list[str] = []

    for pathway in relevant_pathways:
        gene = pathway.get("gene")
        if not gene:
            continue
        factor, row, known = _activity_for(gene, pgx)
        if not known:
            missing.append(
                f"{gene} genotype/phenotype is not available. The model assumes population-typical activity for this pathway; this is an assumption, not personalization."
            )
        gene_ddi = ddi_by_gene.get(gene, [])
        combined_ddi = 1.0
        for effect in gene_ddi:
            combined_ddi *= effect["factor"]
        combined_ddi = _clamp(combined_ddi, 0.05, 3.0)
        gene_rows.append(
            {
                "gene": gene,
                "role": pathway.get("role", "metabolism"),
                "contribution": float(pathway.get("contribution", 0.0)),
                "phenotype": row["phenotype"] if row else "Not available",
                "diplotype": row["diplotype"] if row else None,
                "activity_factor": round(factor, 3),
                "known": known,
                "interaction_factor": round(combined_ddi, 3),
                "interaction_effects": gene_ddi,
                "evidence": "personalized curated PGx" if known else "population assumption",
                "evidence_class": "personalized_evidence" if known else "unknown",
                "is_synthetic": bool(row and row.get("is_synthetic")),
                "limitations": row.get("limitations") if row else "No genotype result available.",
            }
        )

    # Allergy matching is intentionally conservative: exact substance/class token
    # overlap only. It cannot determine cross-reactivity or true allergy.
    allergy_flags = []
    if profile:
        for allergy in profile.allergies or []:
            substance = (allergy.get("substance") or "").lower()
            searchable = f"{med.name} {med.generic_name} {med.drug_class}".lower()
            tokens = [token for token in substance.split() if len(token) > 3]
            if tokens and any(token in searchable for token in tokens):
                allergy_flags.append(
                    {
                        "substance": allergy.get("substance"),
                        "reaction": allergy.get("reaction"),
                        "severity": allergy.get("severity", "unknown"),
                        "classification": "established_clinical_evidence",
                        "statement": (
                            "A reported allergy overlaps with this medicine's name or class. POLIS cannot determine "
                            "true allergy, severity, or cross-reactivity. A pharmacist or clinician must review this "
                            "before any exposure."
                        ),
                    }
                )

    active_ids = {medication.id for _exposure, medication in active}
    current_allergy_related = med.id in active_ids

    for code, label in [
        ("alt", "ALT"),
        ("ast", "AST"),
        ("bilirubin", "total bilirubin"),
        ("alp", "ALP"),
    ]:
        entry = labs.get(code)
        if not entry:
            missing.append(f"No recent {label} result is available.")
        elif entry["freshness"]["stale"]:
            missing.append(f"The latest {label} result is {entry['freshness']['age_days']} days old and may not reflect current liver function.")
    if not labs.get("egfr") and not labs.get("creatinine"):
        missing.append("No eGFR or creatinine is available; renal clearance uses a population assumption.")
    elif (labs.get("egfr") or labs.get("creatinine"))["freshness"]["stale"]:
        missing.append("The latest kidney-function result is more than 180 days old; renal function may have changed.")
    if not profile or not profile.weight_kg:
        missing.append("Body weight is unavailable; volume of distribution uses a 70 kg population assumption.")
    if not profile or not profile.pregnancy_status:
        missing.append("Pregnancy status is not recorded. This simulation does not assess pregnancy safety.")
    if not profile or not profile.date_of_birth:
        missing.append("Date of birth is unavailable; age-dependent clinical context cannot be assessed.")
    if not active_meds:
        missing.append("No active medication list is recorded; interaction detection may be incomplete.")
    if not profile or not profile.allergies:
        missing.append("No allergy history is recorded.")

    if "warfarin" in med.id:
        missing.append("INR is not available. Warfarin effect and bleeding risk cannot be assessed by this PK-only model.")
        missing.append("Dietary vitamin K intake, illness, and anticoagulation target are not recorded.")
    if "metoprolol" in med.id:
        missing.append("Resting heart rate and blood pressure readings are not connected; hemodynamic response cannot be assessed.")
    if "clopidogrel" in med.id:
        missing.append("Antiplatelet indication, stent status, bleeding risk, and ischemic risk are not recorded.")
    if "simvastatin" in med.id or "atorvastatin" in med.id:
        missing.append("Muscle symptoms, creatine kinase, and the current lipid target are not recorded.")
    if "tacrolimus" in med.id:
        missing.append("Tacrolimus trough concentrations and transplant context are not available.")
    if "ibuprofen" in med.id:
        missing.append("Kidney function, gastrointestinal bleeding risk, and anticoagulant use should be reviewed; the model does not estimate these risks.")

    for interaction in interactions:
        if interaction["severity"] in {"major", "contraindicated"}:
            missing.append(
                f"Serious interaction signal with {interaction['other_medication']} requires professional review; the model cannot determine the right regimen."
            )

    assumptions.append("The simulation compares the proposed medicine with a hypothetical reference person with normal enzyme activity, eGFR 90, no interacting drugs, and no marked liver-chemistry abnormality.")
    assumptions.append("The dose entered is not used to calculate a personalized dose. Concentrations are normalized to a reference peak to avoid implying a dosing recommendation.")
    assumptions.append("Age is not applied as an independent clearance multiplier; where eGFR is absent, age contributes only through the CKD-EPI 2021 estimate.")
    assumptions.append("Enzyme activity multipliers are illustrative educational scalings, not CPIC dosing factors or measured enzyme activity.")
    if renal["assumption"]:
        assumptions.append(renal["statement"])
    if weight["assumption"]:
        assumptions.append(weight["statement"])
    if hepatic["used"]:
        assumptions.append(hepatic["statement"])

    summary_metrics: list[dict] = []
    curve = None
    pathway_index = None
    headline = ""
    confidence_label = "Low to moderate"

    if not med.is_simulation_eligible or med.simulation_model == "not_supported":
        output = _resolve_output(
            db,
            med,
            request,
            interactions,
            allergy_flags,
            missing,
            synthetic_patient_data=bool(user.is_demo),
        )
        output["allergy_flags"] = allergy_flags or output["allergy_flags"]
        output["pharmacokinetics"] = _build_pharmacokinetics(med)
        output["assumptions"] = assumptions
        output["active_medications"] = active_meds
        output["data_quality"] = {
            "liver": hepatic,
            "kidney": renal,
            "weight": weight,
            "pgx": gene_rows,
        }
        if allergy_flags:
            output["safety_flags"].insert(
                0,
                {
                    "severity": "danger",
                    "title": "Reported allergy overlap",
                    "detail": (
                        "A recorded allergy name overlaps with this medicine. Do not use this output to determine "
                        "allergy safety. Seek professional review before any exposure."
                    ),
                },
            )
        output = jsonable_encoder(output)
        simulation = Simulation(
            user_id=user.id,
            medication_id=med.id,
            medication_name=med.name,
            dose_text=request.dose_text,
            route=request.route,
            frequency=request.frequency,
            status="not_supported",
            engine_version=ENGINE_VERSION,
            input_json={
                **request.model_dump(),
                "resolved_medication_id": med.id,
                "active_medications": [entry["name"] for entry in active_meds],
            },
            output_json=output,
            evidence_json=output.get("evidence", []),
        )
        db.add(simulation)
        db.flush()
        return simulation

    config = med.simulation_config or {}
    seed_material = f"{user.id}|{med.id}|{med.simulation_model}|v3"
    seed = int.from_bytes(hashlib.sha256(seed_material.encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    egfr_factor = _clamp(renal["value"] / 90.0, 0.1, 1.5)
    renal_fraction = float(med.renal_fraction or 0.0)
    renal_modifier = (1 - renal_fraction) + renal_fraction * egfr_factor
    allometric_cl = _clamp((weight["value"] / 70.0) ** 0.75, 0.6, 1.6)
    volume_factor = _clamp(weight["value"] / 70.0, 0.6, 1.6)

    if med.simulation_model == "pathway_index":
        index_label = config.get("index_label", "Relative pathway activity")
        contributions = []
        base_index = 0.0
        total_contribution = sum(row["contribution"] for row in gene_rows) or 1.0
        for row in gene_rows:
            fraction = row["contribution"] / total_contribution
            base_index += fraction * row["activity_factor"] * row["interaction_factor"]
            contributions.append(
                {
                    "gene": row["gene"],
                    "phenotype": row["phenotype"],
                    "weight": round(fraction, 3),
                    "activity_factor": row["activity_factor"],
                    "interaction_factor": row["interaction_factor"],
                    "contribution": round(fraction * row["activity_factor"] * row["interaction_factor"], 3),
                    "known": row["known"],
                }
            )
        index_draws = np.zeros(N_SAMPLES)
        for row, contribution in zip(gene_rows, contributions):
            sigma = 0.18 if row["known"] else 0.35
            pathway_draw = _lognormal(rng, sigma, N_SAMPLES)
            ddi_sigma = 0.25 if row["interaction_factor"] != 1.0 else 0.0
            ddi_draw = _lognormal(rng, ddi_sigma, N_SAMPLES) if ddi_sigma else np.ones(N_SAMPLES)
            index_draws += contribution["weight"] * row["activity_factor"] * pathway_draw * row["interaction_factor"] * ddi_draw
        interval = _percentiles(index_draws)
        pathway_index = {
            "label": index_label,
            "value": interval["value"],
            "low": interval["low"],
            "high": interval["high"],
            "reference": 1.0,
            "contributions": contributions,
            "basis": config.get("index_basis", "Weighted enzyme activity relative to a normal metabolizer reference."),
            "classification": "model_estimate",
            "note": "A mechanistic index of relative active-metabolite formation potential, not a measure of efficacy, bleeding risk, or clinical outcome.",
        }
        if interval["value"] < 0.85:
            headline = (
                _relative_difference_phrase(interval["value"], "active-metabolite formation potential")
                + " This is a mechanistic hypothesis, not an efficacy prediction; clinical decisions require a qualified clinician."
            )
        elif interval["value"] > 1.15:
            headline = "The experimental pathway model estimates higher relative active-metabolite formation potential, but this does not establish efficacy or safety."
        else:
            headline = "The experimental pathway model estimates near-reference active-metabolite formation potential. This does not predict clinical response."
        summary_metrics.append(
            {
                "key": "pathway_index",
                "label": index_label,
                "value": interval["value"],
                "low": interval["low"],
                "high": interval["high"],
                "unit": "× reference",
                "classification": "model_estimate",
                "note": "5th–95th percentile across illustrative parameter uncertainty. Not a clinical measurement.",
            }
        )
        confidence_label = "Low"
    else:
        try:
            half_life = float((config.get("half_life_hours") or {}).get("value"))
            v_per_kg = float((config.get("v_per_kg") or {}).get("value"))
            bioavailability = float((config.get("bioavailability") or {}).get("value"))
            ka = float((config.get("ka_per_h") or {}).get("value"))
        except (TypeError, ValueError) as exc:
            raise ValueError("The curated simulation parameters for this medication are incomplete.") from exc
        reference_v = v_per_kg * 70.0
        reference_cl = (math.log(2) / half_life) * reference_v
        base_activity = 0.0
        total_contribution = sum(row["contribution"] for row in gene_rows)
        remainder = max(0.0, 1.0 - total_contribution)
        # Draw shared base PK uncertainty and independent modifier uncertainty.
        cl_base_draw = _lognormal(rng, 0.30, N_SAMPLES)
        v_base_draw = _lognormal(rng, 0.20, N_SAMPLES)
        ka_draw = ka * _lognormal(rng, 0.25, N_SAMPLES)
        weighted_draw = np.full(N_SAMPLES, remainder)
        for row in gene_rows:
            sigma = 0.20 if row["known"] else 0.35
            phenotype_draw = _lognormal(rng, sigma, N_SAMPLES)
            if row["interaction_factor"] != 1.0:
                phenotype_draw *= _lognormal(rng, 0.25, N_SAMPLES)
            weighted_draw += row["contribution"] * row["activity_factor"] * row["interaction_factor"] * phenotype_draw
        hepatic_draw = _lognormal(rng, 0.15, N_SAMPLES) if hepatic["used"] else np.ones(N_SAMPLES)
        cl_factor = np.clip(weighted_draw * hepatic_draw * renal_modifier * allometric_cl, 0.03, 3.0)
        v_factor = np.full(N_SAMPLES, volume_factor)
        cl_ref = reference_cl * cl_base_draw
        v_ref = reference_v * v_base_draw
        cl_personal = cl_ref * cl_factor
        v_personal = v_ref * v_factor
        k_ref = cl_ref / v_ref
        k_personal = cl_personal / v_personal

        horizon = _clamp(half_life * 4, 24, 168)
        times = np.linspace(0, horizon, 140)
        # Dose is normalized to 1; curves are relative to reference peak.
        dose = 1.0
        # Cp(t) for each draw. Shapes broadcast to (n_samples, timepoints).
        def concentrations(v_arr, k_arr):
            with np.errstate(divide="ignore", invalid="ignore"):
                denom = v_arr * (ka_draw - k_arr)
                prefactor = (bioavailability * dose * ka_draw) / denom
                first = np.exp(-k_arr[:, None] * times[None, :])
                second = np.exp(-ka_draw[:, None] * times[None, :])
                return prefactor[:, None] * (first - second)

        personal_curves = concentrations(v_personal, k_personal)
        reference_curves = concentrations(v_ref, k_ref)
        # Guard non-finite values from ka approximately equal to k.
        personal_curves = np.nan_to_num(personal_curves, nan=0.0, posinf=0.0, neginf=0.0)
        reference_curves = np.nan_to_num(reference_curves, nan=0.0, posinf=0.0, neginf=0.0)
        allocation = 1.0 / reference_curves.max(axis=1, keepdims=True)
        relative_curves = personal_curves * allocation
        p05, p50, p95 = np.percentile(relative_curves, [5, 50, 95], axis=0)

        reference_peak = np.maximum(reference_curves.max(axis=1), 1e-12)
        personal_peak = personal_curves.max(axis=1)
        reference_auc = bioavailability * dose / np.maximum(cl_ref, 1e-12)
        personal_auc = bioavailability * dose / np.maximum(cl_personal, 1e-12)
        relative_auc = personal_auc / reference_auc
        relative_cmax = personal_peak / reference_peak
        personal_tmax = times[np.argmax(personal_curves, axis=1)]
        personal_half_life = math.log(2) / k_personal

        auc_interval = _percentiles(relative_auc)
        cmax_interval = _percentiles(relative_cmax)
        tmax_interval = _percentiles(personal_tmax, 1)
        half_life_interval = _percentiles(personal_half_life, 1)
        curve = {
            "times": [round(float(value), 2) for value in times],
            "median": [round(float(value), 3) for value in p50],
            "p05": [round(float(value), 3) for value in p05],
            "p95": [round(float(value), 3) for value in p95],
            "reference": [1.0 for _ in times],
            "x_label": "Hours since oral dose",
            "y_label": "Relative concentration (reference peak = 1.0)",
            "horizon_hours": round(float(horizon), 1),
            "classification": "model_estimate",
            "note": "Illustrative one-compartment oral PK. Not a measured concentration and not a dosing target.",
        }
        summary_metrics = [
            {
                "key": "relative_auc",
                "label": "Relative total exposure (AUC)",
                "value": auc_interval["value"],
                "low": auc_interval["low"],
                "high": auc_interval["high"],
                "unit": "× reference",
                "classification": "model_estimate",
                "note": "Area under the illustrative concentration–time curve relative to a typical reference. Not an individualized AUC.",
            },
            {
                "key": "relative_cmax",
                "label": "Relative peak concentration",
                "value": cmax_interval["value"],
                "low": cmax_interval["low"],
                "high": cmax_interval["high"],
                "unit": "× reference",
                "classification": "model_estimate",
                "note": "Illustrative peak relative to reference. No absolute concentration or target range is produced.",
            },
            {
                "key": "tmax",
                "label": "Time to peak",
                "value": tmax_interval["value"],
                "low": tmax_interval["low"],
                "high": tmax_interval["high"],
                "unit": "h",
                "classification": "model_estimate",
                "note": "First-order absorption approximation; formulation-specific behavior is not modeled.",
            },
            {
                "key": "half_life",
                "label": "Estimated elimination half-life",
                "value": half_life_interval["value"],
                "low": half_life_interval["low"],
                "high": half_life_interval["high"],
                "unit": "h",
                "classification": "model_estimate",
                "note": "Derived from modeled clearance and volume, not measured in this person.",
            },
        ]
        headline = (
            _relative_difference_phrase(auc_interval["value"], "relative total exposure")
            + " This is an experimental model estimate, not a measured drug level and not a prediction of benefit or harm."
        )
        confidence_label = "Low to moderate"

    data_quality = {
        "liver": hepatic,
        "kidney": renal,
        "weight": weight,
        "activity_pathways": gene_rows,
        "renal_modifier": round(float(renal_modifier), 3),
        "allometric_clearance_modifier": round(float(allometric_cl), 3),
        "volume_modifier": round(float(volume_factor), 3),
    }

    model_inputs = []
    for row in gene_rows:
        model_inputs.append(
            {
                "label": f"{row['gene']} phenotype",
                "value": f"{row['phenotype']}" + (f" ({row['diplotype']})" if row.get("diplotype") else ""),
                "source": "Synthetic curated pharmacogenomic panel" if row["known"] else "No result: population assumption",
                "classification": row["evidence_class"],
                "used": True,
                "detail": f"{row['contribution'] * 100:.0f}% modeled pathway contribution · activity multiplier {row['activity_factor']}×"
                + (f" · interaction factor {row['interaction_factor']}×" if row["interaction_factor"] != 1.0 else ""),
            }
        )
    model_inputs.extend(
        [
            {
                "label": "Kidney function",
                "value": f"eGFR {renal['value']:g} {renal['unit']}",
                "source": renal["source"],
                "classification": "personalized_evidence" if not renal["assumption"] else "unknown",
                "used": med.renal_fraction not in (None, 0),
                "detail": f"Freshness: {renal['freshness']['label']}. Renal fraction of clearance: {med.renal_fraction if med.renal_fraction is not None else 'not specified'}.",
            },
            {
                "label": "Liver chemistry context",
                "value": (
                    f"ALT {hepatic['alt']['value']:g} {hepatic['alt']['unit']} ({hepatic['alt']['status']})"
                    if hepatic.get("alt")
                    else "Not available"
                ),
                "source": "Latest available laboratory results; mild elevation is not quantitatively used",
                "classification": "personalized_evidence" if hepatic.get("alt") else "unknown",
                "used": hepatic["used"],
                "detail": hepatic["statement"],
            },
            {
                "label": "Body weight",
                "value": f"{weight['value']:g} kg",
                "source": weight["source"],
                "classification": "personalized_evidence" if not weight["assumption"] else "unknown",
                "used": True,
                "detail": "Used for illustrative volume and allometric scaling.",
            },
        ]
    )
    for interaction in interactions:
        model_inputs.append(
            {
                "label": f"Interaction: {interaction['other_medication']}",
                "value": interaction["severity"],
                "source": interaction["source_title"],
                "classification": "established_clinical_evidence",
                "used": bool(interaction.get("applies_to_proposed_simulation")),
                "detail": interaction["mechanism"],
            }
        )

    uncertainty_statements = [
        "Intervals reflect illustrative parameter uncertainty only; they are not confidence intervals for a clinical outcome.",
        "The model does not include active metabolites, transporters for most medicines, protein binding, tissue distribution, or pharmacodynamics.",
        "Phenotype multipliers are educational scalings, not validated dosing factors.",
        "A single latest laboratory value is used; biological and analytical variation are not modeled.",
    ]
    if any(not row["known"] for row in gene_rows):
        uncertainty_statements.append("At least one relevant genotype result is missing, so population-typical activity was assumed and labelled.")
    if interactions:
        uncertainty_statements.append("Curated interaction flags are based on regulatory labeling or guidelines; the magnitude of effect in this individual is unknown.")
    if med.simulation_model == "pathway_index":
        uncertainty_statements.append(
            "The pathway index does not model platelet function, active metabolite concentrations, efficacy, bleeding risk, or clinical outcomes."
        )

    reasoning_steps = [
        {"order": 1, "title": "Medication identified", "status": "complete", "detail": f"{med.name} matched to the curated local formulary.", "evidence_class": "established"},
        {
            "order": 2,
            "title": "Personal biological context retrieved",
            "status": "complete",
            "detail": f"{len(labs)} laboratory markers available; {len(gene_rows)} relevant pharmacogene(s) assessed; {len(active_meds)} active medication(s) recorded.",
            "evidence_class": "personalized_evidence",
        },
        {
            "order": 3,
            "title": "Pharmacogenomic mapping",
            "status": "complete" if gene_rows and all(row["known"] for row in gene_rows) else "flagged",
            "detail": "Known phenotypes mapped to illustrative activity factors. Missing results remain visible and are not invented." if any(not row["known"] for row in gene_rows) else "All relevant curated phenotypes were available.",
            "evidence_class": "personalized_evidence" if all(row["known"] for row in gene_rows) else "unknown",
        },
        {
            "order": 4,
            "title": "Interaction and allergy screen",
            "status": "flagged" if interactions or allergy_flags else "complete",
            "detail": f"{len(interactions)} curated interaction signal(s); {len(allergy_flags)} allergy overlap flag(s). These require professional review." if interactions or allergy_flags else "No curated interaction or allergy-name overlap detected. Absence of a flag is not proof of safety.",
            "evidence_class": "established_clinical_evidence",
        },
        {
            "order": 5,
            "title": "Experimental model run",
            "status": "complete",
            "detail": "One-compartment oral PK visualization with uncertainty propagation." if med.simulation_model == "oral_pk" else "Relative pathway-activity index with uncertainty propagation; no concentration curve.",
            "evidence_class": "experimental_hypothesis",
        },
        {
            "order": 6,
            "title": "Evidence retrieval",
            "status": "complete",
            "detail": "Retrieved versioned guidance and labeling from the local evidence corpus; citations are attached to this result.",
            "evidence_class": "established_clinical_evidence",
        },
        {
            "order": 7,
            "title": "Limits and missing information identified",
            "status": "flagged" if missing else "complete",
            "detail": f"{len(missing)} missing-information item(s) recorded. Unknown information is not replaced by a conclusion." if missing else "No critical information gaps detected by the model's checks, although the model remains experimental.",
            "evidence_class": "unknown" if missing else "established_clinical_evidence",
        },
    ]

    query = f"{med.name} {' '.join(relevant_genes)} metabolism liver kidney interaction clinical evidence"
    retrieved = evidence_service.retrieve(db, query, tags=[med.id, *relevant_genes, "guideline", "label"], limit=5)
    evidence_out = []
    for source, _score, debug in retrieved:
        payload = evidence_service.citation(source).model_dump()
        payload["snippet"] = evidence_service.snippets_for(source, query)
        payload["retrieval_score"] = debug
        evidence_out.append(payload)

    safety_flags = []
    if allergy_flags:
        safety_flags.append(
            {
                "severity": "danger",
                "title": "Reported allergy overlap",
                "detail": "A recorded allergy name overlaps with this medicine. Do not use this simulation to determine allergy safety. Seek professional review before exposure.",
            }
        )
    for interaction in interactions:
        severity = interaction["severity"]
        if severity in {"major", "contraindicated"}:
            safety_flags.append(
                {
                    "severity": "danger" if severity == "contraindicated" else "warning",
                    "title": f"{severity.capitalize()} interaction: {interaction['other_medication']}",
                    "detail": interaction["management"],
                }
            )
        elif severity == "moderate":
            safety_flags.append(
                {
                    "severity": "warning",
                    "title": f"Moderate interaction: {interaction['other_medication']}",
                    "detail": interaction["management"],
                }
            )
    if current_allergy_related:
        safety_flags.append(
            {
                "severity": "warning",
                "title": "Medicine already listed as current",
                "detail": "This medicine appears in your current medication list. POLIS is not reviewing or changing your regimen. Discuss concerns with your prescriber or pharmacist.",
            }
        )
    safety_flags.append(
        {
            "severity": "info",
            "title": "No dose calculation performed",
            "detail": "POLIS does not calculate a personalized dose. Dose text is recorded as context only.",
        }
    )

    output = {
        "status": "complete" if not missing else "partial",
        "headline": headline,
        "model": {
            "name": "POLIS one-compartment oral PK" if med.simulation_model == "oral_pk" else "POLIS prodrug pathway index",
            "version": ENGINE_VERSION,
            "status": "experimental",
            "used": True,
            "confidence": confidence_label,
            "description": "Educational mechanistic simulation with uncertainty propagation. Not a PBPK model and not validated for clinical use.",
            "limitations": (
                "One-compartment approximation, illustrative parameters, no active metabolites or pharmacodynamics, "
                "no validated dosing, no clinical outcome prediction, and no external validation."
            ),
        },
        "medication": {
            "id": med.id,
            "name": med.name,
            "generic_name": med.generic_name,
            "drug_class": med.drug_class,
            "mechanism_summary": med.mechanism_summary,
            "enzyme_pathways": med.enzyme_pathways,
            "transporter_pathways": med.transporter_pathways,
            "half_life_hours": med.half_life_hours,
            "warnings": med.warnings,
            "parameter_note": med.parameter_note,
            "simulation_model": med.simulation_model,
            "parameter_sources": _parameter_sources(med),
        },
        "summary_metrics": summary_metrics,
        "curve": curve,
        "pathway_index": pathway_index,
        "model_inputs": model_inputs,
        "pgx": gene_rows,
        "sensitivity": _sensitivity(
            model_type=med.simulation_model,
            gene_rows=gene_rows,
            remainder=max(0.0, 1.0 - sum(row["contribution"] for row in gene_rows)),
            renal_modifier=float(renal_modifier),
            renal_fraction=float(renal_fraction),
            egfr_factor=float(egfr_factor),
            allometric_cl=float(allometric_cl),
            hepatic_factor=float(hepatic["adjustment"]),
            weight=float(weight["value"]),
        ),
        "active_medications": active_meds,
        "interactions": interactions,
        "allergy_flags": allergy_flags,
        "missing_information": list(dict.fromkeys(missing)),
        "assumptions": list(dict.fromkeys(assumptions)),
        "uncertainty": {
            "level": confidence_label,
            "statements": uncertainty_statements,
            "interval_definition": "5th–95th percentile over 1,600 Monte Carlo draws representing illustrative parameter uncertainty.",
        },
        "pharmacokinetics": _build_pharmacokinetics(med),
        "reasoning_steps": reasoning_steps,
        "evidence": evidence_out,
        "clinician_questions": _question_set(med, relevant_genes, interactions),
        "safety_flags": safety_flags,
        "data_quality": data_quality,
        "disclaimer": DISCLAIMER,
        "synthetic_data": bool(user.is_demo),
        "labels": {
            "established_clinical_evidence": "Established clinical evidence",
            "personalized_evidence": "Personalized evidence",
            "model_estimate": "Model estimate",
            "experimental_hypothesis": "Experimental hypothesis",
            "unknown": "Unknown",
        },
    }

    output = jsonable_encoder(output)
    simulation = Simulation(
        user_id=user.id,
        medication_id=med.id,
        medication_name=med.name,
        dose_text=request.dose_text,
        route=request.route,
        frequency=request.frequency,
        status=output["status"],
        engine_version=ENGINE_VERSION,
        input_json={
            **request.model_dump(),
            "resolved_medication_id": med.id,
            "active_medications": [entry["name"] for entry in active_meds],
        },
        output_json=output,
        evidence_json=evidence_out,
    )
    db.add(simulation)
    db.flush()
    return simulation
