from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import GeneticSample, GeneticVariant
from app.schemas import GeneticSampleOut, GeneticsOverview, PhenotypeOut, VariantOut
from app.services import audit
from app.services.pgx import GENE_INFO, parse_vcf, phenotypes_for_user, uninterpreted_genes, VcfError

router = APIRouter(prefix="/genetics", tags=["genetics"])

DISCLAIMER = (
    "POLIS displays curated demonstration pharmacogenomic interpretations and conservative VCF annotations. "
    "It is not a clinical genetic test. A phenotype must not be inferred from incomplete data, and no medication "
    "decision should be based on this output. Clinical pharmacogenomic testing requires an accredited laboratory, "
    "validated star-allele calling, phasing and copy-number analysis, and professional interpretation."
)


def _overview(db, user_id: str) -> GeneticsOverview:
    samples = list(
        db.scalars(
            select(GeneticSample)
            .where(GeneticSample.user_id == user_id)
            .order_by(GeneticSample.created_at.desc())
        ).all()
    )
    variants = list(
        db.scalars(
            select(GeneticVariant)
            .where(GeneticVariant.user_id == user_id)
            .order_by(GeneticVariant.gene, GeneticVariant.rsid)
        ).all()
    )
    phenotypes = phenotypes_for_user(db, user_id)
    return GeneticsOverview(
        samples=[GeneticSampleOut.model_validate(sample) for sample in samples],
        variants=[VariantOut.model_validate(variant) for variant in variants],
        phenotypes=[PhenotypeOut.model_validate(phenotype) for phenotype in phenotypes],
        uninterpreted_genes=uninterpreted_genes(db, user_id),
        gene_catalog=GENE_INFO,
        disclaimer=DISCLAIMER,
    )


@router.get("", response_model=GeneticsOverview)
def get_genetics(user: CurrentUser, db: DbSession) -> GeneticsOverview:
    return _overview(db, user.id)


@router.get("/samples", response_model=list[GeneticSampleOut])
def get_samples(user: CurrentUser, db: DbSession) -> list[GeneticSampleOut]:
    rows = db.scalars(
        select(GeneticSample).where(GeneticSample.user_id == user.id).order_by(GeneticSample.created_at.desc())
    ).all()
    return [GeneticSampleOut.model_validate(row) for row in rows]


@router.get("/variants", response_model=list[VariantOut])
def get_variants(user: CurrentUser, db: DbSession, gene: str | None = None) -> list[VariantOut]:
    stmt = select(GeneticVariant).where(GeneticVariant.user_id == user.id)
    if gene:
        stmt = stmt.where(GeneticVariant.gene == gene.upper())
    rows = db.scalars(stmt.order_by(GeneticVariant.gene, GeneticVariant.rsid)).all()
    return [VariantOut.model_validate(row) for row in rows]


@router.get("/pharmacogenomics", response_model=list[PhenotypeOut])
def get_pharmacogenomics(user: CurrentUser, db: DbSession) -> list[PhenotypeOut]:
    return [PhenotypeOut.model_validate(row) for row in phenotypes_for_user(db, user.id)]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_vcf(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> dict:
    filename = (file.filename or "upload.vcf").strip()
    content = await file.read()
    if len(content) > 25_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="VCF exceeds the 25 MB MVP limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="VCF must be UTF-8 text.") from exc
    try:
        annotations, warnings = parse_vcf(text)
    except VcfError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    sample = GeneticSample(
        user_id=user.id,
        source="vcf_upload",
        file_name=filename,
        genome_build="declared in VCF (not independently validated)",
        status="annotated_needs_clinical_interpretation",
        variant_count=len(annotations),
        is_synthetic=False,
        provenance={
            "parser": "POLIS conservative VCF annotator v0.1",
            "phenotypes_inferred": 0,
            "warning": "Raw VCF is not a clinical pharmacogenomic result.",
        },
        notes="Uploaded VCF. Known panel positions annotated only; no diplotype or phenotype was inferred.",
    )
    db.add(sample)
    db.flush()
    for annotation in annotations:
        db.add(
            GeneticVariant(
                sample_id=sample.id,
                user_id=user.id,
                gene=annotation["gene"],
                rsid=annotation["rsid"],
                chromosome=annotation["chromosome"],
                position=annotation["position"],
                ref=annotation["ref"],
                alt=annotation["alt"],
                genotype=annotation["genotype"],
                zygosity=annotation["zygosity"],
                star_allele=annotation["star_allele"],
                consequence=annotation["consequence"],
                interpretation=annotation["interpretation"],
                evidence_level=annotation["evidence_level"],
                source=f"Annotated from uploaded VCF: {filename}",
                confidence=annotation["confidence"],
                is_synthetic=False,
            )
        )
    audit.record(
        db,
        user_id=user.id,
        action="genetics.vcf_upload",
        resource_type="genetic_sample",
        resource_id=sample.id,
        detail={"filename": filename, "annotated_variants": len(annotations), "phenotypes_inferred": 0},
    )
    db.commit()
    return {
        "sample": GeneticSampleOut.model_validate(sample).model_dump(),
        "annotated_variants": len(annotations),
        "phenotypes_inferred": 0,
        "warnings": warnings,
        "message": (
            "Known panel positions were annotated. POLIS did not infer a phenotype from this VCF. "
            "Clinical interpretation requires a validated laboratory pipeline."
        ),
    }


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(sample_id: str, user: CurrentUser, db: DbSession) -> None:
    sample = db.scalar(
        select(GeneticSample).where(GeneticSample.id == sample_id, GeneticSample.user_id == user.id)
    )
    if not sample:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Genetic sample not found.")
    db.delete(sample)
    audit.record(db, user_id=user.id, action="genetics.delete_sample", resource_type="genetic_sample", resource_id=sample_id)
    db.commit()
