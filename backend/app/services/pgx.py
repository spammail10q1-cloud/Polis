"""Pharmacogenomic interpretation and conservative VCF annotation.

Design principles:
* Curated demonstration diplotypes are displayed with explicit limitations.
* A raw VCF is annotated at known variant positions but is **never** converted
  into a clinical phenotype. Star-allele calling, phasing and copy-number
  detection require validated laboratory pipelines.
* Unknown genes/variants stay unknown.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PharmacogenomicPhenotype

# Activity multipliers used only inside the *educational* simulation. They are
# not CPIC dosing values and must never be shown as measured enzyme activity.
PHENOTYPE_ACTIVITY: dict[str, dict[str, float]] = {
    "CYP2D6": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
        "rapid metabolizer": 1.3,
        "ultrarapid metabolizer": 1.8,
    },
    "CYP2C19": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
        "rapid metabolizer": 1.3,
        "ultrarapid metabolizer": 1.7,
    },
    "CYP2C9": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
    },
    "CYP3A5": {
        "poor expresser": 0.3,
        "intermediate expresser": 0.65,
        "normal expresser": 1.0,
    },
    "SLCO1B1": {
        "poor function": 0.35,
        "decreased function": 0.65,
        "normal function": 1.0,
        "increased function": 1.15,
    },
    "UGT1A1": {
        "poor metabolizer": 0.3,
        "reduced glucuronidation (intermediate)": 0.65,
        "normal metabolizer": 1.0,
    },
    "TPMT": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
    },
    "NUDT15": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
    },
    "DPYD": {
        "poor metabolizer": 0.1,
        "intermediate metabolizer": 0.5,
        "normal metabolizer": 1.0,
    },
}

GENE_INFO = [
    {
        "symbol": "CYP2D6",
        "name": "Cytochrome P450 family 2 subfamily D member 6",
        "chromosome": "22q13.2",
        "role": "Oxidative metabolism of many medicines, including beta-blockers, some antidepressants and opioids.",
        "complexity": "High. Copy-number variation, deletions, duplications and CYP2D7/2D6 hybrid genes are common.",
        "resources": ["PharmVar", "CPIC", "PharmGKB"],
        "color": "cyan",
    },
    {
        "symbol": "CYP2C19",
        "name": "Cytochrome P450 family 2 subfamily C member 19",
        "chromosome": "10q23.33",
        "role": "Metabolism of proton-pump inhibitors, clopidogrel activation, some antidepressants and antifungals.",
        "complexity": "Moderate. Common *2, *3 and *17 alleles; rare alleles may be missed by targeted panels.",
        "resources": ["CPIC", "PharmVar", "PharmGKB"],
        "color": "violet",
    },
    {
        "symbol": "CYP2C9",
        "name": "Cytochrome P450 family 2 subfamily C member 9",
        "chromosome": "10q23.33",
        "role": "Metabolism of warfarin (S-enantiomer), some NSAIDs and other medicines.",
        "complexity": "Moderate. *2 and *3 are the most studied decreased-function alleles; frequencies vary by ancestry.",
        "resources": ["CPIC", "PharmVar", "PharmGKB"],
        "color": "amber",
    },
    {
        "symbol": "CYP3A5",
        "name": "Cytochrome P450 family 3 subfamily A member 5",
        "chromosome": "7q22.1",
        "role": "Tacrolimus and some other drug metabolism; expression is polymorphic.",
        "complexity": "The common *3 allele abolishes normal expression. CYP3A4 contributes substantially and is not captured by CYP3A5 genotype alone.",
        "resources": ["CPIC", "PharmVar"],
        "color": "cyan",
    },
    {
        "symbol": "CYP3A4",
        "name": "Cytochrome P450 family 3 subfamily A member 4",
        "chromosome": "7q22.1",
        "role": "Major intestinal and hepatic drug-metabolizing enzyme for many medicines.",
        "complexity": "Highly inducible and inhibited by other drugs; genetic variation explains a smaller share of variability than for many other CYPs.",
        "resources": ["PharmGKB", "PharmVar", "FDA DDI guidance"],
        "color": "violet",
    },
    {
        "symbol": "SLCO1B1",
        "name": "Solute carrier organic anion transporter family member 1B1",
        "chromosome": "12p12.1",
        "role": "Hepatic OATP1B1 uptake transporter; affects statin exposure.",
        "complexity": "rs4149056 is common and functionally relevant, particularly for simvastatin. Effects vary by statin and dose.",
        "resources": ["CPIC", "PharmGKB"],
        "color": "amber",
    },
    {
        "symbol": "VKORC1",
        "name": "Vitamin K epoxide reductase complex subunit 1",
        "chromosome": "16p11.2",
        "role": "Target of warfarin; genotype influences pharmacodynamic sensitivity.",
        "complexity": "The -1639G>A variant is common. Warfarin response is multifactorial and requires INR monitoring.",
        "resources": ["CPIC", "PharmGKB"],
        "color": "rose",
    },
    {
        "symbol": "TPMT",
        "name": "Thiopurine S-methyltransferase",
        "chromosome": "6p22.3",
        "role": "Inactivates thiopurine metabolites; deficiency increases myelosuppression risk.",
        "complexity": "*3A is a combination of two variants. Phenotype may be discordant with genotype in some cases.",
        "resources": ["CPIC", "PharmGKB"],
        "color": "amber",
    },
    {
        "symbol": "NUDT15",
        "name": "Nudix hydrolase 15",
        "chromosome": "13q14.2",
        "role": "Inactivates thioguanine nucleotides; deficiency increases thiopurine toxicity risk.",
        "complexity": "The common *3 variant is especially relevant in East Asian and Hispanic populations. Clinical guidance combines NUDT15 and TPMT.",
        "resources": ["CPIC", "PharmGKB"],
        "color": "cyan",
    },
    {
        "symbol": "DPYD",
        "name": "Dihydropyrimidine dehydrogenase",
        "chromosome": "1p21.3",
        "role": "Rate-limiting catabolism of fluoropyrimidines.",
        "complexity": "Many reduced-function variants exist; targeted panels may miss rare variants. Deficiency can cause fatal toxicity.",
        "resources": ["CPIC", "PharmGKB", "FDA"],
        "color": "rose",
    },
    {
        "symbol": "UGT1A1",
        "name": "UDP glucuronosyltransferase family 1 member A1",
        "chromosome": "2q37.1",
        "role": "Conjugates bilirubin and SN-38 (irinotecan metabolite).",
        "complexity": "*28 is a TA-repeat variant that requires repeat-length testing; phenotype is context-dependent.",
        "resources": ["CPIC", "PharmGKB"],
        "color": "amber",
    },
]


# Curated VCF positions for annotation only. NOT a star-allele caller.
VCF_VARIANTS: dict[str, dict] = {
    "rs3892097": {"gene": "CYP2D6", "star": "*4", "consequence": "Nonfunctional splice variant"},
    "rs1065852": {"gene": "CYP2D6", "star": "*10", "consequence": "Decreased-function variant (requires diplotype context)"},
    "rs28371725": {"gene": "CYP2D6", "star": "*41", "consequence": "Decreased-function variant"},
    "rs16947": {"gene": "CYP2D6", "star": "*2", "consequence": "Variant component; haplotype context required"},
    "rs4244285": {"gene": "CYP2C19", "star": "*2", "consequence": "Nonfunctional splice variant"},
    "rs4986893": {"gene": "CYP2C19", "star": "*3", "consequence": "Premature stop codon"},
    "rs12248560": {"gene": "CYP2C19", "star": "*17", "consequence": "Increased transcription"},
    "rs1799853": {"gene": "CYP2C9", "star": "*2", "consequence": "Decreased-function variant"},
    "rs1057910": {"gene": "CYP2C9", "star": "*3", "consequence": "Decreased-function variant"},
    "rs776746": {"gene": "CYP3A5", "star": "*3", "consequence": "Loss of normal expression"},
    "rs4149056": {"gene": "SLCO1B1", "star": "*5", "consequence": "Reduced transporter function"},
    "rs9923231": {"gene": "VKORC1", "star": "-1639G>A", "consequence": "Reduced VKORC1 expression"},
    "rs1800462": {"gene": "TPMT", "star": "*2", "consequence": "Decreased TPMT activity"},
    "rs1800460": {"gene": "TPMT", "star": "*3A component", "consequence": "Decreased TPMT activity; requires haplotype context"},
    "rs1142345": {"gene": "TPMT", "star": "*3A component", "consequence": "Decreased TPMT activity; requires haplotype context"},
    "rs116855232": {"gene": "NUDT15", "star": "*3", "consequence": "Decreased NUDT15 activity"},
    "rs3918290": {"gene": "DPYD", "star": "*2A", "consequence": "Nonfunctional splice variant"},
    "rs55886062": {"gene": "DPYD", "star": "*13", "consequence": "Decreased DPYD activity"},
    "rs67376798": {"gene": "DPYD", "star": "c.2846A>T", "consequence": "Decreased DPYD activity"},
    "rs35599367": {"gene": "CYP3A4", "star": "*22", "consequence": "Reduced CYP3A4 expression"},
}


class VcfError(ValueError):
    pass


def _parse_genotype(ref: str, alt_field: str, fmt: str, sample: str) -> tuple[str, str, str] | None:
    alts = [a.strip() for a in alt_field.split(",") if a.strip() and a.strip() != "."]
    if not alts or not sample:
        return None
    keys = fmt.split(":")
    values = sample.split(":")
    if "GT" not in keys:
        return None
    gt_raw = values[keys.index("GT")] if keys.index("GT") < len(values) else ""
    gt_clean = gt_raw.replace("|", "/")
    if not gt_clean or "." in gt_clean:
        return None
    allele_indexes = [int(a) for a in gt_clean.split("/") if a.isdigit()]
    if any(index > len(alts) for index in allele_indexes):
        return None
    called = sorted({ref if index == 0 else alts[index - 1] for index in allele_indexes})
    genotype = "/".join(called)
    if len(set(allele_indexes)) == 1 and allele_indexes[0] == 0:
        zygosity = "homozygous_reference"
    elif len(set(allele_indexes)) == 1:
        zygosity = "homozygous_alternate"
    elif len(allele_indexes) == 2 and len(set(allele_indexes)) == 2:
        zygosity = "heterozygous"
    else:
        zygosity = "complex"
    alt = alts[allele_indexes[-1] - 1] if allele_indexes and allele_indexes[-1] > 0 else "."
    return genotype, zygosity, alt


def parse_vcf(text: str) -> tuple[list[dict], list[str]]:
    """Annotate known pharmacogenomic positions in a VCF.

    Returns (annotations, warnings). No phenotypes are inferred. Only small
    text VCFs are accepted; binary/BCF and genome-wide interpretation are out of
    scope for the MVP.
    """
    if not text.strip():
        raise VcfError("The uploaded file is empty.")
    if len(text) > 25_000_000:
        raise VcfError("VCF is larger than the 25 MB MVP limit.")

    warnings: list[str] = []
    annotations: list[dict] = []
    seen_samples = 0
    has_header = False

    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("##"):
            if "fileformat=VCF" not in line:
                continue
            continue
        if line.startswith("#CHROM"):
            has_header = True
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 10:
                raise VcfError("The VCF has no sample genotype column.")
            seen_samples = len(columns) - 9
            if seen_samples > 1:
                warnings.append(
                    f"The VCF contains {seen_samples} samples. POLIS annotated only the first sample; "
                    "confirm that it belongs to this account."
                )
            continue
        if line.startswith("#"):
            continue
        if not has_header:
            raise VcfError("The VCF header (#CHROM line) is missing.")

        fields = line.rstrip("\n").split("\t")
        if len(fields) < 10:
            continue
        chrom, pos, vid, ref, alt, _qual, _filt, _info, fmt = fields[:9]
        sample = fields[9]
        rsid = vid.strip()
        if rsid not in VCF_VARIANTS:
            continue
        parsed = _parse_genotype(ref, alt, fmt, sample)
        if not parsed:
            warnings.append(f"{rsid}: genotype could not be parsed and was omitted.")
            continue
        genotype, zygosity, called_alt = parsed
        metadata = VCF_VARIANTS[rsid]
        alt_alleles = alt.split(",")
        relevant_alt = called_alt if called_alt != "." else alt_alleles[0]
        variant_call = zygosity != "homozygous_reference"
        annotations.append(
            {
                "gene": metadata["gene"],
                "rsid": rsid,
                "chromosome": chrom,
                "position": int(pos) if pos.isdigit() else None,
                "ref": ref,
                "alt": relevant_alt,
                "genotype": genotype,
                "zygosity": zygosity,
                "star_allele": metadata["star"] if variant_call else None,
                "consequence": metadata["consequence"],
                "evidence_level": "curated annotation: not a clinical diplotype",
                "interpretation": (
                    f"Known {metadata['gene']} variant position {metadata['star']} detected. "
                    "This annotation alone cannot establish a diplotype or phenotype."
                    if variant_call
                    else f"Reference genotype at a known {metadata['gene']} position; other variants were not assessed here."
                ),
                "confidence": 0.6 if variant_call else 0.9,
            }
        )

    if not has_header:
        raise VcfError("The VCF header (#CHROM line) is missing.")
    if not annotations:
        warnings.append(
            "No pharmacogenomic panel positions were detected. POLIS did not infer a phenotype; "
            "genome-wide interpretation is not supported."
        )
    warnings.append(
        "VCF annotations are not a clinical pharmacogenomic result. A validated laboratory caller, "
        "phasing and copy-number analysis are required before any phenotype can be assigned."
    )
    return annotations, warnings


def gene_info(symbol: str) -> dict | None:
    return next((gene for gene in GENE_INFO if gene["symbol"] == symbol), None)


def phenotypes_for_user(db: Session, user_id: str) -> list[PharmacogenomicPhenotype]:
    return list(
        db.scalars(
            select(PharmacogenomicPhenotype)
            .where(PharmacogenomicPhenotype.user_id == user_id)
            .order_by(PharmacogenomicPhenotype.gene)
        ).all()
    )


def phenotype_map(db: Session, user_id: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in phenotypes_for_user(db, user_id):
        factor = PHENOTYPE_ACTIVITY.get(row.gene, {}).get(row.phenotype.lower())
        result[row.gene] = {
            "gene": row.gene,
            "diplotype": row.diplotype,
            "phenotype": row.phenotype,
            "activity_score": row.activity_score,
            "activity_factor": factor,
            "evidence_level": row.evidence_level,
            "guideline": row.guideline,
            "is_synthetic": row.is_synthetic,
            "source": row.source,
            "interpretation": row.interpretation,
            "limitations": row.limitations,
        }
    return result


def uninterpreted_genes(db: Session, user_id: str) -> list[dict]:
    """Return genes for which a sample exists but no phenotype has been assigned."""
    from app.models import GeneticVariant

    variants = db.scalars(select(GeneticVariant).where(GeneticVariant.user_id == user_id)).all()
    genes = {v.gene for v in variants}
    interpreted = {p.gene for p in phenotypes_for_user(db, user_id)}
    return [
        {
            "gene": gene,
            "status": "no_interpretation",
            "reason": "Variants are annotated, but no validated diplotype/phenotype was assigned. A clinical laboratory caller is required.",
        }
        for gene in sorted(genes - interpreted)
    ]


def normalize_phenotype(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip().lower())
    return cleaned
