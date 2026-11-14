from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import CurrentUser, DbSession
from app.models import KnowledgeGraphEdge, KnowledgeGraphNode
from app.schemas import TwinOverview, TwinSystemDetail
from app.services.twin import build_overview, build_system_detail

router = APIRouter(prefix="/twin", tags=["digital-twin"])


@router.get("", response_model=TwinOverview)
def twin(user: CurrentUser, db: DbSession) -> TwinOverview:
    return build_overview(db, user.id)


@router.get("/completeness")
def completeness(user: CurrentUser, db: DbSession) -> dict:
    overview = build_overview(db, user.id)
    return {
        "overall_completeness": overview.overall_completeness,
        "not_a_health_score": True,
        "note": "Completeness measures data coverage across curated systems; it says nothing about health status.",
        "systems": [
            {
                "id": system.id,
                "name": system.name,
                "completeness": system.completeness,
                "measurements": system.measurements,
                "status": system.status,
            }
            for system in overview.systems
        ],
    }


@router.get("/knowledge-graph")
def knowledge_graph(user: CurrentUser, db: DbSession) -> dict:
    nodes = db.scalars(select(KnowledgeGraphNode)).all()
    edges = db.scalars(select(KnowledgeGraphEdge)).all()
    return {
        "nodes": [
            {"id": node.id, "kind": node.kind, "label": node.label, "description": node.description}
            for node in nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "relation": edge.relation,
                "evidence_level": edge.evidence_level,
                "source": edge.source,
            }
            for edge in edges
        ],
        "disclaimer": (
            "A small curated starter graph for navigation and explanation. It is not a complete biological "
            "knowledge base, and edges are not causal effect estimates for this individual."
        ),
    }


@router.get("/systems/{system_id}", response_model=TwinSystemDetail)
def system_detail(system_id: str, user: CurrentUser, db: DbSession) -> TwinSystemDetail:
    detail = build_system_detail(db, user.id, system_id)
    if not detail:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown biological system.")
    return detail
