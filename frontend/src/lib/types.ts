export type User = {
  id: string;
  email: string;
  name: string;
  role: string;
  is_demo: boolean;
  created_at: string;
};

export type Consent = {
  terms_accepted: boolean;
  ai_processing: boolean;
  research_participation: boolean;
  federated_learning: boolean;
  analytics: boolean;
  consent_version: string;
  consented_at: string | null;
  updated_at: string;
};

export type AuthResponse = { user: User; consent: Consent };

export type Condition = {
  name: string;
  diagnosed_year?: number | null;
  status?: string;
  notes?: string | null;
};

export type Allergy = {
  substance: string;
  reaction?: string | null;
  severity?: "mild" | "moderate" | "severe" | "unknown";
  source?: string | null;
};

export type FamilyHistory = {
  relation: string;
  condition: string;
  age_at_onset?: number | null;
};

export type Profile = {
  date_of_birth: string | null;
  sex_at_birth: string | null;
  gender_identity: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  blood_type: string | null;
  ancestry_context: string | null;
  smoking_status: string | null;
  alcohol_units_per_week: number | null;
  activity_level: string | null;
  pregnancy_status: string | null;
  conditions: Condition[];
  allergies: Allergy[];
  family_history: FamilyHistory[];
  notes: string | null;
  is_synthetic: boolean;
  updated_at: string;
};

export type RangeStatus = "low" | "normal" | "high" | "indeterminate";

export type LabResult = {
  id: string;
  biomarker_id: string;
  code: string;
  name: string;
  category: string;
  value: number;
  unit: string;
  display_value: string;
  ref_low: number | null;
  ref_high: number | null;
  ref_text: string | null;
  range_status: RangeStatus;
  measured_at: string;
  source: string;
  method: string | null;
  confidence: number;
  quality_status: string;
  notes: string | null;
  context: Record<string, unknown>;
  is_synthetic: boolean;
  is_stale: boolean;
  age_days: number;
  converted_from: string | null;
};

export type Biomarker = {
  id: string;
  code: string;
  name: string;
  category: string;
  canonical_unit: string;
  description: string;
  specimen: string;
  reference_note: string;
};

export type TrendPoint = {
  date: string;
  value: number;
  ref_low: number | null;
  ref_high: number | null;
  source: string;
  is_synthetic: boolean;
};

export type Trend = {
  code: string;
  name: string;
  unit: string;
  category: string;
  points: TrendPoint[];
  latest: number | null;
  previous: number | null;
  absolute_change: number | null;
  percent_change: number | null;
  interpretation: string;
};

export type Citation = {
  id: string;
  title: string;
  organization: string;
  url: string;
  published_at: string | null;
  evidence_level: string;
  summary: string;
};

export type Insight = {
  id: string;
  title: string;
  summary: string;
  category: string;
  tone: "neutral" | "info" | "warning";
  evidence: string;
  sources: Citation[];
  data_basis: string[];
  limitations: string;
};

export type TwinSignal = {
  label: string;
  value: string;
  status: string;
  meta: string | null;
};

export type TwinSystem = {
  id: string;
  name: string;
  tagline: string;
  accent: string;
  status: "available" | "review" | "partial" | "missing" | "experimental";
  status_reason: string;
  completeness: number;
  measurements: number;
  genes: string[];
  pathways: string[];
  last_updated: string | null;
  signals: TwinSignal[];
  limitations: string[];
};

export type TwinOverview = {
  systems: TwinSystem[];
  overall_completeness: number;
  last_updated: string | null;
  synthetic_data: boolean;
  disclaimer: string;
};

export type TwinMeasurementDetail = {
  kind: "lab" | "wearable";
  code: string;
  name: string;
  status: string;
  value: number | null;
  unit: string | null;
  date: string | null;
  ref_low?: number | null;
  ref_high?: number | null;
  ref_text?: string | null;
  source: string | null;
  method?: string | null;
  quality_status?: string;
  confidence?: number;
  is_synthetic?: boolean;
  label: string;
};

export type TwinSystemDetail = TwinSystem & {
  description: string;
  measurements_detail: TwinMeasurementDetail[];
  genetic_factors: {
    gene: string;
    diplotype: string;
    phenotype: string;
    guideline: string | null;
    evidence_level: string;
    is_synthetic: boolean;
    interpretation: string;
    limitations: string;
  }[];
  risk_factors: string[];
  connected_systems: string[];
  evidence_quality: string;
  uncertainty: string;
};

export type Variant = {
  id: string;
  gene: string;
  rsid: string;
  chromosome: string | null;
  position: number | null;
  ref: string | null;
  alt: string | null;
  genotype: string;
  zygosity: string;
  star_allele: string | null;
  consequence: string | null;
  interpretation: string | null;
  evidence_level: string;
  source: string;
  confidence: number;
  is_synthetic: boolean;
};

export type Phenotype = {
  id: string;
  gene: string;
  diplotype: string;
  phenotype: string;
  activity_score: number | null;
  evidence_level: string;
  guideline: string | null;
  interpretation: string;
  medications: { name: string; relevance: string; status: string }[];
  limitations: string;
  is_synthetic: boolean;
  source: string;
  updated_at: string;
};

export type GeneticSample = {
  id: string;
  source: string;
  file_name: string | null;
  genome_build: string | null;
  status: string;
  variant_count: number;
  is_synthetic: boolean;
  provenance: Record<string, unknown>;
  notes: string | null;
  created_at: string;
};

export type GeneInfo = {
  symbol: string;
  name: string;
  chromosome: string;
  role: string;
  complexity: string;
  resources: string[];
  color: string;
};

export type GeneticsOverview = {
  samples: GeneticSample[];
  variants: Variant[];
  phenotypes: Phenotype[];
  uninterpreted_genes: { gene: string; status: string; reason: string }[];
  gene_catalog: GeneInfo[];
  disclaimer: string;
};

export type MedicationCatalog = {
  id: string;
  name: string;
  generic_name: string;
  drug_class: string;
  is_simulation_eligible: boolean;
};

export type Medication = MedicationCatalog & {
  atc_code: string | null;
  mechanism_summary: string;
  enzyme_pathways: { gene: string; role: string; contribution?: number; evidence?: string }[];
  transporter_pathways: { gene: string; role: string; evidence?: string }[];
  half_life_hours: number | null;
  route_options: string[];
  renal_fraction: number | null;
  simulation_model: string;
  warnings: string[];
  evidence_refs: string[];
  parameter_note: string;
};

export type Exposure = {
  id: string;
  medication_id: string;
  name: string;
  drug_class: string;
  dose_text: string;
  route: string;
  frequency: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  reason: string | null;
  prescriber_specialty: string | null;
  notes: string | null;
  is_synthetic: boolean;
  enzyme_pathways: { gene: string; role: string }[];
};

export type Interaction = {
  id: string;
  drug_a: string;
  drug_b: string;
  severity: "contraindicated" | "major" | "moderate" | "minor" | string;
  mechanism: string;
  effect: string;
  management: string;
  evidence_level: string;
  source_title: string;
  source_url: string;
};

export type WearableMetric = {
  metric: string;
  label: string;
  unit: string;
  latest: number | null;
  average: number | null;
  min_value: number | null;
  max_value: number | null;
  sample_count: number;
  quality: string;
  source: string;
};

export type WearableDevice = {
  id: string;
  provider: string;
  name: string;
  connection_status: string;
  last_synced_at: string | null;
  is_synthetic: boolean;
};

export type Integration = {
  provider: string;
  name: string;
  status: string;
  detail: string;
};

export type WearableOverview = {
  devices: WearableDevice[];
  metrics: WearableMetric[];
  integration_registry: Integration[];
};

export type SeriesPoint = { date: string; value: number; is_synthetic: boolean };
export type WearableSeries = {
  metric: string;
  label: string;
  unit: string;
  quality: string;
  source: string | null;
  points: SeriesPoint[];
  data_quality_note: string;
};

export type SimulationSummaryMetric = {
  key: string;
  label: string;
  value: number;
  low: number;
  high: number;
  unit: string;
  classification: string;
  note: string;
};

export type SimulationInteraction = {
  id: string;
  drug_a: string;
  drug_b: string;
  other_medication: string;
  severity: string;
  mechanism: string;
  effect: string;
  management: string;
  evidence_level: string;
  source_title: string;
  source_url: string;
  applies_to_proposed_simulation: boolean;
};

export type SimulationEvidence = Citation & {
  snippet?: string;
  retrieval_score?: Record<string, number>;
};

export type SimulationModelInput = {
  label: string;
  value: string;
  source: string;
  classification: string;
  used: boolean;
  detail: string;
};

export type ReasoningStep = {
  order: number;
  title: string;
  status: string;
  detail: string;
  evidence_class: string;
};

export type SafetyFlag = {
  severity: "danger" | "warning" | "info" | string;
  title: string;
  detail: string;
};

export type SimulationResult = {
  status: string;
  headline: string;
  reason?: string;
  model: {
    name: string;
    version: string;
    status: string;
    used: boolean;
    confidence?: string;
    description?: string;
    limitations?: string;
  };
  medication: {
    id: string;
    name: string;
    generic_name: string;
    drug_class: string;
    mechanism_summary: string;
    enzyme_pathways: { gene: string; role: string; contribution?: number }[];
    transporter_pathways?: { gene: string; role: string }[];
    half_life_hours?: number | null;
    warnings: string[];
    parameter_note?: string;
    simulation_model?: string;
    parameter_sources?: { parameter: string; value: string; source: string }[];
  };
  summary_metrics?: SimulationSummaryMetric[];
  curve?: {
    times: number[];
    median: number[];
    p05: number[];
    p95: number[];
    reference: number[];
    x_label: string;
    y_label: string;
    horizon_hours: number;
    classification: string;
    note: string;
  } | null;
  pathway_index?: {
    label: string;
    value: number;
    low: number;
    high: number;
    reference: number;
    contributions: {
      gene: string;
      phenotype: string;
      weight: number;
      activity_factor: number;
      interaction_factor: number;
      contribution: number;
      known: boolean;
    }[];
    basis: string;
    classification: string;
    note: string;
  } | null;
  model_inputs?: SimulationModelInput[];
  sensitivity?: {
    method: string;
    drivers: {
      parameter: string;
      change: string;
      effect_low: number;
      effect_high: number;
      unit: string;
      known: boolean;
    }[];
    not_causal: boolean;
    note: string;
  };
  pgx?: {
    gene: string;
    role: string;
    contribution: number;
    phenotype: string;
    diplotype: string | null;
    activity_factor: number;
    known: boolean;
    interaction_factor: number;
    evidence: string;
    evidence_class: string;
    is_synthetic: boolean;
    limitations: string;
  }[];
  active_medications?: { name: string; dose: string; frequency: string; is_synthetic: boolean }[];
  interactions: SimulationInteraction[];
  allergy_flags: {
    substance: string;
    reaction: string;
    severity: string;
    classification: string;
    statement: string;
  }[];
  missing_information: string[];
  assumptions: string[];
  uncertainty?: {
    level: string;
    statements: string[];
    interval_definition: string;
  };
  pharmacokinetics?: {
    absorption: string;
    distribution: string;
    metabolism: string;
    elimination: string;
    personalization: string;
  };
  reasoning_steps: ReasoningStep[];
  evidence: SimulationEvidence[];
  clinician_questions: string[];
  safety_flags: SafetyFlag[];
  data_quality?: Record<string, unknown>;
  disclaimer: string;
  synthetic_data: boolean;
  labels?: Record<string, string>;
};

export type SimulationResponse = {
  id: string;
  created_at: string;
  status: string;
  engine_version: string;
  input: Record<string, unknown>;
  result: SimulationResult;
  evidence: SimulationEvidence[];
};

export type AnswerBlock = {
  type: "text" | "bullets" | "callout" | "table";
  title: string | null;
  text: string | null;
  items: string[] | null;
  rows: Record<string, string>[] | null;
  tone: "neutral" | "info" | "warning" | "danger" | null;
  citations: string[];
};

export type AssistantAnswer = {
  answer: string;
  blocks: AnswerBlock[];
  citations: Citation[];
  context_used: string[];
  missing_information: string[];
  follow_up_questions: string[];
  engine: string;
  intent: string;
  disclaimer: string;
  evidence_retrieval: {
    id: string;
    title: string;
    organization: string;
    score: number;
    components: Record<string, number>;
    verification_required: boolean;
  }[];
};

export type AssistantStatus = {
  ai_processing_consent: boolean;
  engine: string;
  external_llm_configured: boolean;
  retrieval: string;
  disclaimer: string;
};

export type DataInventory = { resource: string; count: number };

export type FederatedRound = {
  id: string;
  round: number;
  participants: number;
  epsilon: number;
  loss: number;
  accuracy: number;
  status: string;
  created_at: string;
};

export type ConsentState = {
  consent: Consent;
  data_inventory: DataInventory[];
  privacy_budget: { epsilon_spent: number; epsilon_limit: number; label: string };
  federated_rounds: FederatedRound[];
  retention: string;
  rights: string[];
};

export type AuditEntry = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export type FederatedResult = {
  status: string;
  rounds: {
    round: number;
    participants: number;
    loss: number;
    accuracy: number;
    epsilon: number;
    epsilon_spent_cumulative: number;
    mechanism: string;
  }[];
  epsilon_spent_total: number;
  epsilon_limit: number;
  privacy_notes: string[];
  simulation_notice: string;
};

export type Overview = {
  user: { name: string; is_demo: boolean; email: string };
  profile: {
    age: number | null;
    sex_at_birth: string | null;
    height_cm: number | null;
    weight_kg: number | null;
    blood_type: string | null;
    conditions: string[];
    allergies: string[];
    is_synthetic: boolean;
  };
  synthetic_notice: string | null;
  twin: TwinOverview;
  latest_labs: LabResult[];
  trends: Trend[];
  wearables: {
    devices: { provider: string; name: string; status: string; is_synthetic: boolean }[];
    summary: {
      metric: string;
      average_14d: number;
      latest: number;
      unit: string;
      quality: string;
      samples: number;
    }[];
    last_sample: string | null;
  };
  active_medications: {
    id: string;
    medication_id: string;
    name: string;
    dose_text: string;
    frequency: string;
    drug_class: string;
    is_synthetic: boolean;
  }[];
  insights: Insight[];
  recent_simulations: {
    id: string;
    medication_name: string;
    status: string;
    created_at: string;
    headline: string | null;
  }[];
  data_status: {
    last_laboratory: string | null;
    last_wearable_sample: string | null;
    wearable_ingestion: string;
    genetic_source: string | null;
    data_completeness: number;
    not_a_health_score: boolean;
  };
  privacy: {
    ai_processing: boolean;
    research_participation: boolean;
    federated_learning: boolean;
  };
  suggested_simulations: { medication_id: string; label: string; reason: string }[];
  generated_at: string;
  disclaimer: string;
};

export type ApiError = { detail?: string | { message?: string; errors?: string[]; warnings?: string[] } };

export type ModelVersion = {
  id: string;
  name: string;
  version: string;
  status: string;
  description: string;
  limitations: string;
  validation_summary: string;
  clinically_validated: boolean;
};

export type ModelRegistry = {
  models: ModelVersion[];
  validation_policy: string;
};


export type CausalTreatment = {
  code: string;
  label: string;
  unit: string;
  default_delta: number;
  min_delta: number;
  max_delta: number;
  delta_step: number;
  source: string;
  outcomes: string[];
};

export type CausalOutcome = {
  code: string;
  label: string;
  unit: string;
  direction_note: string;
};

export type CausalCatalog = {
  treatments: CausalTreatment[];
  outcomes: CausalOutcome[];
  minimum_days: number;
  method: string;
  evidence_class: string;
  disclaimer: string;
};

export type CausalPoint = {
  date: string;
  treatment: number;
  outcome: number;
  confounder: number;
};

export type CausalResult = {
  status: string;
  reason?: string;
  available_days: number;
  excluded_days?: number;
  treatment?: CausalTreatment;
  outcome?: CausalOutcome;
  delta?: number;
  observed?: { treatment_mean: number; outcome_mean: number; confounder_mean: number };
  model?: {
    name: string;
    version: string;
    coefficient: number;
    intercept: number;
    confounder_coefficient: number;
    r_squared: number;
    n_days: number;
    equation: string;
    evidence_class: string;
  };
  estimate?: {
    value: number;
    low: number;
    high: number;
    unit: string;
    direction: string;
    label: string;
    interval_definition: string;
  };
  dag?: {
    nodes: { id: string; label: string; role: string }[];
    edges: { source: string; target: string; label: string; assumption: string }[];
  };
  points?: CausalPoint[];
  assumptions?: string[];
  limitations?: string[];
  alternative_explanations?: string[];
  evidence?: Citation[];
  disclaimer?: string;
  evidence_class?: string;
  not_causal_proof?: boolean;
  intervention_semantics?: string;
  missing_information?: string[];
  generated_at?: string;
};

export type WearableImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
  warnings: string[];
  device: WearableDevice;
  notice: string;
};
