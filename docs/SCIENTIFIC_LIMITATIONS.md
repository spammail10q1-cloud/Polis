# Scientific Model Limitations

**Status:** experimental, educational, research-use demonstration. Not a medical device. Not clinically validated. Not suitable for dosing or treatment decisions.

This document describes what POLIS models, what it does not, and why the boundaries exist.

## 1. What the simulation is

The What If? workspace offers two deliberately limited models.

### 1.1 One-compartment oral PK visualization

For direct-acting medicines, POLIS implements a standard one-compartment model with first-order absorption and elimination:

```
k   = ln(2) / t½
C(t) = (F · D · ka) / (V · (ka − k)) · (e^(−k·t) − e^(−ka·t))
AUC = F · D / CL
CL  = k · V
```

The dose is normalized to a unit input. The output is a **relative concentration** and **relative AUC versus a reference scenario**. No absolute plasma concentration is reported. No dose is calculated.

Curated starting parameters (half-life, apparent volume per kg, bioavailability, absorption rate) are stored with source notes in `backend/app/data/drug_catalog.json`. They are derived from public labeling and illustrative population PK ranges; they are not qualified PBPK parameters for this individual.

### 1.2 Prodrug pathway index

For clopidogrel, the active thiol metabolite is not directly modeled. POLIS computes:

```
relative activation index =
    Σ contribution_i × activity_i × interaction_i
```

where contributions (CYP2C19 65%, CYP3A4 20%, CYP1A2 15%) are illustrative weights informed by CPIC and FDA labeling. This is not an efficacy model. It does not model platelet function, bleeding, thrombosis, stent outcomes or active-metabolite concentrations.

## 2. Personalization rules

| Input | Use | Evidence classification |
|---|---|---|
| CYP2C19 / CYP2D6 / CYP2C9 / CYP3A5 / SLCO1B1 phenotype | Illustrative activity multiplier on the modeled pathway | Personal evidence + experimental scaling |
| Missing relevant genotype | Activity = 1 with explicit assumption and wider uncertainty | Unknown / population assumption |
| eGFR | Renal fraction of clearance scaled by eGFR/90, bounded | Personal evidence |
| Missing eGFR | eGFR = 90 as an explicit assumption | Unknown / population assumption |
| Body weight | Linear apparent-volume scaling; allometric CL `(weight/70)^0.75` | Personal evidence + illustrative approximation |
| Mild isolated ALT elevation | No quantitative clearance reduction; shown as context | Observation, not model input |
| ALT ≥3× ULN or bilirubin ≥2× ULN | Bounded 30% reduction in illustrative hepatic clearance | Mechanistic hypothesis; not validated |
| Curated strong inhibitor/inducer | Multiplies the affected pathway activity for the proposed drug | Established interaction label/guideline |
| Age | Not an independent scalar; only enters an eGFR fallback via CKD-EPI 2021 | Explicitly limited |

The phenotype multipliers in `PHENOTYPE_ACTIVITY` are **educational scalings**, not CPIC dose factors and not measured enzyme activity. CPIC activity scores are genotype interpretation constructs; they are not direct kinetic constants.

## 3. Uncertainty

For oral PK, POLIS runs 1,600 Monte Carlo draws with:

- shared base CL lognormal CV ~30%,
- volume CV ~20%,
- absorption CV ~25%,
- phenotype modifier uncertainty CV ~20% if known, ~35% if assumed,
- interaction modifier CV ~25% when applied,
- hepatic modifier uncertainty when applied,
- fixed eGFR and body weight.

Reported 5th to 95th percentiles are intervals over these illustrative assumptions. They are **not** confidence intervals for a health outcome, and they do not include model-structure uncertainty.

Sensitivity analysis varies selected inputs one at a time and reports the percent change in the modeled index. It is explicitly **model-parameter influence, not a causal effect**.

## 4. What is not modeled

- Tissue distribution, perfusion, partition coefficients or a true PBPK structure
- Active metabolites for most medicines
- Protein binding
- Transporters except a simplified SLCO1B1 contribution for statins
- Enzyme induction time course
- Pharmacodynamics, efficacy, toxicity, bleeding, arrhythmia, INR, platelet function, blood pressure, lipid change or clinical outcomes
- Formulation-specific absorption (extended release, enteric coating)
- Food effects, adherence, renal tubular secretion, dialysis, acute kidney injury
- Pregnancy, lactation, hepatic encephalopathy, heart failure or critical illness
- Drug concentrations in this individual
- Dose selection or titration

## 5. Pharmacogenomics

- Demo phenotypes are **synthetic curated diplotypes**, not clinical test results.
- VCF uploads annotate known panel positions only. POLIS deliberately does not infer a diplotype or phenotype from a raw VCF. Accurate CYP2D6 interpretation requires copy-number analysis, phasing and hybrid-gene detection; targeted panels can miss rare alleles.
- A phenotype is predicted enzyme function from a diplotype, not measured activity.
- Genotype-drug relevance depends on the medicine, dose, indication, interactions, organ function, adherence and clinical context.
- Warfarin: VKORC1 and CYP2C9 genotype context is displayed, but **INR and pharmacodynamics are not modeled**.
- Thiopurines, fluoropyrimidines, irinotecan and other high-risk oncology agents are intentionally excluded from simulation.

## 6. Laboratory interpretation

- Classification uses only the reference interval supplied with that specific result.
- If no usable interval exists, status is `indeterminate`; population ranges are not substituted.
- Supported unit conversions are explicit; unsupported units are rejected.
- Biological and analytical variation are not modeled in organ status.
- A single value or trend does not establish a diagnosis or cause.
- eGFR is a population estimate; the demonstration uses a laboratory-reported value. The fallback CKD-EPI 2021 equation is identified when used.
- PDF extraction can misread layouts; every PDF result is marked needs review.
- FHIR import depends on local code mapping and source-system identity; imported values are unverified.

## 7. Evidence retrieval and the assistant

- The evidence corpus is small, manually curated and versioned; it is not a systematic review.
- Retrieval uses deterministic hashed embeddings plus lexical scoring. It is described as hybrid local retrieval, not a validated semantic search system.
- Citations are attached only from retrieved sources; the assistant is required to say when the data are insufficient.
- The assistant never diagnoses, prescribes, calculates doses or advises starting/stopping medication.
- The optional external LLM path is disabled by default and falls back to deterministic synthesis.
- The demonstration assistant uses synthetic personal data.

## 8. Causal lab and causal interpretation

POLIS includes a deliberately narrow **experimental causal lab** for two wearable questions:

- do(sleep duration + delta) → HRV or resting heart rate,
- do(daily steps + delta) → HRV or resting heart rate.

It fits a linear structural equation with one measured confounder (the other of steps/sleep) using complete same-day wearable days and computes a 5th to 95th percentile bootstrap interval over days. The interface returns the DAG, equation, assumptions, limitations and alternative explanations, and labels the output `experimental_hypothesis`.

This is **not**:
- causal discovery,
- a back-door adjustment over an arbitrary graph,
- a time-varying or lagged causal model,
- a clinical prediction model,
- proof that changing sleep or activity will change the outcome.

It assumes linearity, no unmeasured common causes of treatment and outcome, correct measurement, and no reverse causation. Consumer wearable errors violate the measurement assumption. Effects are individual and may not generalize. The model has no external validation.

The broader product still treats knowledge-graph edges as provenance-bearing associations/mechanisms, PK outputs as model estimates, and sensitivity analysis as model-parameter influence rather than real-world effect modification. No clinical decision can be derived from any of these outputs.

## 9. Validation status

| Component | Status |
|---|---|
| Unit/classification/reproducibility tests | Implemented |
| Tenant isolation and consent tests | Implemented |
| Backend API integration tests | Implemented |
| Causal-lab equation and assumption tests | Implemented |
| External clinical validation | Not performed |
| Calibration / discrimination / subgroup performance | Not assessed |
| Prospective outcome study | Not performed |
| Model drift monitoring | Not implemented for clinical use |
| Regulatory qualification | None |

No model in POLIS is described as clinically validated. The model registry is exposed at `/api/v1/models` and labels every model experimental.

## 10. Selected references

- CPIC. *CYP2C19 Genotype and Clopidogrel Therapy: 2022 Update.* https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/
- CPIC. *SLCO1B1 Genotype and Simvastatin Therapy.* https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/
- CPIC. *Warfarin and CYP2C9/VKORC1.* https://cpicpgx.org/guidelines/guideline-for-warfarin-and-cyp2c9-and-vkorc1/
- CPIC. *Thiopurines and TPMT/NUDT15.* https://cpicpgx.org/guidelines/guideline-for-thiopurines-and-tpmt/
- CPIC. *Fluoropyrimidines and DPYD.* https://cpicpgx.org/guidelines/guideline-for-fluoropyrimidines-and-dpyd/
- FDA. *Physiologically Based Pharmacokinetic Analyses: Format and Content.* https://www.fda.gov/regulatory-information/search-fda-guidance-documents/physiologically-based-pharmacokinetic-analyses-format-and-content
- FDA. *Clinical Drug Interaction Studies: Cytochrome P450 Enzyme- and Transporter-Mediated Drug Interactions.* https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-drug-interaction-studies-cytochrome-p450-enzyme-and-transporter-mediated-drug-interactions
- Jones HM, Rowland-Yeo K. Basic concepts in physiologically based pharmacokinetic modeling. *CPT Pharmacometrics Syst Pharmacol.* 2013. https://doi.org/10.1038/psp.2013.41
- CDC. *About Sleep.* https://www.cdc.gov/sleep/about/index.html
- Hernán MA, Robins JM. *Causal Inference: What If.* Chapman & Hall/CRC; 2020. (Methodological reference for counterfactual reasoning; POLIS discusses assumptions, not a full implementation.)
- KDIGO. *2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease.* https://kdigo.org/guidelines/ckd-evaluation-and-management/
- ACG. *Evaluation of Abnormal Liver Chemistries.* https://journals.lww.com/ajg/fulltext/2017/01000/acg_clinical_guideline__evaluation_of_abnormal_liver.20.aspx
- PharmVar. *CYP2D6.* https://www.pharmvar.org/gene/CYP2D6

Detailed source metadata, summaries, versions and retrieval scores are in the application's evidence corpus and are shown with each answer.
