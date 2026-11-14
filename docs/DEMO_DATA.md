# Demonstration Data

Every personal health record in the default demo account is **synthetic**. It is not derived from a real person and must never be treated as clinical information.

The UI marks the demo account with:

> **Demonstration data: not real patient information**

## Account

```
Email:    demo@polis.health
Password: PolisDemo!2026
```

The shared account is protected from deletion. You can create a new account to exercise empty and onboarding states.

## What the dataset contains

### Profile

- Avery Chen, born 1985, 168 cm, 64 kg
- Self-reported East Asian and European ancestry, explicitly not used to infer genotype
- Hypertension, hyperlipidemia, hypothyroidism, asthma, seasonal allergic rhinitis
- Penicillin allergy (patient-reported rash)
- Family history of myocardial infarction and hypothyroidism

### Pharmacogenomics

Synthetic curated panel for 10 pharmacogenes:

| Gene | Diplotype | Phenotype |
|---|---|---|
| CYP2D6 | *1/*4 | Intermediate metabolizer |
| CYP2C19 | *1/*2 | Intermediate metabolizer |
| CYP2C9 | *1/*1 | Normal metabolizer |
| CYP3A5 | *3/*3 | Poor expresser |
| SLCO1B1 | *1/*5 | Decreased function |
| VKORC1 | −1639G>A (G/A) | Intermediate warfarin sensitivity |
| TPMT | *1/*3A | Intermediate metabolizer |
| NUDT15 | *1/*1 | Normal metabolizer |
| DPYD | *1/*1 | Normal metabolizer |
| UGT1A1 | *1/*28 | Reduced glucuronidation |

These are curated demonstration diplotypes, not clinical test results. Limitations are displayed with every phenotype. A raw VCF upload never generates a phenotype.

### Laboratory series

39 latest biomarkers across liver, kidney, metabolic, inflammation, haematology, hormonal, nutritional and electrolyte panels, with four timepoints for selected markers. Notable demonstration states:

- ALT 48 U/L vs a 7 to 35 laboratory interval (review state)
- LDL 118 mg/dL vs a <100 interval
- eGFR 94 mL/min/1.73 m² with cystatin C and urine ACR
- hs-CRP 2.8 mg/L
- Vitamin D 31 ng/mL after supplementation
- Reference intervals are attached to each result rather than a global population range

The dates are generated relative to the time the demo is seeded, so the profile stays current.

### Medications

Six active synthetic entries: metoprolol succinate, omeprazole, atorvastatin, levothyroxine, albuterol inhaler and cholecalciferol.

The interaction catalogue supports explorations such as:

- clopidogrel + omeprazole → major curated interaction, reduced prodrug activation
- simvastatin + clarithromycin → contraindicated interaction
- metoprolol + paroxetine → major CYP2D6 interaction
- warfarin + fluconazole → major bleeding-risk interaction

### Wearables

45 days of deterministic synthetic Oura-style data in the unified schema: sleep duration/stages, HRV, resting heart rate, steps, respiratory rate, skin-temperature deviation, oxygen saturation and active minutes. Device data are always labelled `device_estimate`. No live wearable OAuth integration is claimed or enabled. You can import a user-owned wearable CSV through the UI; imported values are marked as user-supplied device estimates, not synthetic and not laboratory measurements.

### Causal Lab

The synthetic wearable series contains a deliberate recent sleep-debt pattern. The Causal Lab can model a hypothetical same-day sleep or steps shift against HRV or resting heart rate. It returns a DAG, a fitted equation, a bootstrap interval, assumptions and alternative explanations. This is a synthetic structure, not evidence about real physiology.

### Simulations

No simulation is pre-seeded. Run What If? with **clopidogrel** to see:

- CYP2C19 intermediate metabolizer context,
- omeprazole interaction warning,
- pathway index instead of a concentration curve,
- uncertainty interval,
- missing information (indication, bleeding risk, stent context),
- evidence and clinician questions.

Run **metoprolol** to see:

- one-compartment oral PK visualization,
- CYP2D6 context,
- relative exposure interval,
- sensitivity drivers,
- explicit assumptions.

Run **azathioprine**, **fluorouracil** or **irinotecan** to see structured refusal behaviour.

## Data generation and provenance

- Generator/version: POLIS synthetic demo v1 (`backend/app/data/demo.py`).
- `is_synthetic=True` on all user-owned demo records.
- `provenance` and UI labels identify synthetic origin.
- Seeded reference data (biomarkers, drug catalog, evidence) is shared; it is not user health data.
- The demo user is created only when `DEMO_SEED=true`.

## Resetting the demo

SQLite (local development):

```bash
cd backend
rm -f polis.db polis.db-wal polis.db-shm
../.venv/bin/uvicorn app.main:app --reload
```

PostgreSQL/Docker:

```bash
docker compose down -v
docker compose up --build
```

Warning: `down -v` deletes all database data, not just the demo.

## What this dataset is designed to exercise

- normal, out-of-range and missing measurements,
- laboratory-specific intervals and indeterminate states,
- curated PGx with limitations,
- interaction and allergy flags,
- experimental simulation boundaries,
- evidence retrieval and citation display,
- incomplete profile/clinical context,
- consent and deletion flows,
- responsive layouts with dense scientific content.

It is intentionally **not** a clinically realistic patient record and must not be used to evaluate medical decision-making.
