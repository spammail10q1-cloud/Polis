# POLIS

**Your body. Your biology. Your digital twin.**

POLIS is a privacy-first, evidence-grounded research platform for building a continuously updatable computational model of an individual's biology. It combines a longitudinal health record, pharmacogenomic interpretation, a structured physiological simulation workspace, longitudinal laboratory intelligence and a retrieval-grounded assistant.

> **Safety boundary:** POLIS is an experimental research prototype, not a medical device. It does not diagnose, prescribe, recommend doses, or tell anyone to start, stop or change a medicine. All demonstration data are synthetic. Clinical decisions must involve qualified healthcare professionals.

---

## What is implemented

- **Restrained dark interface** with 12 product modules, responsive navigation, a licensed anatomical navigation model with visible attribution and accessible structured-result views.
- **Authentication and tenant isolation** using scrypt password hashing, HttpOnly JWT sessions, cookie-or-bearer authentication and account-scoped queries on every health record.
- **Personal biological profile** with demographics, conditions, allergies and family history.
- **Laboratory intelligence**: manual entry, CSV, FHIR JSON and text-PDF import; strict unit handling; per-result laboratory reference intervals; historical trends; deletion; explicit indeterminate states.
- **Pharmacogenomics**: curated synthetic diplotypes for 10 pharmacogenes, conservative VCF annotation that **never** infers a phenotype from a raw VCF, variant-level provenance and limitations.
- **Digital body** with 10 interactive systems, data completeness, statuses based on data availability and laboratory intervals, genetic context, limitations and uncertainty.
- **Causal lab** inside Insights: an explicit DAG, a do-operator intervention, linear structural equation with one measured confounder, bootstrap intervals, sensitivity to assumptions, and alternative explanations. It is exploratory and never presented as causal proof.
- **What If?** simulation workspace with:
  - curated medication catalog and interaction screening,
  - phenotype, liver, kidney, weight and interaction modifiers,
  - experimental one-compartment oral PK visualization and prodrug pathway index,
  - Monte Carlo uncertainty bands,
  - local sensitivity analysis,
  - missing-data and assumption inventory,
  - cited evidence, safety flags and clinician questions,
  - structured refusal for high-risk medicines where a simplified model would mislead.
- **POLIS AI**: deterministic, grounded synthesis over the user's data and a local curated evidence corpus. Optional OpenAI-compatible provider abstraction with strict validation and fallback. Citations only come from retrieved sources.
- **Federated learning demonstration**: actual local training over synthetic clients, clipping, Gaussian noise, additive pairwise masks, FedAvg, per-round evaluation and a privacy-budget ledger. Clearly labelled as a simulation, not production secure aggregation.
- **Privacy controls**: independent AI/research/federated/analytics consent, machine-readable export, health-data deletion, account deletion and an audit trail.
- **Testing**: 62 backend tests, 10 frontend component/unit tests and 10 Playwright end-to-end journeys, including a cross-tenant isolation proof.
- **Docker Compose** with PostgreSQL/pgvector, FastAPI and the Next.js frontend.

See [DESIGN.md](DESIGN.md) for the visual direction and [docs/SCIENTIFIC_LIMITATIONS.md](docs/SCIENTIFIC_LIMITATIONS.md) before interpreting any simulation.

---

## Screens

| Module | Purpose |
|---|---|
| Overview | Twin visual, available signals, changes, medications, insights and completeness |
| My Biology | Structured profile, clinical context, data domains and provenance |
| Digital Twin | Interactive system navigation with measurements, genes, uncertainty |
| What If? | Medication context, mechanism, interactions, model estimates and evidence |
| Genetics | Phenotypes, diplotypes, variants, limitations and VCF upload |
| Biomarkers | Laboratory results, local intervals, histories and imports |
| Medications | Active/history regimen, mechanisms and curated interaction screen |
| Wearables | Sample time series, CSV import, data-quality labels and integration readiness |
| Insights | Evidence-linked observations plus an experimental do-operator causal lab |
| POLIS AI | Grounded research thread with citations and unknowns |
| Privacy & Data | Consent, inventory, export, deletion, audit and federated lab |
| Settings | Profile maintenance, account and model registry |

The demo account is fully synthetic and marked throughout the UI.

---

## Quick start (local)

### Prerequisites

- Python 3.12+ (tested on Python 3.14)
- Node.js 20.9+ (tested on Node 22)
- npm
- Optional: Docker + Docker Compose for PostgreSQL

### 1. Install

```bash
cd /path/to/Polis
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm install && cd ..
cp .env.example .env
```

Edit `.env` and set a real `SECRET_KEY` for anything beyond local development:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

The default SQLite configuration requires no database server. Keep `DATABASE_URL=sqlite:///./polis.db` and start the backend from `backend/` (the next step does this), or use an absolute SQLite URL.

### 2. Run the API

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/api/docs
- Health: http://127.0.0.1:8000/health

The first start seeds the curated reference corpus and the synthetic demonstration account. It can take several seconds.

### 3. Run the web app

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://127.0.0.1:3000.

### 4. Sign in

Use **Explore the demonstration twin** on the login page, or:

```
Email:    demo@polis.health
Password: PolisDemo!2026
```

New registrations start with an empty profile and no AI consent enabled.

---

## Testing

### Backend

```bash
cd backend
../.venv/bin/python -m pytest
```

Covers authentication, tenant isolation, uploads/unit validation, consent enforcement, simulation boundaries, assistant grounding, export/deletion, federated consent and the model registry.

### Frontend

```bash
cd frontend
npx tsc --noEmit
npm test
npm run build
```

### End-to-end

With the backend available (the Playwright config can start it):

```bash
cd frontend
npx playwright install chromium
npm run e2e
```

The ten journeys verify demo login/overview, the clopidogrel What If? workflow, grounded ALT assistant response, privacy export, mobile navigation, registration/consent onboarding, manual laboratory ingestion, federated opt-in, the causal lab and wearable CSV import.

### Migrations

```bash
cd backend
../.venv/bin/alembic upgrade head
DATABASE_URL=sqlite:///./fresh.db ../.venv/bin/alembic upgrade head
```

---

## Docker Compose

```bash
cp .env.example .env
# Set SECRET_KEY and POSTGRES_PASSWORD in .env
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000
- PostgreSQL with pgvector: internal `db` service

The backend runs Alembic migrations on startup. For a real deployment, set `DEMO_SEED=false`, use TLS, set `COOKIE_SECURE=true`, pin exposed ports, and follow the hardening checklist in [docs/SECURITY.md](docs/SECURITY.md).

---

## Configuration

All settings are environment variables (see `.env.example`). Important values:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///.../polis.db` | SQLAlchemy database URL |
| `SECRET_KEY` | development placeholder | JWT signing; required unique value in production |
| `ENVIRONMENT` | `development` | Enables production guards |
| `COOKIE_SECURE` | `false` | Set true behind HTTPS |
| `CORS_ORIGINS` | localhost:3000 origins | Browser origins |
| `DEMO_SEED` | `true` | Create the synthetic demo account |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | demo values | Demonstration credentials |
| `ALLOW_REGISTRATION` | `true` | Account creation |
| `LLM_PROVIDER` | `deterministic` | `deterministic` or an OpenAI-compatible provider |
| `LLM_API_KEY` | empty | Optional external model key |
| `FEDERATED_DP_EPSILON_PER_ROUND` | `0.35` | Demonstration privacy ledger |

No API key is required for the default assistant. It uses local retrieval and deterministic grounded synthesis.

---

## Architecture

```
Next.js 16 (App Router, client data layer, Tailwind 4, Recharts, Framer Motion)
        │  /api/v1/* via same-origin rewrite
        ▼
FastAPI (routers → services → SQLAlchemy)
        │
        ├── SQLite (zero-config local) / PostgreSQL + pgvector (Docker)
        ├── Scientific engine
        │     ├── deterministic local evidence retrieval
        │     ├── pharmacogenomic interpretation (curated + conservative VCF annotation)
        │     ├── one-compartment oral PK / prodrug pathway index
        │     ├── Monte Carlo uncertainty + local sensitivity
        │     └── federated simulation (FedAvg, clipping, noise, masking)
        ├── Grounded assistant (deterministic default; optional external LLM)
        └── Audit / consent / privacy-budget ledger
```

Important properties:

- **No raw-data model egress** in the default assistant path.
- **No clinical diagnosis** is inferred from any organ status.
- **No personalized dose** is calculated anywhere.
- **Unknown data is retained as unknown.** Population assumptions are labelled in the simulation output.
- **Every evidence-grounded answer** displays citations and a source URL.
- **VCF uploads** are annotated only; no clinical phenotype is inferred.

Full design notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Repository map

```
backend/
  app/
    api/             versioned routers
    core/            config, database, security, limits
    data/            curated demo/reference datasets
    models.py        SQLAlchemy schema
    schemas.py       Pydantic contracts
    services/        labs, ingestion, PGx, twin, simulation, evidence, assistant, federated
  alembic/           migrations
  tests/             62 backend tests
frontend/
  src/app/           12 app routes + auth
  src/components/    design system, body map, charts, shell
  src/lib/           typed API client, formats, validation
  e2e/               Playwright journeys
docs/
  ARCHITECTURE.md
  SCIENTIFIC_LIMITATIONS.md
  SECURITY.md
  DEMO_DATA.md
```

---

## Data and API

- REST endpoints under `/api/v1` with OpenAPI at `/api/docs`.
- All patient-owned rows carry `user_id`; every query filters by the authenticated account.
- Results keep their own unit and reference interval; conversions are explicit and recorded.
- Audit logs record actions, never free-text health content.
- Export produces machine-readable JSON; deletion supports health-data-only or full-account scope.
- Consent enforcement is server-side: the assistant returns 403 without AI consent, and federated rounds require independent opt-in.

Selected endpoints:

```
POST   /api/v1/auth/register | login | demo | logout
GET    /api/v1/overview
GET    /api/v1/profile
POST   /api/v1/labs/manual | upload
GET    /api/v1/labs | trends | biomarkers
POST   /api/v1/genetics/upload
GET    /api/v1/genetics | pharmacogenomics
GET    /api/v1/medications | interactions | catalog
POST   /api/v1/medications
GET    /api/v1/twin | systems/{id} | completeness | knowledge-graph
POST   /api/v1/simulations
GET    /api/v1/simulations/{id} | evidence
POST   /api/v1/assistant/chat | explain
GET    /api/v1/privacy/consent | audit
POST   /api/v1/privacy/export | data | federated-rounds
GET    /api/v1/models
GET    /api/v1/causal/catalog
POST   /api/v1/causal/simulate
POST   /api/v1/wearables/import
```

---

## What is deliberately not claimed

- No clinical validation, regulatory clearance, HIPAA certification or GDPR compliance badge.
- No production federated learning, secure aggregation or differential-privacy proof.
- No live wearable integrations. The sample Oura series demonstrates the data model; provider OAuth is not enabled.
- No OCR for scanned PDFs.
- No complete star-allele caller, phasing or copy-number analysis.
- No full PBPK, pharmacodynamic, efficacy or toxicity prediction.
- No diagnosis from genetics, labs or organ status.
- The causal lab is not causal discovery or causal proof; it is a model-dependent counterfactual under strong assumptions and does not generalize beyond the recorded individual data.

See the scientific and privacy documents for detailed limitations and residual risks.

---

## Illustration attribution

The anatomical base used by the Digital Twin and login visual is **“202403 human anatomy organs.svg”** by the DataBase Center for Life Science (DBCLS), licensed under **CC BY 4.0**. POLIS recolours the illustration into a muted bone-toned display treatment and overlays navigation markers. The image is a generic anatomical navigation interface, not a scan or an image of any real person's organs. Full attribution is in [`frontend/public/anatomy/NOTICE.md`](frontend/public/anatomy/NOTICE.md).

## Documentation

- [Design direction](DESIGN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scientific model limitations](docs/SCIENTIFIC_LIMITATIONS.md)
- [Security and privacy](docs/SECURITY.md)
- [Demonstration data](docs/DEMO_DATA.md)
- [API docs](http://127.0.0.1:8000/api/docs) when running locally
