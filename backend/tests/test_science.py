from __future__ import annotations

import math

import pytest

from app.services.federated import _pairwise_masks
from app.services.labs import classify_range
from app.services.pgx import normalize_phenotype
from app.services.units import UnitError, convert_to_canonical


def test_reference_range_classification_boundaries():
    assert classify_range(30, 7, 35) == "normal"
    assert classify_range(7, 7, 35) == "normal"
    assert classify_range(35, 7, 35) == "normal"
    assert classify_range(36, 7, 35) == "high"
    assert classify_range(6.9, 7, 35) == "low"
    assert classify_range(100, None, None) == "indeterminate"
    assert classify_range(100, 60, None) == "normal"
    assert classify_range(50, 60, None) == "low"


def test_unit_conversion_and_rejection():
    value, note = convert_to_canonical("glucose", 5.4, "mmol/L", "mg/dL")
    assert abs(value - 97.2983) < 0.001
    assert note and "mmol/L" in note
    hba1c, note = convert_to_canonical("hba1c", 42, "mmol/mol", "%")
    assert math.isclose(hba1c, 5.99, abs_tol=0.02)
    assert "NGSP" in (note or "")
    with pytest.raises(UnitError):
        convert_to_canonical("creatinine", 90, "bananas", "mg/dL")
    with pytest.raises(UnitError):
        convert_to_canonical("alt", 40, "mmol/L", "U/L")


def test_phenotype_normalization():
    assert normalize_phenotype("  Intermediate Metabolizer ") == "intermediate metabolizer"


def test_pairwise_masks_cancel():
    masks = _pairwise_masks((3,), 6, __import__("numpy").random.default_rng(5))
    total = masks[0].copy()
    for mask in masks[1:]:
        total += mask
    assert abs(float(total.sum())) < 1e-9


def test_engine_horizon_and_labels_are_documented(demo_client):
    data = demo_client.post(
        "/api/v1/simulations", json={"medication_id": "simvastatin"}
    ).json()["result"]
    assert data["model"]["status"] == "experimental"
    assert data["model"]["used"] is True
    assert data["curve"]["horizon_hours"] >= 24
    assert data["labels"]["established_clinical_evidence"] == "Established clinical evidence"
    assert data["labels"]["experimental_hypothesis"] == "Experimental hypothesis"
    assert data["labels"]["unknown"] == "Unknown"
    assert data["model"]["limitations"]
    assert data["uncertainty"]["statements"]
