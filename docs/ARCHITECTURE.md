# POLIS Architecture

## 1. System context

POLIS is a medical data application for research use, composed of:

- a Next.js 16 web client,
- a FastAPI/SQLAlchemy API,
- a relational database (SQLite for local development, PostgreSQL 16 + pgvector in Docker),
- local scientific services (evidence retrieval, pharmacogenomic interpretation, simulation, federated demonstration),
- an optional OpenAI-compatible LLM adapter.

```
┌────────────────────────────────────────────────────────────────────┐
│ Next.js client                                                     │
│  App Router · typed fetch client · auth gate · accessible UI       │
│  visual twin · charts · structured result renderer                 │
└───────────────┬────────────────────────────────────────────────────┘
                │ same-origin /api/v1 rewrite (HttpOnly cookie)
┌───────────────▼────────────────────────────────────────────────────┐
│ FastAPI                                                            │
│  auth · profile · labs · genetics · medications · twin             │
│  simulations · assistant · wearables · privacy · overview · models│
│                                                                    │
│  services: ingestion, units, PGx, twin, evidence, assistant,       │
│            simulation, federated, insights, seeding                │
└───────────────┬───────────────────────────┬────────────────────────┘
                │                           │
      ┌─────────▼─────────┐       ┌─────────▼──────────────────────┐
      │ SQLAlchemy models │       │ Scientific engines             │
      │ users + records   │       │ deterministic retrieval        │
      │ reference corpus  │       │ curated PGx + VCF annotation   │
      │ audit + consent   │       │ 1-compartment PK / index       │
      └─────────┬─────────┘       │ Monte Carlo + sensitivity      │
                │                 │ FedAvg demo + privacy ledger   │
      ┌─────────▼─────────┐       └─────────┬──────────────────────┘
      │ SQLite /          │                 │ optional
      │ PostgreSQL+pgvec  │          ┌──────▼─────────┐
      └───────────────────┘          │ LLM adapter    │
                                     │ strict context │
                                     │ + fallback     │
                                     └────────────────┘
```

## 2. Layered physiology architecture

The architecture is organized into five layers.

### Layer 1: Biological knowledge graph

Implemented as relational `kg_nodes` / `kg_edges` with typed relations (`encodes`, `metabolizes`, `inhibits`, `transports`, `participates_in`, etc.), an evidence level and a source on every edge. A small curated starter graph (42 nodes / 40 edges) supports explanation and navigation. It is not a complete biological network and is exposed with that limitation at `/api/v1/twin/knowledge-graph`.

### Layer 2: Mechanistic models

`services/simulation.py` implements:

- an explicitly educational **one-compartment oral PK** model with first-order absorption and elimination, and
- a **prodrug pathway index** for medicines where active-metabolite formation, not parent exposure, is the relevant mechanistic quantity.

Parameters are curated `Medication.simulation_config` entries with source notes. The API returns `parameter_sources` so every UI estimate can show its published starting point. This is not a PBPK model. A full PBPK architecture would require tissue compartments, blood flows, partition coefficients, transporter expression and observed-data qualification.

### Layer 3: Personalization

The engine maps available data to model modifiers only where a transparent rule is defined:

- curated PGx phenotype → illustrative enzyme-activity multiplier per pathway contribution,
- phenotype contribution fractions from the curated drug record,
- eGFR → renal-fraction clearance scaling,
- body weight → apparent volume and allometric clearance approximation,
- marked liver-chemistry abnormality → bounded illustrative hepatic clearance reduction,
- curated inhibitor/inducer interactions → pathway modifiers for the proposed medicine.

Every modifier is returned with its source, value, classification and whether it was an assumption. Missing genotypes are not silently treated as normal; the assumption is labelled and an uncertainty penalty is applied.

### Layer 4: Causal modeling

A narrow **experimental causal lab** is implemented in `services/causal.py` and exposed at `/api/v1/causal`:

- a small explicit DAG for sleep/steps → HRV/resting heart rate,
- a linear structural equation with one measured confounder fitted to complete within-person wearable days,
- do-operator semantics (`do(T = observed + delta)`) with the confounder held at its observed value,
- bootstrap 5th to 95th percentile intervals,
- explicit assumptions, limitations, alternative explanations and complete-case accounting,
- a structured `insufficient_data` outcome rather than imputation.

It is **not** causal discovery, does not adjust an arbitrary graph, and makes a strong no-unmeasured-confounding assumption. The interface labels the result `experimental_hypothesis` and states that it is not causal proof. No clinical decision can be derived from it.

The broader system still sharply distinguishes:

- curated associations and mechanistic edges,
- simulation model estimates (one-compartment PK, pathway index),
- the experimental causal counterfactual,
- model-parameter sensitivity (explicitly not causal),
- observed trends and missing data.

Future work: arbitrary DAGs, back-door adjustment, time-varying confounding, instrumental variables, mediation, counterfactual sensitivity to unmeasured confounding and external validation.

### Layer 5: Model validation

The `model_versions` table and `/api/v1/models` registry record version, status (`experimental`, `research-use-demo`, `simulation-only`), limitations and validation summary. No model is marked clinically validated. Unit, reproducibility, boundary and isolation tests exist; external calibration, discrimination, subgroup performance, drift and prospective validation do not.

## 3. Backend structure

```
backend/app/
  main.py                 application factory, middleware, lifespan, routers
  core/
    config.py             env-driven pydantic-settings
    db.py                 engine/session + SQLite foreign keys/WAL
    security.py           scrypt, JWT, cookie/bearer auth, current-user dependency
    limits.py             in-process sliding-window rate limiter
  models.py               SQLAlchemy 2.0 mapped models + UTCDateTime
  schemas.py              Pydantic validation and API contracts
  api/
    auth.py profile.py labs.py genetics.py medications.py
    twin.py simulations.py assistant.py wearables.py
    causal.py privacy.py overview.py models.py
  services/
    seed.py               idempotent reference + synthetic demo seeding
    units.py              explicit unit conversion and rejection
    labs.py               classification, serialization, trends
    ingestion.py          CSV / FHIR / PDF parsers
    pgx.py                phenotype maps, conservative VCF annotation
    twin.py               organ status, completeness, details
    drugs.py              catalog, exposures, curated interactions
    simulation.py         PK/index, modifiers, Monte Carlo, sensitivity
    causal.py             experimental DAG + structural equation + do-operator
    evidence.py           hashed embedding + lexical hybrid retrieval
    assistant.py          intents, grounded composition, citation control
    llm.py                optional provider adapter with fallback
    federated.py          FedAvg demonstration + DP/privacy ledger
    insights.py           evidence-linked observations
    audit.py              action logging without health free text
```

Routes are mounted under `/api/v1`; OpenAPI is served at `/api/docs`.

## 4. Database schema

Core patient-owned entities:

- `users`, `user_consents`, `health_profiles`
- `genetic_samples`, `genetic_variants`, `pharmacogenomic_phenotypes`
- `lab_results` → `biomarkers`
- `medication_exposures` → `medications`; `drug_interactions`
- `wearable_devices`, `wearable_measurements`
- `simulations`
- causal queries are audited rather than stored as new patient datasets
- `federated_training_rounds`, `privacy_budgets`
- `audit_logs`

Reference/read-mostly entities:

- `biological_systems`, `biological_pathways`
- `kg_nodes`, `kg_edges`
- `evidence_sources`
- `model_versions`

Every patient-owned row has `user_id`, timestamps, provenance/quality fields and `is_synthetic` where relevant. Cascades delete dependent records when an account is removed. SQLite foreign keys are enabled explicitly at connection time.

### Time handling

`UTCDateTime` is a SQLAlchemy type decorator that always returns timezone-aware UTC datetimes. This prevents SQLite's loss of timezone information from shifting timestamps in the browser.

### Migrations

Alembic owns schema evolution. The initial migration lives in `backend/alembic/versions/`. Causal queries are not persisted as a separate table; they use existing wearable data and produce an audit entry. The development app also calls `Base.metadata.create_all` at startup for zero-config use; production Docker runs `alembic upgrade head` before starting the API.

## 5. Authentication and tenant isolation

- Registration: name, email, strong password, explicit terms acceptance, optional AI/research consent.
- Passwords: scrypt (`N=2^14`, `r=8`, `p=1`) with 16-byte salts, stored as versioned strings.
- Sessions: HS256 JWT with issuer/audience checks, delivered as an HttpOnly, SameSite=Lax cookie. API clients may use Bearer tokens.
- Every protected dependency resolves the user from the token and loads the account.
- Every health query includes `user_id == current_user.id`; tests verify cross-user denial for labs, genetics, simulations, assistant context and export.
- Cookies are `Secure` when configured; production also requires a non-default secret.

## 6. Laboratory pipeline

1. Ingest: manual, CSV, FHIR Observation/Bundle or text PDF.
2. Validate: code/name, numeric value, explicit unit, explicit date, laboratory interval.
3. Normalize: supported units convert together with their interval; unsupported units are rejected. The original unit is stored in provenance and returned as `converted_from`.
4. Classify: against the result's own interval only. Missing interval → `indeterminate`.
5. Persist: quality status (`self_reported`, `unverified_import`, `needs_review`, `demonstration`), source, method, confidence, context and provenance.
6. Present: latest table, history chart, interval band, source and quality.

PDF extraction is heuristic and marked needs review. Scanned PDFs are rejected because OCR is not enabled.

## 7. Pharmacogenomics

- Curated demo diplotypes use CPIC/PharmVar terminology and explicit limitations.
- VCF uploads are parsed for a small curated panel and stored as variant annotations.
- **No diplotype or phenotype is inferred from a VCF.** Star-allele calling, phasing, copy-number and hybrid-gene detection require a validated laboratory pipeline.
- Phenotypes are linked to medications for explanation only. No dose recommendation is generated.

## 8. Simulation engine

See [SCIENTIFIC_LIMITATIONS.md](SCIENTIFIC_LIMITATIONS.md) for equations and evidence.

Request flow:

1. Resolve medication or return a structured refusal/404.
2. Collect phenotypes, latest labs, active medications, allergies, weight, age and renal context.
3. Check curated interactions and allergy-name overlap.
4. Build modifier inputs; label known vs assumed.
5. Run 1,600 Monte Carlo draws (normalized, no absolute concentration) or the pathway index.
6. Compute 5th to 95th percentile intervals, metrics, sensitivity drivers.
7. Retrieve evidence chunks and attach only retrieved citations.
8. Persist input/output/evidence snapshot with engine version and timestamp.
9. Return reasoning steps, safety flags, assumptions, missing data and clinician questions.

No code path calculates a personalized dose.

## 9. Grounded assistant

- Intent classification is rule-based and safety-first (emergency, medication-change refusal, prompt-injection boundary, then domain intents).
- Facts are pulled from the current user's records only.
- Retrieval uses deterministic 384-dimensional hashed token/bigram embeddings plus lexical overlap and tag boosts.
- Answers are assembled from structured blocks; citations must be present in the retrieved set and are filtered again before response.
- If a question cannot be grounded, the assistant returns `insufficient_information`.
- Optional external generation receives only the prepared context/evidence, must return JSON, and is validated; any failure falls back to deterministic synthesis.
- Message text is not written to audit logs; only intent, length and engine metadata are stored.

## 10. Federated demonstration

Implemented entirely in-process over synthetic clients:

- local logistic-regression training,
- update L2 clipping,
- calibrated Gaussian noise,
- simulated additive pairwise masks that sum to zero,
- FedAvg aggregation,
- synthetic holdout evaluation,
- basic-composition epsilon accounting persisted in `privacy_budgets`.

This is not production secure aggregation and has no formal end-to-end DP proof. It is labelled accordingly in API output, UI and documentation.

## 11. Frontend architecture

- Next.js App Router with client-side data fetching through a same-origin proxy.
- AuthProvider validates `/auth/me`, routes unauthorized users to login, and listens for 401 events.
- Typed API client for errors, uploads, exports.
- Design system: panels, badges, status pills, callouts, sheets, tabs, charts.
- The Digital Twin uses a CC BY 4.0 anatomical illustration from DBCLS, recoloured into a muted bone-toned treatment with keyboard-selectable navigation anchors and explicit "navigation only" labeling. Attribution is retained in the UI and `frontend/public/anatomy/NOTICE.md`.
- The body is an explanatory interface, never a scan or an image of a real person's organs.
- Recharts for biomarker/wearable trends and exposure bands.
- Causal Lab (inside Insights) with controls, DAG, counterfactual estimate, fitted-line scatter and assumption/limitation panels.
- Every result renderer carries evidence-class labels and explicit uncertainty copy.
- Mobile navigation uses a drawer; layouts stack at defined breakpoints.

## 12. Reliability & deployment

- Health endpoint `/health`.
- Docker healthchecks for API and web.
- SQLite WAL and foreign keys for local reliability.
- Postgres volume and initial pgvector extension in Docker.
- Seed operation is idempotent and versioned reference data is upserted at startup.
- Production guard rejects the development secret.
- TLS is expected at the reverse proxy; HSTS should be added there. See security docs.

## 13. Key architecture decisions

| Decision | Rationale |
|---|---|
| Deterministic RAG default | Works without credentials; auditable citations; no raw egress |
| Local JSON embeddings, pgvector-ready schema | Portable MVP; no external embedding dependency; honest claim |
| SQLite dev / Postgres prod | Zero-setup onboarding; production-grade relational store |
| Curated formulary | Avoids presenting uncurated medication information as authoritative |
| Structured refusals | Safer than generating estimates for high-risk medicines |
| No dose calculation | Regulatory and safety boundary; simulations are normalized |
| Curated demo diplotypes + no VCF phenotype inference | Avoids clinically dangerous overreach |
| In-process FedAvg demo | Demonstrates mechanics without pretending production privacy infrastructure exists |

## 14. Scalability path

- Move rate limiting and caching to Redis.
- Add pgvector-backed embedding retrieval and a versioned ingestion pipeline for evidence updates.
- Replace curated starter graph with a provenance-rich graph service.
- Add a validated star-allele caller and clinical genetics integration.
- Add a PBPK model registry with observed-data qualification and external validation.
- Move federated orchestration to a real coordinator with cryptographic secure aggregation and a formal DP accountant.
- Add background workers for imports, model runs and audit export.

None of these are claimed to exist today.
