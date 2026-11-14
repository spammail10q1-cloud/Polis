"""Experimental causal modeling layer.

This is a deliberately narrow structural causal exploration over the user's own
wearable series. It is **not** a causal discovery engine, does not establish
causality, and makes an explicit no-unmeasured-confounding assumption.

Implemented:
* a small directed acyclic graph for the supported question,
* a linear structural equation with a single modeled confounder,
* a do-operator intervention on the treatment,
* bootstrap uncertainty intervals,
* complete-case accounting and explicit limitations.

Not implemented:
* causal discovery, back-door adjustment over an arbitrary graph, instrumental
  variables, propensity methods, time-varying confounding, mediation analysis,
  or clinical outcome modeling.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WearableMeasurement
from app.services.evidence import citations
from app.services.labs import _aware

DISCLAIMER = (
    "This is an exploratory causal model under strong, stated assumptions. It does not establish causation "
    "and must not be used for diagnosis, treatment, or health decisions. Discuss any concern with a qualified clinician."
)

TREATMENTS: dict[str, dict] = {
    "sleep_duration": {
        "code": "sleep_duration",
        "label": "Sleep duration",
        "unit": "h",
        "default_delta": 0.5,
        "min_delta": -2.0,
        "max_delta": 2.0,
        "delta_step": 0.25,
        "source": "Consumer wearable estimate",
        "outcomes": ["hrv", "resting_hr"],
        "confounder": "steps",
        "evidence_ids": ["cdc-sleep"],
    },
    "steps": {
        "code": "steps",
        "label": "Daily steps",
        "unit": "steps",
        "default_delta": 1000,
        "min_delta": -5000,
        "max_delta": 5000,
        "delta_step": 250,
        "source": "Consumer wearable estimate",
        "outcomes": ["hrv", "resting_hr"],
        "confounder": "sleep_duration",
        "evidence_ids": [],
    },
}

OUTCOMES: dict[str, dict] = {
    "hrv": {"code": "hrv", "label": "Heart-rate variability", "unit": "ms", "direction_note": "device estimate"},
    "resting_hr": {"code": "resting_hr", "label": "Resting heart rate", "unit": "bpm", "direction_note": "device estimate"},
}

ALLOWED_OUTCOMES = {
    ("sleep_duration", "hrv"),
    ("sleep_duration", "resting_hr"),
    ("steps", "hrv"),
    ("steps", "resting_hr"),
}


def catalog() -> dict:
    return {
        "treatments": [
            {key: value for key, value in item.items() if key not in {"evidence_ids", "outcomes"}}
            | {"outcomes": item["outcomes"]}
            for item in TREATMENTS.values()
        ],
        "outcomes": list(OUTCOMES.values()),
        "minimum_days": 14,
        "method": (
            "Linear structural equation with one measured confounder, estimated from complete within-person days. "
            "The intervention uses do(T = observed + delta) with the confounder held at its observed value."
        ),
        "evidence_class": "experimental_hypothesis",
        "disclaimer": DISCLAIMER,
    }


def _daily_values(db: Session, user_id: str) -> tuple[list[dict], int]:
    rows = list(
        db.scalars(
            select(WearableMeasurement)
            .where(WearableMeasurement.user_id == user_id)
            .order_by(WearableMeasurement.recorded_at)
        ).all()
    )
    by_day: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        if row.metric not in {"sleep_duration", "steps", "hrv", "resting_hr"}:
            continue
        day = _aware(row.recorded_at).date().isoformat()
        by_day.setdefault(day, {}).setdefault(row.metric, []).append(float(row.value))
    daily = []
    dropped = 0
    for day, metrics in sorted(by_day.items()):
        if "sleep_duration" not in metrics or "steps" not in metrics or ("hrv" not in metrics and "resting_hr" not in metrics):
            dropped += 1
            continue
        daily.append(
            {
                "date": day,
                "sleep_duration": sum(metrics["sleep_duration"]) / len(metrics["sleep_duration"]),
                "steps": sum(metrics["steps"]) / len(metrics["steps"]),
                "hrv": (sum(metrics["hrv"]) / len(metrics["hrv"])) if "hrv" in metrics else None,
                "resting_hr": (sum(metrics["resting_hr"]) / len(metrics["resting_hr"])) if "resting_hr" in metrics else None,
            }
        )
    return daily, dropped


def _fit(rows: list[dict], treatment: str, outcome: str, confounder: str) -> tuple[np.ndarray, float]:
    x = np.array(
        [[1.0, float(row[treatment]), float(row[confounder])] for row in rows],
        dtype=float,
    )
    y = np.array([float(row[outcome]) for row in rows], dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    predictions = x @ beta
    residual = float(np.sum((y - predictions) ** 2))
    total = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - residual / total if total > 0 else 0.0
    return beta, r_squared


def run_causal_query(
    db: Session,
    *,
    user_id: str,
    treatment: str,
    outcome: str,
    delta: float,
) -> dict:
    if treatment not in TREATMENTS:
        raise ValueError("Unsupported treatment. Choose sleep_duration or steps.")
    if outcome not in OUTCOMES:
        raise ValueError("Unsupported outcome. Choose hrv or resting_hr.")
    if (treatment, outcome) not in ALLOWED_OUTCOMES:
        raise ValueError("This treatment/outcome pair is not supported by the experimental causal model.")
    treatment_spec = TREATMENTS[treatment]
    if not math.isfinite(delta) or delta < treatment_spec["min_delta"] or delta > treatment_spec["max_delta"]:
        raise ValueError(
            f"Delta must be between {treatment_spec['min_delta']} and {treatment_spec['max_delta']} {treatment_spec['unit']}."
        )
    daily, dropped = _daily_values(db, user_id)
    complete = [row for row in daily if row[outcome] is not None and row[treatment] is not None and row[treatment_spec["confounder"]] is not None]
    if len(complete) < 14:
        return {
            "status": "insufficient_data",
            "reason": f"At least 14 complete within-person days are required; {len(complete)} are available.",
            "available_days": len(complete),
            "missing_information": [
                "Complete same-day wearable treatment, outcome and confounder values are required.",
                "The model does not impute missing days.",
            ],
            "disclaimer": DISCLAIMER,
            "evidence_class": "experimental_hypothesis",
        }

    confounder = treatment_spec["confounder"]
    beta, r_squared = _fit(complete, treatment, outcome, confounder)
    coefficient = float(beta[1])
    effect = coefficient * delta
    rng = np.random.default_rng(20261114)
    bootstrap_effects: list[float] = []
    n = len(complete)
    for _ in range(800):
        idx = rng.integers(0, n, n)
        sample = [complete[i] for i in idx]
        try:
            sample_beta, _ = _fit(sample, treatment, outcome, confounder)
            bootstrap_effects.append(float(sample_beta[1]) * delta)
        except np.linalg.LinAlgError:
            continue
    if bootstrap_effects:
        low, high = np.percentile(bootstrap_effects, [5, 95])
    else:
        low = high = effect
    observed_mean = float(np.mean([row[treatment] for row in complete]))
    outcome_mean = float(np.mean([row[outcome] for row in complete]))
    confounder_mean = float(np.mean([row[confounder] for row in complete]))
    direction = "increase" if effect > 0 else "decrease" if effect < 0 else "no modeled change"

    dag_nodes = [
        {"id": treatment, "label": treatment_spec["label"], "role": "treatment"},
        {"id": outcome, "label": OUTCOMES[outcome]["label"], "role": "outcome"},
        {"id": confounder, "label": "Daily steps" if confounder == "steps" else "Sleep duration", "role": "confounder"},
        {"id": "unmeasured", "label": "Unmeasured factors", "role": "unobserved"},
    ]
    dag_edges = [
        {"source": treatment, "target": outcome, "label": "modeled effect", "assumption": "linear, no interaction"},
        {"source": confounder, "target": outcome, "label": "adjusted", "assumption": "linear additive control"},
        {"source": "unmeasured", "target": outcome, "label": "not measured", "assumption": "assumed not confounding"},
        {"source": "unmeasured", "target": treatment, "label": "not measured", "assumption": "no unmeasured treatment confounding"},
    ]
    sources = citations(db, treatment_spec["evidence_ids"])
    points = [
        {
            "date": row["date"],
            "treatment": round(row[treatment], 2),
            "outcome": round(row[outcome], 2),
            "confounder": round(row[confounder], 1),
        }
        for row in complete[:60]
    ]
    return {
        "status": "complete",
        "available_days": len(complete),
        "excluded_days": dropped,
        "treatment": {key: value for key, value in treatment_spec.items() if key not in {"evidence_ids", "outcomes"}},
        "outcome": OUTCOMES[outcome],
        "delta": delta,
        "observed": {
            "treatment_mean": round(observed_mean, 2),
            "outcome_mean": round(outcome_mean, 2),
            "confounder_mean": round(confounder_mean, 1),
        },
        "model": {
            "name": "Exploratory linear structural equation",
            "version": "0.1.0-experimental",
            "coefficient": round(coefficient, 5),
            "intercept": round(float(beta[0]), 4),
            "confounder_coefficient": round(float(beta[2]), 6),
            "r_squared": round(r_squared, 3),
            "n_days": len(complete),
            "equation": f"{OUTCOMES[outcome]['label']} = {float(beta[0]):.3f} + ({coefficient:.5f} × {treatment_spec['label']}) + ({float(beta[2]):.6f} × {confounder.replace('_', ' ')})",
            "evidence_class": "experimental_hypothesis",
        },
        "estimate": {
            "value": round(effect, 2),
            "low": round(float(low), 2),
            "high": round(float(high), 2),
            "unit": OUTCOMES[outcome]["unit"],
            "direction": direction,
            "label": f"Associational counterfactual under a do({treatment} + {delta:g} {treatment_spec['unit']}) intervention",
            "interval_definition": "5th–95th percentile bootstrap interval over within-person complete days (800 resamples).",
        },
        "dag": {"nodes": dag_nodes, "edges": dag_edges},
        "points": points,
        "assumptions": [
            "The linear functional form is correct and stable across the observed range.",
            f"{confounder.replace('_', ' ').title()} is the only measured confounder included.",
            "There are no unmeasured common causes of treatment and outcome.",
            "Wearable measurements are unbiased same-day estimates; they are not.",
            "No lag structure, time-varying confounding, or reverse causation is modeled.",
            "The intervention is a hypothetical shift holding the confounder at its observed value.",
        ],
        "limitations": [
            "This is not causal discovery and not a proof of causation.",
            "Consumer wearable errors can bias both treatment and outcome estimates.",
            "The demonstration dataset is synthetic and generated with its own structure.",
            "The interval reflects sampling uncertainty only; model-structure uncertainty is not included.",
            "Effects estimated in one individual over a short period may not generalize.",
            "A statistically visible association is not a treatment recommendation.",
        ],
        "alternative_explanations": [
            "Reverse causation (for example, a low HRV day changing activity or sleep).",
            "Unmeasured stress, illness, alcohol, travel, or environmental exposure.",
            "Regression to the mean and seasonal or weekly patterns.",
            "Device wear time and measurement artifacts.",
        ],
        "evidence": [source.model_dump(mode="json") for source in sources],
        "disclaimer": DISCLAIMER,
        "evidence_class": "experimental_hypothesis",
        "not_causal_proof": True,
        "intervention_semantics": "do(treatment = observed + delta); one measured confounder held at its observed value.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
