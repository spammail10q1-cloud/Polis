"""Synthetic demonstration dataset.

Every record created from this module is explicitly marked ``is_synthetic=True``
and carries provenance identifying it as demonstration data. Nothing here is
derived from a real person. Values were chosen to exercise normal, out-of-range,
missing, and uncertain states across the product.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

NOW = datetime.now(UTC)


def days_ago(days: int, *, hour: int = 8, minute: int = 15) -> datetime:
    stamp = NOW - timedelta(days=days)
    return stamp.replace(hour=hour, minute=minute, second=0, microsecond=0)


BIOMARKERS = [
    ("alt", "Alanine aminotransferase", "liver", "U/L", 7, 35, "Hepatocellular enzyme; elevations are non-specific.", 10),
    ("ast", "Aspartate aminotransferase", "liver", "U/L", 10, 35, "Enzyme present in liver, muscle and other tissues.", 20),
    ("alp", "Alkaline phosphatase", "liver", "U/L", 44, 121, "Cholestatic and bone-derived enzyme.", 30),
    ("ggt", "Gamma-glutamyl transferase", "liver", "U/L", 9, 48, "Biliary and hepatic enzyme; affected by alcohol and medicines.", 40),
    ("bilirubin", "Total bilirubin", "liver", "mg/dL", 0.2, 1.2, "Heme breakdown product conjugated by UGT1A1.", 50),
    ("albumin", "Albumin", "liver", "g/dL", 3.5, 5.0, "Hepatic synthetic protein and nutritional marker.", 60),
    ("creatinine", "Creatinine", "kidney", "mg/dL", 0.6, 1.1, "Muscle-derived filtration marker.", 70),
    ("egfr", "Estimated GFR", "kidney", "mL/min/1.73m²", 60, None, "Population estimate of glomerular filtration; lab equation dependent.", 80),
    ("bun", "Blood urea nitrogen", "kidney", "mg/dL", 7, 20, "Urea nitrogen; affected by hydration and protein intake.", 90),
    ("cystatin_c", "Cystatin C", "kidney", "mg/L", 0.53, 0.95, "Alternative filtration marker less dependent on muscle mass.", 100),
    ("urine_acr", "Urine albumin-to-creatinine ratio", "kidney", "mg/g", None, 30, "Albuminuria marker; single samples can vary.", 110),
    ("glucose", "Fasting glucose", "metabolic", "mg/dL", 70, 99, "Single fasting plasma glucose measurement.", 120),
    ("hba1c", "Hemoglobin A1c", "metabolic", "%", 4.0, 5.6, "Reflects average glycemia over roughly 2–3 months.", 130),
    ("insulin", "Fasting insulin", "metabolic", "µIU/mL", 2.6, 24.9, "Fasting insulin; interpretation depends on assay and context.", 140),
    ("total_cholesterol", "Total cholesterol", "metabolic", "mg/dL", None, 200, "Total circulating cholesterol.", 150),
    ("ldl", "LDL cholesterol", "metabolic", "mg/dL", None, 100, "LDL cholesterol; cardiovascular risk context is broader than one value.", 160),
    ("hdl", "HDL cholesterol", "metabolic", "mg/dL", 40, None, "HDL cholesterol; low values are associated with risk in context.", 170),
    ("triglycerides", "Triglycerides", "metabolic", "mg/dL", None, 150, "Fasting triglycerides; affected by recent intake and alcohol.", 180),
    ("apoB", "Apolipoprotein B", "metabolic", "mg/dL", None, 90, "Approximates atherogenic particle number.", 190),
    ("hs_crp", "High-sensitivity CRP", "inflammatory", "mg/L", None, 3.0, "Low-grade inflammation marker; non-specific.", 200),
    ("esr", "Erythrocyte sedimentation rate", "inflammatory", "mm/h", 0, 20, "Non-specific inflammatory marker affected by anemia and proteins.", 210),
    ("hemoglobin", "Hemoglobin", "hematology", "g/dL", 12, 15.5, "Oxygen-carrying protein concentration.", 220),
    ("hematocrit", "Hematocrit", "hematology", "%", 36, 46, "Packed red-cell volume fraction.", 230),
    ("wbc", "White blood cell count", "hematology", "10^9/L", 4, 11, "Total leukocyte count; differential not available.", 240),
    ("rbc", "Red blood cell count", "hematology", "10^12/L", 3.9, 5.2, "Erythrocyte concentration.", 250),
    ("platelets", "Platelet count", "hematology", "10^9/L", 150, 400, "Platelet concentration; relevant to bleeding and clotting context.", 260),
    ("ferritin", "Ferritin", "hematology", "ng/mL", 15, 150, "Iron-storage protein and acute-phase reactant.", 270),
    ("tsh", "Thyroid-stimulating hormone", "hormonal", "mIU/L", 0.4, 4.0, "Primary thyroid screening marker; affected by timing and medicines.", 280),
    ("free_t4", "Free thyroxine (T4)", "hormonal", "ng/dL", 0.8, 1.8, "Unbound thyroxine concentration.", 290),
    ("free_t3", "Free triiodothyronine (T3)", "hormonal", "pg/mL", 2.3, 4.2, "Unbound triiodothyronine concentration.", 300),
    ("testosterone", "Total testosterone", "hormonal", "ng/dL", 8, 60, "Interpretation depends on sex, age, time, and assay.", 310),
    ("estradiol", "Estradiol", "hormonal", "pg/mL", 30, 400, "Cycle-phase-dependent; phase not recorded.", 320),
    ("cortisol", "Cortisol (morning)", "hormonal", "µg/dL", 5, 25, "Diurnal hormone; collection time is essential.", 330),
    ("vitamin_d", "25-hydroxyvitamin D", "nutritional", "ng/mL", 30, 60, "Vitamin D status marker.", 340),
    ("vitamin_b12", "Vitamin B12", "nutritional", "pg/mL", 200, 900, "Cobalamin status marker; assay dependent.", 350),
    ("sodium", "Sodium", "electrolytes", "mmol/L", 135, 145, "Serum sodium.", 360),
    ("potassium", "Potassium", "electrolytes", "mmol/L", 3.5, 5.1, "Serum potassium.", 370),
    ("calcium", "Calcium", "electrolytes", "mg/dL", 8.6, 10.2, "Total serum calcium; albumin dependent.", 380),
    ("magnesium", "Magnesium", "electrolytes", "mg/dL", 1.7, 2.3, "Serum magnesium; does not measure total body stores.", 390),
]


def biomarker_seed() -> list[dict]:
    return [
        {
            "id": code,
            "code": code,
            "name": name,
            "category": category,
            "canonical_unit": unit,
            "typical_ref_low": low,
            "typical_ref_high": high,
            "description": description,
            "reference_note": "Typical adult interval for orientation; the reporting laboratory's interval is stored with each result.",
            "sort_order": order,
        }
        for code, name, category, unit, low, high, description, order in BIOMARKERS
    ]


# (code, value, ref_low, ref_high, offset_days, source, context)
LATEST = [
    ("alt", 48, 7, 35, 16, "Meridian Reference Lab (synthetic)", {"fasting": "not required"}),
    ("ast", 33, 10, 35, 16, "Meridian Reference Lab (synthetic)", {}),
    ("alp", 82, 44, 121, 16, "Meridian Reference Lab (synthetic)", {}),
    ("ggt", 44, 9, 48, 16, "Meridian Reference Lab (synthetic)", {"alcohol": "self-reported 2 units/week"}),
    ("bilirubin", 0.9, 0.2, 1.2, 16, "Meridian Reference Lab (synthetic)", {}),
    ("albumin", 4.2, 3.5, 5.0, 16, "Meridian Reference Lab (synthetic)", {}),
    ("creatinine", 0.88, 0.6, 1.1, 16, "Meridian Reference Lab (synthetic)", {}),
    ("egfr", 94, 60, None, 16, "Meridian Reference Lab (synthetic)", {"equation": "CKD-EPI 2021 creatinine"}),
    ("bun", 14, 7, 20, 16, "Meridian Reference Lab (synthetic)", {}),
    ("cystatin_c", 0.82, 0.53, 0.95, 16, "Meridian Reference Lab (synthetic)", {}),
    ("urine_acr", 8, None, 30, 16, "Meridian Reference Lab (synthetic)", {"specimen": "spot urine"}),
    ("glucose", 96, 70, 99, 16, "Meridian Reference Lab (synthetic)", {"fasting_hours": 11}),
    ("hba1c", 5.5, 4.0, 5.6, 16, "Meridian Reference Lab (synthetic)", {"method": "HPLC"}),
    ("insulin", 9.8, 2.6, 24.9, 16, "Meridian Reference Lab (synthetic)", {"fasting_hours": 11}),
    ("total_cholesterol", 188, None, 200, 16, "Meridian Reference Lab (synthetic)", {"fasting_hours": 11}),
    ("ldl", 118, None, 100, 16, "Meridian Reference Lab (synthetic)", {"fasting_hours": 11, "calculation": "Friedewald"}),
    ("hdl", 58, 40, None, 16, "Meridian Reference Lab (synthetic)", {}),
    ("triglycerides", 128, None, 150, 16, "Meridian Reference Lab (synthetic)", {"fasting_hours": 11}),
    ("apoB", 88, None, 90, 16, "Meridian Reference Lab (synthetic)", {}),
    ("hs_crp", 2.8, None, 3.0, 16, "Meridian Reference Lab (synthetic)", {"acute_illness": "none reported"}),
    ("esr", 12, 0, 20, 16, "Meridian Reference Lab (synthetic)", {}),
    ("hemoglobin", 13.4, 12, 15.5, 16, "Meridian Reference Lab (synthetic)", {}),
    ("hematocrit", 40.2, 36, 46, 16, "Meridian Reference Lab (synthetic)", {}),
    ("wbc", 5.8, 4, 11, 16, "Meridian Reference Lab (synthetic)", {}),
    ("rbc", 4.52, 3.9, 5.2, 16, "Meridian Reference Lab (synthetic)", {}),
    ("platelets", 248, 150, 400, 16, "Meridian Reference Lab (synthetic)", {}),
    ("ferritin", 68, 15, 150, 16, "Meridian Reference Lab (synthetic)", {"iron_supplement": "none"}),
    ("tsh", 2.4, 0.4, 4.0, 16, "Meridian Reference Lab (synthetic)", {"levothyroxine_timing": "before morning dose"}),
    ("free_t4", 1.1, 0.8, 1.8, 16, "Meridian Reference Lab (synthetic)", {}),
    ("free_t3", 3.1, 2.3, 4.2, 16, "Meridian Reference Lab (synthetic)", {}),
    ("testosterone", 28, 8, 60, 16, "Meridian Reference Lab (synthetic)", {"collection_time": "08:15"}),
    ("estradiol", 78, 30, 400, 16, "Meridian Reference Lab (synthetic)", {"cycle_day": "not recorded", "note": "Interpretation limited without cycle phase"}),
    ("cortisol", 11.2, 5, 25, 16, "Meridian Reference Lab (synthetic)", {"collection_time": "08:10", "note": "Morning collection"}),
    ("vitamin_d", 31, 30, 60, 16, "Meridian Reference Lab (synthetic)", {"supplement": "2000 IU daily"}),
    ("vitamin_b12", 420, 200, 900, 16, "Meridian Reference Lab (synthetic)", {"supplement": "none"}),
    ("sodium", 140, 135, 145, 16, "Meridian Reference Lab (synthetic)", {}),
    ("potassium", 4.2, 3.5, 5.1, 16, "Meridian Reference Lab (synthetic)", {}),
    ("calcium", 9.4, 8.6, 10.2, 16, "Meridian Reference Lab (synthetic)", {"albumin_corrected": "not calculated"}),
    ("magnesium", 2.0, 1.7, 2.3, 16, "Meridian Reference Lab (synthetic)", {}),
]

HISTORICAL = [
    # ALT rising trend, still modest and non-specific
    ("alt", 42, 7, 35, 108), ("alt", 36, 7, 35, 208), ("alt", 31, 7, 35, 320),
    ("ast", 28, 10, 35, 108), ("ast", 25, 10, 35, 208), ("ast", 22, 10, 35, 320),
    ("ggt", 40, 9, 48, 108), ("ggt", 34, 9, 48, 208), ("ggt", 30, 9, 48, 320),
    ("ldl", 121, None, 100, 108), ("ldl", 126, None, 100, 208), ("ldl", 132, None, 100, 320),
    ("hba1c", 5.4, 4.0, 5.6, 108), ("hba1c", 5.5, 4.0, 5.6, 208), ("hba1c", 5.4, 4.0, 5.6, 320),
    ("hs_crp", 2.9, None, 3.0, 108), ("hs_crp", 3.2, None, 3.0, 208), ("hs_crp", 3.6, None, 3.0, 320),
    ("egfr", 95, 60, None, 108), ("egfr", 96, 60, None, 208), ("egfr", 98, 60, None, 320),
    ("ferritin", 65, 15, 150, 108), ("ferritin", 61, 15, 150, 208), ("ferritin", 54, 15, 150, 320),
    ("tsh", 2.6, 0.4, 4.0, 108), ("tsh", 2.7, 0.4, 4.0, 208), ("tsh", 2.9, 0.4, 4.0, 320),
    ("vitamin_d", 29, 30, 60, 108), ("vitamin_d", 27, 30, 60, 208), ("vitamin_d", 24, 30, 60, 320),
    ("creatinine", 0.9, 0.6, 1.1, 108), ("creatinine", 0.89, 0.6, 1.1, 208), ("creatinine", 0.91, 0.6, 1.1, 320),
]


GENETIC_SAMPLE = {
    "source": "synthetic_curated_pgx_panel",
    "file_name": "POLIS_demo_pharmacogenomic_panel.json",
    "genome_build": "GRCh38",
    "status": "parsed",
    "notes": "Synthetic curated panel generated by POLIS. Not derived from a real person and not a clinical test result.",
    "provenance": {
        "generator": "POLIS synthetic demo v1",
        "notice": "Demonstration data. Not real patient information.",
        "curation": "Allele calls curated for demonstration; copy-number and hybrid alleles were not independently assayed.",
    },
}

# gene, rsid, chrom, pos, ref, alt, genotype, zygosity, star, consequence, evidence, interpretation
VARIANTS = [
    ("CYP2D6", "rs3892097", "22", 42128945, "C", "T", "C/T", "heterozygous", "*4", "Splice defect; nonfunctional allele", "CPIC/PharmVar", "One no-function *4 allele detected; diplotype curated as *1/*4 for demonstration."),
    ("CYP2C19", "rs4244285", "10", 94781859, "G", "A", "G/A", "heterozygous", "*2", "Splice-site variant; no function", "CPIC/PharmVar", "One no-function *2 allele detected; diplotype curated as *1/*2 for demonstration."),
    ("CYP2C9", "rs1799853", "10", 94981296, "C", "T", "C/C", "homozygous_reference", None, "No *2 variant", "CPIC/PharmVar", "Reference genotype at this assayed position; other variants not excluded."),
    ("CYP2C9", "rs1057910", "10", 94986041, "A", "C", "A/A", "homozygous_reference", None, "No *3 variant", "CPIC/PharmVar", "Reference genotype at this assayed position; other variants not excluded."),
    ("CYP3A5", "rs776746", "7", 99672916, "A", "G", "G/G", "homozygous_alternate", "*3", "Loss of normal expression", "PharmVar", "*3/*3 predicted poor expresser; CYP3A4 remains active."),
    ("SLCO1B1", "rs4149056", "12", 21178615, "T", "C", "T/C", "heterozygous", "*5", "Reduced transporter function", "CPIC", "One decreased-function *5 allele; phenotype curated as decreased function."),
    ("VKORC1", "rs9923231", "16", 31096368, "G", "A", "G/A", "heterozygous", "-1639G>A", "Reduced VKORC1 expression", "CPIC", "One reduced-expression allele; warfarin sensitivity context only."),
    ("TPMT", "rs1800460", "6", 18143724, "C", "T", "C/T", "heterozygous", "*3A component", "Reduced TPMT activity", "CPIC", "Component of *3A; requires the second variant for diplotype assignment."),
    ("TPMT", "rs1142345", "6", 18130918, "T", "C", "T/C", "heterozygous", "*3A component", "Reduced TPMT activity", "CPIC", "Component of *3A; requires the first variant for diplotype assignment."),
    ("NUDT15", "rs116855232", "13", 48620031, "C", "T", "C/C", "homozygous_reference", None, "No common *3 variant", "CPIC", "Reference genotype at this assayed position; other variants not excluded."),
    ("DPYD", "rs3918290", "1", 97515839, "C", "T", "C/C", "homozygous_reference", None, "No *2A variant", "CPIC", "Reference genotype at this assayed position; other DPYD variants not excluded."),
    ("UGT1A1", "rs3064744", "2", 233760233, "TA6", "TA7", "TA6/TA7", "heterozygous_repeat", "*28", "Reduced UGT1A1 expression", "CPIC/PharmGKB", "One *28 repeat allele; phenotype curated as reduced glucuronidation."),
    ("CYP2C19", "rs12248560", "10", 94761900, "C", "T", "C/C", "homozygous_reference", None, "No *17 variant", "CPIC/PharmVar", "Reference genotype at this assayed position."),
]

# gene, diplotype, phenotype, activity score, guideline, interpretation, medications, limitations
PHENOTYPES = [
    (
        "CYP2D6",
        "*1/*4",
        "Intermediate metabolizer",
        0.5,
        "CPIC standardized terms; PharmVar allele definitions",
        "One no-function allele (*4) and one normal-function allele are curated. Reduced CYP2D6 activity is expected, but enzyme activity is not directly measured.",
        [
            {"name": "Metoprolol", "relevance": "CYP2D6 substrate; higher exposure is plausible in intermediate metabolizers.", "status": "active medication"},
            {"name": "Codeine", "relevance": "Prodrug activated by CYP2D6; reduced analgesia is possible.", "status": "not in current list"},
            {"name": "Paroxetine", "relevance": "CYP2D6 inhibitor; may further reduce CYP2D6 activity.", "status": "not in current list"},
        ],
        "Synthetic curated diplotype. Copy-number variants, hybrid CYP2D7/2D6 genes and rare alleles were not independently assayed. A clinical result requires a validated laboratory report.",
    ),
    (
        "CYP2C19",
        "*1/*2",
        "Intermediate metabolizer",
        1.0,
        "CPIC CYP2C19 genotype-phenotype table",
        "One no-function *2 allele is curated. Reduced CYP2C19 activity is expected, with relevance to clopidogrel activation and proton-pump inhibitor exposure.",
        [
            {"name": "Clopidogrel", "relevance": "Prodrug activation is CYP2C19-dependent; intermediate metabolizer status is relevant to guideline-based decision-making.", "status": "not in current list"},
            {"name": "Omeprazole", "relevance": "Metabolized by CYP2C19; exposure may be higher. Omeprazole also inhibits CYP2C19.", "status": "active medication"},
            {"name": "Escitalopram", "relevance": "CYP2C19 substrate; genotype is relevant to some prescribing guidance.", "status": "not in current list"},
        ],
        "Synthetic curated diplotype. Rare decreased-function alleles and phasing were not independently confirmed. Phenotype is not a diagnosis and does not determine therapy.",
    ),
    (
        "CYP2C9",
        "*1/*1",
        "Normal metabolizer",
        2.0,
        "CPIC CYP2C9 genotype-phenotype table",
        "No reduced-function *2 or *3 allele was detected at the assayed positions.",
        [
            {"name": "Warfarin", "relevance": "S-warfarin is metabolized by CYP2C9; VKORC1 and clinical factors also matter.", "status": "not in current list"},
            {"name": "Ibuprofen", "relevance": "CYP2C9 substrate; normal metabolizer status lowers, but does not eliminate, interaction concerns.", "status": "not in current list"},
        ],
        "Only *2 and *3 were assayed in this synthetic panel; rare no-function alleles are not excluded. Normal metabolizer status does not guarantee a specific drug response.",
    ),
    (
        "CYP3A5",
        "*3/*3",
        "Poor expresser",
        0.0,
        "CPIC CYP3A5 genotype-phenotype table",
        "Homozygous *3 is associated with absent CYP3A5 expression. CYP3A4 remains the dominant tacrolimus-metabolizing enzyme in most people.",
        [
            {"name": "Tacrolimus", "relevance": "CYP3A5 expressers generally require higher tacrolimus exposure to reach target; poor expressers are a different subgroup. Clinical use requires transplant expertise.", "status": "not in current list"},
        ],
        "CYP3A5 phenotype does not by itself determine tacrolimus dosing; therapeutic drug monitoring and clinical context are required.",
    ),
    (
        "SLCO1B1",
        "*1/*5",
        "Decreased function",
        1.0,
        "CPIC SLCO1B1 guideline",
        "One rs4149056 (decreased-function) allele is curated. OATP1B1-mediated hepatic uptake is expected to be reduced, with relevance to simvastatin exposure.",
        [
            {"name": "Simvastatin", "relevance": "Decreased-function SLCO1B1 is associated with higher simvastatin exposure and myopathy risk; CPIC provides prescribing considerations.", "status": "not in current list"},
            {"name": "Atorvastatin", "relevance": "SLCO1B1 effects are smaller than for simvastatin; genotype is one factor among many.", "status": "active medication"},
        ],
        "Synthetic curated result for rs4149056 only. This is not a complete transporter assessment and does not measure OATP1B1 activity.",
    ),
    (
        "VKORC1",
        "-1639G>A (G/A)",
        "Intermediate warfarin sensitivity",
        None,
        "CPIC warfarin guideline",
        "One reduced-expression VKORC1 allele is present. This is pharmacodynamic context, not a pharmacokinetic parameter.",
        [
            {"name": "Warfarin", "relevance": "VKORC1 genotype is used with CYP2C9 and clinical factors in genotype-guided dosing algorithms, always with INR monitoring.", "status": "not in current list"},
        ],
        "Warfarin sensitivity depends on VKORC1, CYP2C9, age, body size, diet, illness and interacting drugs. POLIS does not predict INR or calculate a dose.",
    ),
    (
        "TPMT",
        "*1/*3A",
        "Intermediate metabolizer",
        1.0,
        "CPIC thiopurine guideline",
        "A *3A allele is curated. Reduced TPMT activity is expected, increasing thioguanine nucleotide exposure and myelosuppression risk for thiopurines.",
        [
            {"name": "Azathioprine", "relevance": "Thiopurine therapy requires specialist management and genotype-informed starting-dose guidance; POLIS does not simulate this.", "status": "not in current list"},
        ],
        "The *3A call uses two assayed variants; phasing was curated for demonstration. Clinical testing and interpretation are required before thiopurine therapy.",
    ),
    (
        "NUDT15",
        "*1/*1",
        "Normal metabolizer",
        1.0,
        "CPIC thiopurine guideline",
        "No common *3 variant was detected at the assayed position. Other NUDT15 variants are not excluded.",
        [
            {"name": "Azathioprine", "relevance": "NUDT15 is considered with TPMT and clinical factors for thiopurines.", "status": "not in current list"},
        ],
        "Single-variant synthetic panel. Clinical NUDT15 testing must be interpreted by the performing laboratory.",
    ),
    (
        "DPYD",
        "*1/*1",
        "Normal metabolizer",
        1.0,
        "CPIC DPYD guideline",
        "No DPYD *2A variant was detected at the assayed position. Other reduced-function DPYD variants were not tested, so normal activity cannot be assumed.",
        [
            {"name": "Fluorouracil", "relevance": "DPYD activity is relevant to fluoropyrimidine toxicity; no simulation or dosing is offered.", "status": "not in current list"},
        ],
        "A single-variant synthetic panel cannot exclude DPYD deficiency. Fluoropyrimidine therapy requires oncology-led testing and interpretation.",
    ),
    (
        "UGT1A1",
        "*1/*28 (TA6/TA7)",
        "Reduced glucuronidation (intermediate)",
        1.0,
        "CPIC UGT1A1 guideline; PharmGKB",
        "One *28 repeat allele is curated. Reduced UGT1A1 glucuronidation can affect bilirubin and SN-38 clearance, with drug- and context-specific relevance.",
        [
            {"name": "Irinotecan", "relevance": "UGT1A1 variation is associated with SN-38 exposure and neutropenia risk; oncology-guided decisions only.", "status": "not in current list"},
            {"name": "Atazanavir", "relevance": "UGT1A1 variation is associated with atazanavir-related hyperbilirubinemia.", "status": "not in current list"},
        ],
        "Repeat-length assay details and phasing were curated for demonstration. Bilirubin is also affected by hemolysis, liver disease and other factors.",
    ),
]

# medication_id, dose, route, frequency, start offset days, reason, specialty
MEDICATIONS = [
    ("metoprolol", "47.5 mg", "oral", "once daily", 640, "Hypertension", "Primary care"),
    ("omeprazole", "20 mg", "oral", "once daily", 410, "GERD symptoms", "Primary care"),
    ("atorvastatin", "20 mg", "oral", "once nightly", 590, "LDL cholesterol management", "Primary care"),
    ("levothyroxine", "50 mcg", "oral", "once daily, morning", 360, "Hypothyroidism", "Endocrinology"),
    ("albuterol", "90 mcg/inhalation", "inhalation", "as needed", 1200, "Asthma rescue", "Primary care"),
    ("cholecalciferol", "2000 IU", "oral", "once daily", 700, "Vitamin D supplementation", "Self-directed"),
]

CONDITIONS = [
    {"name": "Hypertension", "diagnosed_year": 2021, "status": "active", "notes": "Home readings not connected; self-reported."},
    {"name": "Hyperlipidemia", "diagnosed_year": 2022, "status": "active", "notes": "On statin therapy; LDL above laboratory target interval on latest result."},
    {"name": "Hypothyroidism", "diagnosed_year": 2023, "status": "active", "notes": "On levothyroxine; TSH within laboratory interval on latest result."},
    {"name": "Asthma", "diagnosed_year": 2004, "status": "active", "notes": "Rescue inhaler as needed; no spirometry connected."},
    {"name": "Seasonal allergic rhinitis", "diagnosed_year": 2010, "status": "active", "notes": "Seasonal symptoms."},
]

ALLERGIES = [
    {"substance": "Penicillin", "reaction": "Diffuse rash", "severity": "moderate", "source": "Patient-reported; not formally evaluated"},
]

FAMILY_HISTORY = [
    {"relation": "Father", "condition": "Myocardial infarction", "age_at_onset": 63},
    {"relation": "Mother", "condition": "Hypothyroidism", "age_at_onset": 45},
]

PROFILE = {
    "date_of_birth": "1985-03-14",
    "sex_at_birth": "female",
    "gender_identity": "woman",
    "height_cm": 168,
    "weight_kg": 64,
    "blood_type": "O+",
    "ancestry_context": "Self-reported East Asian and European ancestry (not used to infer genotype)",
    "smoking_status": "never",
    "alcohol_units_per_week": 2,
    "activity_level": "moderately_active",
    "pregnancy_status": "not_pregnant",
    "conditions": CONDITIONS,
    "allergies": ALLERGIES,
    "family_history": FAMILY_HISTORY,
    "notes": "Demonstration profile: synthetic data, not a real person.",
}

WEARABLE_REGISTRY = [
    {"provider": "apple_health", "name": "Apple Health", "status": "integration_interface_ready", "detail": "OAuth/HealthKit import requires a signed app and user permission; not connected in the MVP."},
    {"provider": "google_health_connect", "name": "Google Health Connect", "status": "integration_interface_ready", "detail": "Android permissions flow is designed but not enabled in this deployment."},
    {"provider": "garmin", "name": "Garmin", "status": "not_configured", "detail": "Requires Garmin Health API credentials."},
    {"provider": "fitbit", "name": "Fitbit", "status": "not_configured", "detail": "Requires Fitbit Web API credentials."},
    {"provider": "oura", "name": "Oura", "status": "sample_data_only", "detail": "A synthetic sample dataset demonstrates the unified time-series model; OAuth ingestion is not operational."},
    {"provider": "whoop", "name": "WHOOP", "status": "not_configured", "detail": "Requires WHOOP developer credentials."},
]


def wearable_series() -> list[dict]:
    """Deterministic 45-day synthetic wearable series with realistic daily rhythm.

    Values are generated, not measured. The recent window intentionally includes a
    short-sleep stretch to demonstrate trend and recovery views.
    """
    rng = random.Random(4217)
    records: list[dict] = []
    for day_index in range(44, -1, -1):
        day = (NOW - timedelta(days=day_index)).replace(hour=7, minute=0, second=0, microsecond=0)
        phase = (44 - day_index) / 6.0
        # Recent sleep debt (last 9 days) with partial recovery.
        sleep_debt = 1.05 if day_index < 9 else 0.0
        sleep = 7.25 - 0.55 * math.sin(phase * 0.75) - sleep_debt + rng.gauss(0, 0.35)
        sleep = max(4.9, min(8.8, sleep))
        deep = max(0.55, min(1.8, sleep * 0.2 + rng.gauss(0, 0.12)))
        rem = max(0.8, min(2.2, sleep * 0.24 + rng.gauss(0, 0.18)))
        resting_hr = 59 + 1.8 * math.sin(phase * 0.8) + (2.2 if day_index < 9 else 0) + rng.gauss(0, 1.6)
        hrv = 52 - 6.5 * math.sin(phase * 0.8) - (7.5 if day_index < 9 else 0) + rng.gauss(0, 3.4)
        steps = 8200 + 1800 * math.sin(phase * 1.1) + rng.gauss(0, 1600)
        respiratory = 14.2 + 0.5 * math.sin(phase) + rng.gauss(0, 0.35)
        skin_temp = 0.05 * math.sin(phase * 1.2) + rng.gauss(0, 0.14) + (0.12 if day_index < 4 else 0)
        spo2 = 97.2 + rng.gauss(0, 0.45)
        active = 34 + 10 * math.sin(phase) + rng.gauss(0, 8)
        for metric, value, unit in [
            ("resting_hr", resting_hr, "bpm"),
            ("hrv", hrv, "ms"),
            ("sleep_duration", sleep, "h"),
            ("deep_sleep", deep, "h"),
            ("rem_sleep", rem, "h"),
            ("steps", steps, "steps"),
            ("respiratory_rate", respiratory, "breaths/min"),
            ("skin_temp", skin_temp, "°C deviation"),
            ("spo2", spo2, "%"),
            ("active_minutes", active, "min"),
        ]:
            decimals = 0 if metric in {"steps", "resting_hr", "active_minutes"} else (
                1 if metric in {"sleep_duration", "deep_sleep", "rem_sleep", "respiratory_rate", "spo2", "hrv"} else 2
            )
            records.append(
                {
                    "metric": metric,
                    "value": round(value, decimals),
                    "unit": unit,
                    "recorded_at": day,
                    "quality": "device_estimate",
                }
            )
    return records


MODEL_VERSIONS = [
    {
        "id": "mv_simulation_core",
        "name": "POLIS one-compartment oral PK / pathway index",
        "version": "0.3.0-experimental",
        "status": "experimental",
        "description": "Educational pharmacokinetic visualization with phenotype, renal function, anthropometric and curated interaction modifiers.",
        "limitations": "Not a PBPK model, not validated for dosing, does not predict efficacy or toxicity, ignores active metabolites for most drugs, and lacks prospective clinical validation.",
        "validation_summary": "Unit and deterministic reproducibility tests only. No external clinical validation. Not a medical device.",
    },
    {
        "id": "mv_pgx_rules",
        "name": "Curated pharmacogenomic phenotype mapping",
        "version": "0.2.0",
        "status": "research-use-demo",
        "description": "Displays synthetically curated diplotypes using CPIC/PharmVar terminology. VCF uploads are annotated but not converted into clinical phenotypes without a validated caller.",
        "limitations": "No comprehensive star-allele calling, no copy-number calling, no phasing. Clinical use requires an accredited laboratory.",
        "validation_summary": "Schema and guardrail tests. No analytical or clinical validation.",
    },
    {
        "id": "mv_evidence_retrieval",
        "name": "Local evidence retrieval (hybrid lexical embedding)",
        "version": "0.1.0",
        "status": "research-use-demo",
        "description": "Retrieves a curated, versioned evidence corpus using local embeddings and lexical ranking; every citation links to the source.",
        "limitations": "The corpus is small and not exhaustive. Retrieval is not a systematic review and may miss relevant evidence. Citations are not endorsements of a clinical decision.",
        "validation_summary": "Retrieval smoke tests; no information-retrieval benchmark validation.",
    },
    {
        "id": "mv_federated_demo",
        "name": "Federated learning demonstration",
        "version": "0.1.0-demo",
        "status": "simulation-only",
        "description": "In-process simulation of FedAvg with update clipping, Gaussian noise, additive pairwise masks, and a privacy budget ledger over synthetic clients.",
        "limitations": "No production secure aggregation, no formal end-to-end DP guarantee, no real participants, no poisoning defence deployment.",
        "validation_summary": "Determinism and consent enforcement tests only. Not a production federated system.",
    },
]


def audit_detail_notice() -> dict:
    return {"synthetic": True, "notice": "Demonstration data. Not real patient information."}
