from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import ModelVersion

router = APIRouter(prefix="/models", tags=["model-validation"])


@router.get("")
def list_models(user: CurrentUser, db: DbSession) -> dict:
    """Model registry and validation status.

    Experimental models are intentionally separated from any clinically
    validated module. No model in this deployment is clinically validated.
    """
    rows = list(db.scalars(select(ModelVersion).order_by(ModelVersion.name)).all())
    return {
        "models": [
            {
                "id": row.id,
                "name": row.name,
                "version": row.version,
                "status": row.status,
                "description": row.description,
                "limitations": row.limitations,
                "validation_summary": row.validation_summary,
                "clinically_validated": False,
            }
            for row in rows
        ],
        "validation_policy": (
            "No model listed here is clinically validated. Experimental / demonstration status is shown explicitly. "
            "Clinical validation would require external datasets, calibration, subgroup performance analysis, "
            "prospective study and regulatory assessment."
        ),
    }
