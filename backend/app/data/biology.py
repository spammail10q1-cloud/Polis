"""Curated biological reference data.

This is deliberately a small, provenance-bearing starter graph. It is not a
complete biological knowledge base. Every edge carries an evidence level and a
source so the UI can separate established biology from mechanistic inference.
"""

SYSTEMS = [
    {
        "id": "liver",
        "name": "Liver",
        "tagline": "Metabolic processing, detoxification and synthesis",
        "description": (
            "The liver handles first-pass and systemic metabolism for many medicines, synthesizes "
            "albumin and clotting factors, and conjugates bilirubin. Liver chemistry patterns are "
            "non-specific: elevations can reflect many causes and are never diagnosed by POLIS."
        ),
        "organs": ["Liver", "Biliary tree"],
        "pathways": ["hepatic-cyp-metabolism", "bilirubin-conjugation", "lipid-metabolism"],
        "accent": "amber",
        "sort_order": 1,
        "expected_codes": ["alt", "ast", "alp", "ggt", "bilirubin", "albumin"],
        "expected_metrics": [],
        "genes": ["CYP2D6", "CYP2C19", "CYP2C9", "CYP3A4", "CYP3A5", "UGT1A1"],
        "connected": ["digestive", "metabolic", "immune"],
        "limitations": [
            "Liver blood tests do not measure total liver function or establish a cause.",
            "A simplified PK model does not represent hepatic blood flow, transporters, or enzyme induction.",
        ],
    },
    {
        "id": "kidneys",
        "name": "Kidneys",
        "tagline": "Filtration, electrolyte balance and drug elimination",
        "description": (
            "The kidneys filter plasma, regulate fluid and electrolytes, and eliminate many medicines "
            "and metabolites. eGFR is a population estimate, not a direct measurement of individual "
            "nephron function, and is less reliable at extremes of muscle mass or in acute illness."
        ),
        "organs": ["Kidneys", "Renal vasculature"],
        "pathways": ["renal-clearance", "renin-angiotensin"],
        "accent": "cyan",
        "sort_order": 2,
        "expected_codes": ["creatinine", "egfr", "bun", "cystatin_c", "urine_acr"],
        "expected_metrics": [],
        "genes": ["UMOD", "ACE"],
        "connected": ["heart", "metabolic", "endocrine"],
        "limitations": [
            "eGFR equations are population estimates and may be inaccurate in acute kidney injury.",
            "Urine albumin can vary with exercise, fever and menstrual blood; a single result is not a diagnosis.",
        ],
    },
    {
        "id": "heart",
        "name": "Heart & circulation",
        "tagline": "Cardiac rhythm, vascular tone and lipid transport",
        "description": (
            "The cardiovascular system transports oxygen, nutrients and medicines. Heart rate and "
            "heart-rate variability from wearables are device estimates, not diagnostic ECG measures. "
            "Lipid and inflammation markers inform risk context but do not constitute a diagnosis."
        ),
        "organs": ["Heart", "Aorta", "Arteries", "Veins"],
        "pathways": ["lipid-metabolism", "renin-angiotensin", "adrenergic-signaling"],
        "accent": "rose",
        "sort_order": 3,
        "expected_codes": ["apoB", "hs_crp"],
        "expected_metrics": ["resting_hr", "hrv", "blood_pressure_systolic", "blood_pressure_diastolic"],
        "genes": ["ADRB1", "CYP2D6"],
        "connected": ["lungs", "kidneys", "metabolic", "brain"],
        "limitations": [
            "Wearable heart rate and HRV are not ECG or ambulatory monitoring.",
            "Blood pressure readings are not part of this demonstration dataset; hypertension context is self-reported.",
        ],
    },
    {
        "id": "lungs",
        "name": "Lungs",
        "tagline": "Gas exchange and respiratory reserve",
        "description": (
            "The lungs exchange oxygen and carbon dioxide. POLIS has no spirometry, imaging or blood-gas "
            "data for this demonstration profile, so pulmonary function cannot be assessed. Respiratory "
            "rate and oxygen saturation from wearables are estimates with substantial motion artifact."
        ),
        "organs": ["Lungs", "Bronchi", "Alveoli"],
        "pathways": ["gas-exchange", "inflammatory-response"],
        "accent": "cyan",
        "sort_order": 4,
        "expected_codes": [],
        "expected_metrics": ["respiratory_rate", "spo2"],
        "genes": [],
        "connected": ["heart", "immune"],
        "limitations": [
            "No spirometry or pulmonary function data are available.",
            "Asthma control cannot be assessed from wearable respiratory rate alone.",
        ],
    },
    {
        "id": "brain",
        "name": "Brain & nervous system",
        "tagline": "Cognition, autonomic regulation and sleep architecture",
        "description": (
            "The nervous system coordinates cognition, autonomic tone, sleep and pain. Wearable sleep "
            "stages and HRV are proprietary estimates. POLIS contains no cognitive testing, EEG, or "
            "neurological examination data, so this system is intentionally marked as partial."
        ),
        "organs": ["Brain", "Spinal cord", "Peripheral nerves"],
        "pathways": ["sleep-circadian", "adrenergic-signaling", "serotonergic-signaling"],
        "accent": "violet",
        "sort_order": 5,
        "expected_codes": [],
        "expected_metrics": ["sleep_duration", "hrv", "deep_sleep"],
        "genes": ["CYP2D6", "CYP2C19"],
        "connected": ["endocrine", "heart", "immune"],
        "limitations": [
            "No neurological examination, cognitive assessment, EEG, or imaging is available.",
            "Sleep staging from a consumer wearable is an estimate and can misclassify stages.",
        ],
    },
    {
        "id": "digestive",
        "name": "Digestive system",
        "tagline": "Absorption, enterohepatic cycling and the gut–liver axis",
        "description": (
            "The gastrointestinal tract absorbs nutrients and medicines and communicates with the liver "
            "through portal circulation. POLIS has no endoscopy, stool studies, or microbiome sequencing "
            "for this profile; nutritional markers provide only indirect context."
        ),
        "organs": ["Stomach", "Small intestine", "Colon", "Pancreas"],
        "pathways": ["hepatic-cyp-metabolism", "gut-liver-axis"],
        "accent": "amber",
        "sort_order": 6,
        "expected_codes": ["albumin", "vitamin_b12"],
        "expected_metrics": [],
        "genes": ["CYP3A4", "SLCO1B1"],
        "connected": ["liver", "metabolic", "immune"],
        "limitations": [
            "No endoscopy, stool studies, or microbiome data are available.",
            "Gastrointestinal symptoms and medication absorption are not modeled.",
        ],
    },
    {
        "id": "endocrine",
        "name": "Endocrine system",
        "tagline": "Hormonal axes, thyroid regulation and metabolic signaling",
        "description": (
            "Endocrine glands regulate metabolism, stress response, reproduction and growth. Hormone "
            "interpretation depends on time of day, cycle phase, medication timing and assay method. "
            "POLIS displays values and context without diagnosing an endocrine disorder."
        ),
        "organs": ["Thyroid", "Adrenal glands", "Pancreas", "Ovaries/Testes"],
        "pathways": ["thyroid-axis", "hypothalamic-pituitary-axis", "glycemic-regulation"],
        "accent": "violet",
        "sort_order": 7,
        "expected_codes": ["tsh", "free_t4", "free_t3", "cortisol", "testosterone", "estradiol"],
        "expected_metrics": [],
        "genes": ["CYP2C19", "CYP2D6"],
        "connected": ["brain", "metabolic", "kidneys"],
        "limitations": [
            "Estradiol and testosterone interpretation depends on cycle phase, time, and assay.",
            "No dynamic endocrine testing (stimulation/suppression) is available.",
        ],
    },
    {
        "id": "immune",
        "name": "Immune system",
        "tagline": "Inflammation, infection response and hypersensitivity",
        "description": (
            "Innate and adaptive immunity defend against infection and shape inflammatory responses. "
            "White-cell counts, CRP and ESR are non-specific. A reported allergy is not the same as a "
            "confirmed immunological hypersensitivity, and delabeling requires clinical assessment."
        ),
        "organs": ["Bone marrow", "Lymph nodes", "Spleen", "Thymus"],
        "pathways": ["inflammatory-response", "thiopurine-metabolism"],
        "accent": "amber",
        "sort_order": 8,
        "expected_codes": ["wbc", "hs_crp", "esr", "ferritin"],
        "expected_metrics": ["skin_temp"],
        "genes": ["TPMT", "NUDT15"],
        "connected": ["lungs", "liver", "digestive"],
        "limitations": [
            "CRP and ESR are non-specific and cannot identify the source of inflammation.",
            "No allergy testing, immunoglobulin levels, or lymphocyte subsets are available.",
        ],
    },
    {
        "id": "musculoskeletal",
        "name": "Musculoskeletal system",
        "tagline": "Structure, mineral balance and physical capacity",
        "description": (
            "Bones, muscles and connective tissue support movement and store minerals. POLIS has "
            "nutritional and mineral markers but no imaging, bone density, strength testing, or "
            "functional assessment. Muscle symptoms require clinical evaluation."
        ),
        "organs": ["Skeletal muscle", "Bones", "Joints", "Tendons"],
        "pathways": ["calcium-phosphate-homeostasis", "vitamin-d-axis"],
        "accent": "slate",
        "sort_order": 9,
        "expected_codes": ["vitamin_d", "calcium", "magnesium"],
        "expected_metrics": ["steps", "active_minutes"],
        "genes": ["VKORC1", "SLCO1B1"],
        "connected": ["kidneys", "endocrine", "digestive"],
        "limitations": [
            "No bone density, imaging, or functional strength testing is available.",
            "Serum calcium and magnesium do not measure total body stores.",
        ],
    },
    {
        "id": "metabolic",
        "name": "Metabolic system",
        "tagline": "Energy balance, glucose regulation and lipid metabolism",
        "description": (
            "Metabolism integrates nutrient sensing, glucose regulation and lipoprotein handling across "
            "organs. A fasting glucose or HbA1c can inform risk context but does not by itself diagnose "
            "diabetes. Weight and activity data are user- or device-reported."
        ),
        "organs": ["Adipose tissue", "Skeletal muscle", "Liver", "Pancreas"],
        "pathways": ["glycemic-regulation", "lipid-metabolism", "hepatic-cyp-metabolism"],
        "accent": "cyan",
        "sort_order": 10,
        "expected_codes": [
            "glucose",
            "hba1c",
            "insulin",
            "total_cholesterol",
            "ldl",
            "hdl",
            "triglycerides",
            "apoB",
        ],
        "expected_metrics": ["steps", "active_minutes", "sleep_duration"],
        "genes": ["CYP2C9", "CYP3A4", "SLCO1B1"],
        "connected": ["liver", "endocrine", "heart", "digestive"],
        "limitations": [
            "No oral glucose tolerance test or continuous glucose monitoring is available.",
            "Single lipid measurements are affected by fasting state and recent illness.",
        ],
    },
]

PATHWAYS = [
    {
        "id": "hepatic-cyp-metabolism",
        "name": "Hepatic CYP-mediated drug metabolism",
        "description": "Cytochrome P450 enzymes in hepatocytes and enterocytes oxidize many medicines, influencing first-pass and systemic exposure.",
        "genes": ["CYP2D6", "CYP2C19", "CYP2C9", "CYP3A4", "CYP3A5"],
        "organs": ["liver", "digestive"],
        "evidence_level": "established biology",
        "source": "FDA drug interaction guidance; CPIC gene-drug guidelines",
    },
    {
        "id": "bilirubin-conjugation",
        "name": "Bilirubin conjugation and excretion",
        "description": "UGT1A1 conjugates bilirubin, making it water-soluble for biliary excretion. Reduced activity can cause unconjugated hyperbilirubinemia.",
        "genes": ["UGT1A1"],
        "organs": ["liver", "digestive"],
        "evidence_level": "established biology",
        "source": "CPIC UGT1A1 guideline; FDA labeling",
    },
    {
        "id": "renal-clearance",
        "name": "Renal filtration and tubular handling",
        "description": "Glomerular filtration and tubular secretion eliminate hydrophilic drugs and metabolites. Kidney function modifies exposure for renally cleared drugs.",
        "genes": [],
        "organs": ["kidneys"],
        "evidence_level": "established physiology",
        "source": "KDIGO 2024; FDA PBPK guidance",
    },
    {
        "id": "lipid-metabolism",
        "name": "Lipoprotein metabolism and hepatic cholesterol handling",
        "description": "LDL receptor activity, hepatic cholesterol synthesis, and lipoprotein clearance determine circulating LDL and ApoB particle numbers.",
        "genes": ["SLCO1B1", "CYP3A4"],
        "organs": ["liver", "metabolic", "heart"],
        "evidence_level": "established biology",
        "source": "FDA statin labeling; CPIC SLCO1B1 guideline",
    },
    {
        "id": "thiopurine-metabolism",
        "name": "Thiopurine activation and inactivation",
        "description": "TPMT and NUDT15 inactivate thioguanine nucleotides; reduced activity increases active metabolite exposure and myelosuppression risk.",
        "genes": ["TPMT", "NUDT15"],
        "organs": ["liver", "immune"],
        "evidence_level": "established pharmacogenomics",
        "source": "CPIC thiopurine guideline",
    },
    {
        "id": "fluoropyrimidine-catabolism",
        "name": "Fluoropyrimidine catabolism",
        "description": "DPYD is the rate-limiting enzyme for fluoropyrimidine catabolism; deficiency increases systemic exposure and severe toxicity risk.",
        "genes": ["DPYD"],
        "organs": ["liver"],
        "evidence_level": "established pharmacogenomics",
        "source": "CPIC DPYD guideline",
    },
    {
        "id": "vitamin-k-cycle",
        "name": "Vitamin K epoxide cycle",
        "description": "VKORC1 regenerates reduced vitamin K for clotting factor synthesis; warfarin inhibits this cycle. CYP2C9 metabolizes the more potent S-warfarin.",
        "genes": ["VKORC1", "CYP2C9"],
        "organs": ["liver"],
        "evidence_level": "established biology",
        "source": "CPIC warfarin guideline; FDA labeling",
    },
    {
        "id": "adrenergic-signaling",
        "name": "Adrenergic signaling",
        "description": "Beta-adrenergic receptors modulate heart rate, contractility and vascular tone. Beta-blockers compete with endogenous catecholamines.",
        "genes": ["ADRB1", "CYP2D6"],
        "organs": ["heart", "brain"],
        "evidence_level": "established biology",
        "source": "FDA metoprolol labeling",
    },
    {
        "id": "renin-angiotensin",
        "name": "Renin–angiotensin–aldosterone axis",
        "description": "A hormonal cascade regulating blood pressure, sodium balance and glomerular filtration.",
        "genes": ["ACE"],
        "organs": ["kidneys", "heart"],
        "evidence_level": "established biology",
        "source": "KDIGO 2024",
    },
    {
        "id": "thyroid-axis",
        "name": "Hypothalamic–pituitary–thyroid axis",
        "description": "TRH, TSH, T4 and T3 form a negative-feedback loop controlling basal metabolism. TSH is the primary screening marker.",
        "genes": ["DIO1", "DIO2"],
        "organs": ["endocrine", "brain"],
        "evidence_level": "established biology",
        "source": "FDA levothyroxine labeling",
    },
    {
        "id": "glycemic-regulation",
        "name": "Glucose and insulin regulation",
        "description": "Insulin, glucagon, hepatic glucose output and muscle glucose uptake maintain glucose homeostasis. HbA1c reflects average glycemia over roughly two to three months.",
        "genes": [],
        "organs": ["metabolic", "endocrine", "liver", "musculoskeletal"],
        "evidence_level": "established biology",
        "source": "Clinical laboratory standards; ADA context",
    },
    {
        "id": "inflammatory-response",
        "name": "Acute-phase inflammatory response",
        "description": "Cytokines drive hepatic acute-phase protein synthesis, including CRP, and alter white-cell trafficking. These markers are non-specific.",
        "genes": ["CRP"],
        "organs": ["immune", "liver"],
        "evidence_level": "established biology",
        "source": "ACG/clinical pathology references",
    },
    {
        "id": "sleep-circadian",
        "name": "Sleep–wake and circadian regulation",
        "description": "Circadian and homeostatic processes regulate sleep timing and architecture, which in turn influence autonomic and metabolic function.",
        "genes": ["CLOCK", "ARNTL"],
        "organs": ["brain", "endocrine"],
        "evidence_level": "established biology",
        "source": "Sleep physiology literature; device-measurement limitations",
    },
    {
        "id": "gut-liver-axis",
        "name": "Gut–liver axis",
        "description": "Portal blood carries nutrients, microbial products and orally absorbed drugs from the intestine to the liver, shaping first-pass metabolism and immune signaling.",
        "genes": ["CYP3A4"],
        "organs": ["digestive", "liver", "immune"],
        "evidence_level": "established physiology",
        "source": "Pharmacology and physiology literature",
    },
    {
        "id": "hypothalamic-pituitary-axis",
        "name": "Hypothalamic–pituitary–adrenal axis",
        "description": "CRH, ACTH and cortisol coordinate the stress response. Cortisol has a strong diurnal rhythm and is affected by timing and acute illness.",
        "genes": ["NR3C1"],
        "organs": ["endocrine", "brain"],
        "evidence_level": "established biology",
        "source": "Endocrinology references",
    },
    {
        "id": "calcium-phosphate-homeostasis",
        "name": "Calcium and phosphate homeostasis",
        "description": "Parathyroid hormone, vitamin D, kidneys, intestine and bone coordinate serum calcium and phosphate.",
        "genes": ["VDR"],
        "organs": ["musculoskeletal", "kidneys", "endocrine"],
        "evidence_level": "established biology",
        "source": "KDIGO mineral metabolism guidance",
    },
    {
        "id": "vitamin-d-axis",
        "name": "Vitamin D metabolism",
        "description": "Skin synthesis and dietary intake produce 25-hydroxyvitamin D, which is further activated in the kidney and affects calcium absorption and bone metabolism.",
        "genes": ["VDR", "CYP2R1"],
        "organs": ["musculoskeletal", "kidneys", "digestive"],
        "evidence_level": "established biology",
        "source": "NIH Office of Dietary Supplements",
    },
    {
        "id": "gas-exchange",
        "name": "Alveolar gas exchange",
        "description": "Oxygen and carbon dioxide diffuse across the alveolar–capillary membrane; ventilation and perfusion must be matched.",
        "genes": [],
        "organs": ["lungs", "heart"],
        "evidence_level": "established physiology",
        "source": "Respiratory physiology references",
    },
    {
        "id": "serotonergic-signaling",
        "name": "Serotonergic neurotransmission",
        "description": "Serotonin modulates mood, sleep, appetite and autonomic function; SSRIs inhibit reuptake and CYP2D6 affects exposure to some agents.",
        "genes": ["SLC6A4", "CYP2D6"],
        "organs": ["brain", "digestive"],
        "evidence_level": "established biology",
        "source": "FDA SSRI labeling",
    },
]

KG_NODES = [
    ("gene:CYP2D6", "gene", "CYP2D6", "Highly polymorphic cytochrome P450 enzyme gene with copy-number and structural variation."),
    ("gene:CYP2C19", "gene", "CYP2C19", "Cytochrome P450 gene affecting clopidogrel activation and proton-pump inhibitor metabolism."),
    ("gene:CYP2C9", "gene", "CYP2C9", "Cytochrome P450 gene affecting warfarin and NSAID metabolism."),
    ("gene:CYP3A4", "gene", "CYP3A4", "Major drug-metabolizing enzyme and target of many inhibitors and inducers."),
    ("gene:CYP3A5", "gene", "CYP3A5", "Cytochrome P450 gene with a common loss-of-function allele affecting tacrolimus clearance."),
    ("gene:SLCO1B1", "gene", "SLCO1B1", "OATP1B1 transporter gene affecting statin uptake and exposure."),
    ("gene:VKORC1", "gene", "VKORC1", "Vitamin K epoxide reductase gene affecting warfarin pharmacodynamics."),
    ("gene:TPMT", "gene", "TPMT", "Thiopurine methyltransferase gene affecting thiopurine inactivation."),
    ("gene:NUDT15", "gene", "NUDT15", "Nudix hydrolase gene affecting thioguanine nucleotide inactivation."),
    ("gene:DPYD", "gene", "DPYD", "Dihydropyrimidine dehydrogenase gene affecting fluoropyrimidine catabolism."),
    ("gene:UGT1A1", "gene", "UGT1A1", "UDP-glucuronosyltransferase gene affecting bilirubin and SN-38 conjugation."),
    ("protein:CYP2D6", "enzyme", "CYP2D6 enzyme", "Hepatic and enterocyte cytochrome P450 enzyme."),
    ("protein:CYP2C19", "enzyme", "CYP2C19 enzyme", "Hepatic cytochrome P450 enzyme."),
    ("protein:CYP2C9", "enzyme", "CYP2C9 enzyme", "Hepatic cytochrome P450 enzyme."),
    ("protein:CYP3A4", "enzyme", "CYP3A4 enzyme", "Abundant hepatic and intestinal cytochrome P450 enzyme."),
    ("protein:CYP3A5", "enzyme", "CYP3A5 enzyme", "Cytochrome P450 enzyme expressed in liver, kidney and intestine."),
    ("protein:OATP1B1", "transporter", "OATP1B1", "Hepatic uptake transporter encoded by SLCO1B1."),
    ("protein:VKORC1", "enzyme", "VKORC1", "Vitamin K epoxide reductase complex subunit 1."),
    ("protein:TPMT", "enzyme", "TPMT", "Thiopurine methyltransferase."),
    ("protein:NUDT15", "enzyme", "NUDT15", "Nudix hydrolase 15."),
    ("protein:DPD", "enzyme", "Dihydropyrimidine dehydrogenase", "Rate-limiting enzyme for fluoropyrimidine catabolism."),
    ("protein:UGT1A1", "enzyme", "UGT1A1", "Bilirubin and xenobiotic glucuronosyltransferase."),
    ("drug:clopidogrel", "medication", "Clopidogrel", "P2Y12 inhibitor prodrug requiring CYP-mediated activation."),
    ("drug:omeprazole", "medication", "Omeprazole", "Proton pump inhibitor and CYP2C19 inhibitor."),
    ("drug:metoprolol", "medication", "Metoprolol", "Beta-1 selective adrenergic blocker and CYP2D6 substrate."),
    ("drug:simvastatin", "medication", "Simvastatin", "HMG-CoA reductase inhibitor and SLCO1B1/CYP3A4 substrate."),
    ("drug:warfarin", "medication", "Warfarin", "Vitamin K antagonist; CYP2C9 substrate and VKORC1 inhibitor."),
    (" drug:azathioprine", "medication", "Azathioprine", "Thiopurine prodrug affected by TPMT and NUDT15."),
    ("protein:ADRB1", "receptor", "Beta-1 adrenergic receptor", "G-protein coupled receptor mediating cardiac chronotropic and inotropic effects."),
    ("protein:P2Y12", "receptor", "P2Y12 receptor", "Platelet ADP receptor blocked by active clopidogrel metabolite."),
    ("protein:HMGCR", "enzyme", "HMG-CoA reductase", "Rate-limiting enzyme in cholesterol synthesis."),
    ("biomarker:alt", "biomarker", "ALT", "Alanine aminotransferase; hepatocellular enzyme."),
    ("biomarker:egfr", "biomarker", "eGFR", "Estimated glomerular filtration rate from a population equation."),
    ("biomarker:ldl", "biomarker", "LDL cholesterol", "Circulating LDL cholesterol concentration."),
    ("biomarker:bilirubin", "biomarker", "Bilirubin", "Heme catabolism product conjugated by UGT1A1."),
    ("organ:liver", "organ", "Liver", "Central metabolic and detoxification organ."),
    ("organ:kidneys", "organ", "Kidneys", "Filtration and elimination organs."),
    ("organ:heart", "organ", "Heart", "Muscular pump driving circulation."),
    ("organ:platelets", "organ", "Platelets", "Anucleate blood cells mediating hemostasis."),
    ("pathway:hepatic-cyp-metabolism", "pathway", "Hepatic CYP metabolism", "Oxidative drug metabolism pathway."),
    ("pathway:renal-clearance", "pathway", "Renal clearance", "Kidney-mediated elimination."),
    ("pathway:lipid-metabolism", "pathway", "Lipoprotein metabolism", "Cholesterol and lipoprotein handling."),
]

KG_EDGES = [
    ("gene:CYP2D6", "protein:CYP2D6", "encodes", "established biology", "Central dogma / PharmVar"),
    ("gene:CYP2C19", "protein:CYP2C19", "encodes", "established biology", "Central dogma / PharmVar"),
    ("gene:CYP2C9", "protein:CYP2C9", "encodes", "established biology", "Central dogma / PharmVar"),
    ("gene:CYP3A4", "protein:CYP3A4", "encodes", "established biology", "Central dogma / PharmVar"),
    ("gene:CYP3A5", "protein:CYP3A5", "encodes", "established biology", "Central dogma / PharmVar"),
    ("gene:SLCO1B1", "protein:OATP1B1", "encodes", "established biology", "PharmVar"),
    ("gene:VKORC1", "protein:VKORC1", "encodes", "established biology", "PharmVar"),
    ("gene:TPMT", "protein:TPMT", "encodes", "established biology", "PharmVar"),
    ("gene:NUDT15", "protein:NUDT15", "encodes", "established biology", "PharmVar"),
    ("gene:DPYD", "protein:DPD", "encodes", "established biology", "PharmVar"),
    ("gene:UGT1A1", "protein:UGT1A1", "encodes", "established biology", "PharmVar"),
    ("protein:CYP2D6", "drug:metoprolol", "metabolizes", "established biology", "FDA metoprolol labeling"),
    ("protein:CYP2C19", "drug:omeprazole", "metabolizes", "established biology", "FDA omeprazole labeling"),
    ("protein:CYP2C19", "drug:clopidogrel", "activates", "peer-reviewed guideline", "CPIC 2022 clopidogrel guideline"),
    ("protein:CYP3A4", "drug:simvastatin", "metabolizes", "established biology", "FDA simvastatin labeling"),
    ("protein:OATP1B1", "drug:simvastatin", "transports", "peer-reviewed guideline", "CPIC SLCO1B1 guideline"),
    ("protein:CYP2C9", "drug:warfarin", "metabolizes", "established biology", "CPIC warfarin guideline"),
    ("drug:warfarin", "protein:VKORC1", "inhibits", "established biology", "CPIC warfarin guideline"),
    ("protein:TPMT", "drug:azathioprine", "inactivates", "peer-reviewed guideline", "CPIC thiopurine guideline"),
    ("protein:NUDT15", "drug:azathioprine", "associated_with", "peer-reviewed guideline", "CPIC thiopurine guideline"),
    ("drug:metoprolol", "protein:ADRB1", "inhibits", "established pharmacology", "FDA metoprolol labeling"),
    ("drug:clopidogrel", "protein:P2Y12", "inhibits", "established pharmacology", "FDA clopidogrel labeling"),
    ("drug:simvastatin", "protein:HMGCR", "inhibits", "established pharmacology", "FDA simvastatin labeling"),
    ("drug:omeprazole", "protein:CYP2C19", "inhibits", "established pharmacology", "FDA omeprazole labeling"),
    ("protein:CYP2D6", "organ:liver", "expressed_in", "established biology", "Pharmacology literature"),
    ("protein:CYP2C19", "organ:liver", "expressed_in", "established biology", "Pharmacology literature"),
    ("protein:CYP3A4", "organ:liver", "expressed_in", "established biology", "Pharmacology literature"),
    ("protein:OATP1B1", "organ:liver", "expressed_in", "established biology", "CPIC SLCO1B1 guideline"),
    ("protein:ADRB1", "organ:heart", "expressed_in", "established biology", "Pharmacology literature"),
    ("protein:P2Y12", "organ:platelets", "expressed_in", "established biology", "Pharmacology literature"),
    ("biomarker:alt", "organ:liver", "associated_with", "established clinical association", "ACG liver chemistry guideline"),
    ("biomarker:egfr", "organ:kidneys", "associated_with", "established clinical association", "KDIGO 2024"),
    ("biomarker:ldl", "pathway:lipid-metabolism", "part_of", "established biology", "Lipidology literature"),
    ("biomarker:bilirubin", "pathway:hepatic-cyp-metabolism", "associated_with", "established biology", "UGT1A1 biology"),
    ("protein:CYP2D6", "pathway:hepatic-cyp-metabolism", "participates_in", "established biology", "Pharmacology literature"),
    ("protein:CYP2C19", "pathway:hepatic-cyp-metabolism", "participates_in", "established biology", "Pharmacology literature"),
    ("protein:CYP2C9", "pathway:hepatic-cyp-metabolism", "participates_in", "established biology", "Pharmacology literature"),
    ("protein:OATP1B1", "pathway:lipid-metabolism", "participates_in", "established biology", "CPIC SLCO1B1 guideline"),
    ("organ:kidneys", "pathway:renal-clearance", "participates_in", "established physiology", "KDIGO 2024"),
    ("organ:liver", "pathway:hepatic-cyp-metabolism", "participates_in", "established physiology", "Pharmacology literature"),
]

# Fix a deliberate data-entry guard: strip accidental whitespace in node IDs.
KG_NODES = [(node_id.strip(), *rest) for node_id, *rest in KG_NODES]
