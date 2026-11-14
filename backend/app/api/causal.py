from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.security import CurrentUser, DbSession
from app.schemas import CausalRequest
from app.services import audit
from app.services.causal import catalog, run_causal_query

router = APIRouter(prefix="/causal", tags=["causal-lab"])


@router.get("/catalog")
def causal_catalog(user: CurrentUser) -> dict:
    return catalog()


@router.post("/simulate")
def causal_simulate(payload: CausalRequest, user: CurrentUser, db: DbSession) -> dict:
    try:
        result = run_causal_query(
            db,
            user_id=user.id,
            treatment=payload.treatment,
            outcome=payload.outcome,
            delta=payload.delta,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    audit.record(
        db,
        user_id=user.id,
        action="causal.simulate",
        resource_type="causal_query",
        detail={
            "treatment": payload.treatment,
            "outcome": payload.outcome,
            "delta": payload.delta,
            "status": result.get("status"),
        },
    )
    db.commit()
    return result
