"""Pydantic request/response models.

Response models are deliberately explicit about provenance, range status,
uncertainty and synthetic/demo labeling so those concepts cannot be lost in the
UI layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Auth / profile
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    name: str = Field(min_length=2, max_length=120)
    accept_terms: bool
    ai_processing: bool = True
    research_participation: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Please provide your name")
        return cleaned

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must include at least one letter and one number")
        return value

    @field_validator("accept_terms")
    @classmethod
    def must_accept(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the terms and privacy notice to create an account")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: str
    role: str
    is_demo: bool
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    consent: "ConsentOut"


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    terms_accepted: bool
    ai_processing: bool
    research_participation: bool
    federated_learning: bool
    analytics: bool
    consent_version: str
    consented_at: datetime | None
    updated_at: datetime


class ConsentUpdate(BaseModel):
    ai_processing: bool | None = None
    research_participation: bool | None = None
    federated_learning: bool | None = None
    analytics: bool | None = None


class ConditionOut(BaseModel):
    name: str
    diagnosed_year: int | None = None
    status: str = "active"
    notes: str | None = None


class AllergyOut(BaseModel):
    substance: str
    reaction: str | None = None
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    source: str | None = None


class FamilyHistoryOut(BaseModel):
    relation: str
    condition: str
    age_at_onset: int | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_of_birth: str | None
    sex_at_birth: str | None
    gender_identity: str | None
    height_cm: float | None
    weight_kg: float | None
    blood_type: str | None
    ancestry_context: str | None
    smoking_status: str | None
    alcohol_units_per_week: float | None
    activity_level: str | None
    pregnancy_status: str | None
    conditions: list[dict] = Field(default_factory=list)
    allergies: list[dict] = Field(default_factory=list)
    family_history: list[dict] = Field(default_factory=list)
    notes: str | None = None
    is_synthetic: bool = False
    updated_at: datetime


class ProfileUpdate(BaseModel):
    date_of_birth: str | None = None
    sex_at_birth: str | None = None
    gender_identity: str | None = None
    height_cm: float | None = Field(default=None, ge=50, le=260)
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    blood_type: str | None = None
    ancestry_context: str | None = None
    smoking_status: str | None = None
    alcohol_units_per_week: float | None = Field(default=None, ge=0, le=200)
    activity_level: str | None = None
    pregnancy_status: str | None = None
    conditions: list[ConditionOut] | None = None
    allergies: list[AllergyOut] | None = None
    family_history: list[FamilyHistoryOut] | None = None
    notes: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def valid_dob(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            dob = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Date of birth must be YYYY-MM-DD") from exc
        if dob.year < 1900 or dob > datetime.now():
            raise ValueError("Date of birth is outside a supported range")
        return value


# ---------------------------------------------------------------------------
# Biomarkers / labs
# ---------------------------------------------------------------------------


class BiomarkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    category: str
    canonical_unit: str
    description: str
    specimen: str
    reference_note: str


RangeStatus = Literal["low", "normal", "high", "indeterminate"]


class LabResultOut(BaseModel):
    id: str
    biomarker_id: str
    code: str
    name: str
    category: str
    value: float
    unit: str
    display_value: str
    ref_low: float | None
    ref_high: float | None
    ref_text: str | None
    range_status: RangeStatus
    measured_at: datetime
    source: str
    method: str | None
    confidence: float
    quality_status: str
    notes: str | None
    context: dict
    is_synthetic: bool
    is_stale: bool
    age_days: int
    converted_from: str | None = None


class LabCreate(BaseModel):
    code: str
    value: float = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=32)
    measured_at: datetime
    ref_low: float | None = Field(default=None, ge=0)
    ref_high: float | None = Field(default=None, ge=0)
    ref_text: str | None = Field(default=None, max_length=120)
    source: str = Field(default="Self-entered", min_length=2, max_length=160)
    method: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def range_order(self) -> "LabCreate":
        if self.ref_low is not None and self.ref_high is not None and self.ref_low >= self.ref_high:
            raise ValueError("Reference low must be below reference high")
        return self


class LabUploadResult(BaseModel):
    imported: int
    skipped: int
    warnings: list[str]
    errors: list[str]
    results: list[LabResultOut]


class TrendPoint(BaseModel):
    date: datetime
    value: float
    ref_low: float | None
    ref_high: float | None
    source: str
    is_synthetic: bool


class TrendOut(BaseModel):
    code: str
    name: str
    unit: str
    category: str
    points: list[TrendPoint]
    latest: float | None
    previous: float | None
    absolute_change: float | None
    percent_change: float | None
    interpretation: str


# ---------------------------------------------------------------------------
# Genetics
# ---------------------------------------------------------------------------


class GeneticSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    file_name: str | None
    genome_build: str | None
    status: str
    variant_count: int
    is_synthetic: bool
    provenance: dict
    notes: str | None
    created_at: datetime


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    gene: str
    rsid: str
    chromosome: str | None
    position: int | None
    ref: str | None
    alt: str | None
    genotype: str
    zygosity: str
    star_allele: str | None
    consequence: str | None
    interpretation: str | None
    evidence_level: str
    source: str
    confidence: float
    is_synthetic: bool


class PhenotypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    gene: str
    diplotype: str
    phenotype: str
    activity_score: float | None
    evidence_level: str
    guideline: str | None
    interpretation: str
    medications: list
    limitations: str
    is_synthetic: bool
    source: str
    updated_at: datetime


class GeneticsOverview(BaseModel):
    samples: list[GeneticSampleOut]
    variants: list[VariantOut]
    phenotypes: list[PhenotypeOut]
    uninterpreted_genes: list[dict]
    gene_catalog: list[dict]
    disclaimer: str


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    generic_name: str
    drug_class: str
    atc_code: str | None
    mechanism_summary: str
    enzyme_pathways: list
    transporter_pathways: list
    half_life_hours: float | None
    route_options: list
    renal_fraction: float | None
    simulation_model: str
    warnings: list
    evidence_refs: list
    is_simulation_eligible: bool
    parameter_note: str


class ExposureCreate(BaseModel):
    medication_id: str
    dose_text: str = Field(min_length=1, max_length=80)
    route: str = Field(default="oral", max_length=32)
    frequency: str = Field(default="daily", max_length=64)
    start_date: str | None = None
    end_date: str | None = None
    reason: str | None = Field(default=None, max_length=160)
    prescriber_specialty: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class ExposureUpdate(BaseModel):
    status: Literal["active", "stopped", "paused"] | None = None
    dose_text: str | None = Field(default=None, min_length=1, max_length=80)
    frequency: str | None = Field(default=None, max_length=64)
    end_date: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ExposureOut(BaseModel):
    id: str
    medication_id: str
    name: str
    drug_class: str
    dose_text: str
    route: str
    frequency: str
    start_date: str | None
    end_date: str | None
    status: str
    reason: str | None
    prescriber_specialty: str | None
    notes: str | None
    is_synthetic: bool
    enzyme_pathways: list


class InteractionOut(BaseModel):
    id: str
    drug_a: str
    drug_b: str
    severity: str
    mechanism: str
    effect: str
    management: str
    evidence_level: str
    source_title: str
    source_url: str


# ---------------------------------------------------------------------------
# Wearables
# ---------------------------------------------------------------------------


class WearableDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    name: str
    connection_status: str
    last_synced_at: datetime | None
    is_synthetic: bool


class WearableMetricSummary(BaseModel):
    metric: str
    label: str
    unit: str
    latest: float | None
    average: float | None
    min_value: float | None
    max_value: float | None
    sample_count: int
    quality: str
    source: str


class WearableOverview(BaseModel):
    devices: list[WearableDeviceOut]
    metrics: list[WearableMetricSummary]
    integration_registry: list[dict]


# ---------------------------------------------------------------------------
# Twin
# ---------------------------------------------------------------------------


class TwinSignal(BaseModel):
    label: str
    value: str
    status: str
    meta: str | None = None


class TwinSystemSummary(BaseModel):
    id: str
    name: str
    tagline: str
    accent: str
    status: Literal["available", "review", "partial", "missing", "experimental"]
    status_reason: str
    completeness: int
    measurements: int
    genes: list[str]
    pathways: list[str]
    last_updated: datetime | None
    signals: list[TwinSignal]
    limitations: list[str]


class TwinOverview(BaseModel):
    systems: list[TwinSystemSummary]
    overall_completeness: int
    last_updated: datetime | None
    synthetic_data: bool
    disclaimer: str


class TwinSystemDetail(TwinSystemSummary):
    description: str
    measurements_detail: list[dict]
    genetic_factors: list[dict]
    risk_factors: list[str]
    connected_systems: list[str]
    evidence_quality: str
    uncertainty: str


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


class SimulationRequest(BaseModel):
    medication_id: str | None = None
    medication_name: str | None = Field(default=None, max_length=160)
    dose_text: str | None = Field(default="Label-listed dose (illustrative)", max_length=80)
    route: str = Field(default="oral", max_length=32)
    frequency: str = Field(default="single dose", max_length=64)
    context: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def identify_medication(self) -> "SimulationRequest":
        if not self.medication_id and not self.medication_name:
            raise ValueError("Provide a medication_id or medication_name")
        return self


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ExplainRequest(BaseModel):
    entity: str = Field(min_length=2, max_length=160)
    kind: Literal["auto", "biomarker", "gene", "medication", "system"] = "auto"


class CitationOut(BaseModel):
    id: str
    title: str
    organization: str
    url: str
    published_at: str | None
    evidence_level: str
    summary: str


class AnswerBlock(BaseModel):
    type: Literal["text", "bullets", "callout", "table"]
    title: str | None = None
    text: str | None = None
    items: list[str] | None = None
    rows: list[dict] | None = None
    tone: Literal["neutral", "info", "warning", "danger"] | None = None
    citations: list[str] = Field(default_factory=list)


class AssistantAnswer(BaseModel):
    answer: str
    blocks: list[AnswerBlock]
    citations: list[CitationOut]
    context_used: list[str]
    missing_information: list[str]
    follow_up_questions: list[str]
    engine: str
    intent: str
    disclaimer: str
    evidence_retrieval: list[dict]


# ---------------------------------------------------------------------------
# Privacy / federated
# ---------------------------------------------------------------------------


class ConsentState(BaseModel):
    consent: ConsentOut
    data_inventory: list[dict]
    privacy_budget: dict
    federated_rounds: list[dict]
    retention: str
    rights: list[str]


class DeleteRequest(BaseModel):
    confirmation: str
    password: str
    scope: Literal["health_data", "account"] = "health_data"


class FederatedRoundRequest(BaseModel):
    rounds: int = Field(default=3, ge=1, le=5)


class FederatedRoundResult(BaseModel):
    status: str
    rounds: list[dict]
    epsilon_spent_total: float
    epsilon_limit: float
    privacy_notes: list[str]
    simulation_notice: str


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    resource_type: str
    resource_id: str | None
    detail: dict
    created_at: datetime


class InsightOut(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    tone: Literal["neutral", "info", "warning"]
    evidence: str
    sources: list[CitationOut]
    data_basis: list[str]
    limitations: str


class SearchMedicationOut(BaseModel):
    id: str
    name: str
    generic_name: str
    drug_class: str
    is_simulation_eligible: bool


AuthResponse.model_rebuild()


class CausalRequest(BaseModel):
    treatment: Literal["sleep_duration", "steps"]
    outcome: Literal["hrv", "resting_hr"]
    delta: float = Field(default=0.5, ge=-100000, le=100000)
