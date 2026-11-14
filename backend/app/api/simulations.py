from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import Simulation
from app.schemas import SimulationRequest
from app.services import audit
from app.services.simulation import MedicationNotFoundError, run_simulation

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _summary(simulation: Simulation) -> dict:
    output = simulation.output_json or {}
    return {
        "id": simulation.id,
        "medication_name": simulation.medication_name,
        "dose_text": simulation.dose_text,
        "route": simulation.route,
        "frequency": simulation.frequency,
        "status": simulation.status,
        "engine_version": simulation.engine_version,
        "created_at": simulation.created_at.isoformat(),
        "headline": output.get("headline"),
        "model_status": (output.get("model") or {}).get("status"),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_simulation(payload: SimulationRequest, user: CurrentUser, db: DbSession) -> dict:
    try:
        simulation = run_simulation(db, user, payload)
    except MedicationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    audit.record(
        db,
        user_id=user.id,
        action="simulations.run",
        resource_type="simulation",
        resource_id=simulation.id,
        detail={
            "medication_id": simulation.medication_id,
            "status": simulation.status,
            "engine_version": simulation.engine_version,
        },
    )
    db.commit()
    db.refresh(simulation)
    return {
        "id": simulation.id,
        "created_at": simulation.created_at.isoformat(),
        "status": simulation.status,
        "engine_version": simulation.engine_version,
        "input": simulation.input_json,
        "result": simulation.output_json,
        "evidence": simulation.evidence_json,
    }


@router.get("")
def list_simulations(user: CurrentUser, db: DbSession) -> list[dict]:
    rows = db.scalars(
        select(Simulation)
        .where(Simulation.user_id == user.id)
        .order_by(Simulation.created_at.desc())
        .limit(30)
    ).all()
    return [_summary(row) for row in rows]


@router.get("/{simulation_id}")
def get_simulation(simulation_id: str, user: CurrentUser, db: DbSession) -> dict:
    simulation = db.scalar(
        select(Simulation).where(Simulation.id == simulation_id, Simulation.user_id == user.id)
    )
    if not simulation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Simulation not found.")
    return {
        "id": simulation.id,
        "created_at": simulation.created_at.isoformat(),
        "status": simulation.status,
        "engine_version": simulation.engine_version,
        "input": simulation.input_json,
        "result": simulation.output_json,
        "evidence": simulation.evidence_json,
    }


@router.get("/{simulation_id}/evidence")
def get_simulation_evidence(simulation_id: str, user: CurrentUser, db: DbSession) -> dict:
    simulation = db.scalar(
        select(Simulation).where(Simulation.id == simulation_id, Simulation.user_id == user.id)
    )
    if not simulation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Simulation not found.")
    return {
        "simulation_id": simulation.id,
        "engine_version": simulation.engine_version,
        "evidence": simulation.evidence_json,
        "model": (simulation.output_json or {}).get("model"),
        "disclaimer": (simulation.output_json or {}).get("disclaimer"),
    }
