from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.limits import assistant_limit
from app.core.security import CurrentUser, DbSession
from app.models import UserConsent
from app.schemas import AssistantAnswer, ChatRequest, ExplainRequest
from app.services import audit, llm
from app.services.assistant import answer_chat, explain_entity

router = APIRouter(prefix="/assistant", tags=["assistant"])

DISCLAIMER = (
    "POLIS AI is not a clinician and does not provide diagnosis, treatment, prescribing, or dosing. "
    "For urgent symptoms, contact local emergency services."
)


def _require_ai_consent(db, user_id: str) -> UserConsent:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user_id))
    if not consent or not consent.ai_processing:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "AI processing consent is not enabled for this account. Enable it in Privacy & Data before using "
                "the assistant. The rest of POLIS remains available."
            ),
        )
    return consent


@router.get("/status")
def assistant_status(user: CurrentUser, db: DbSession) -> dict:
    consent = db.scalar(select(UserConsent).where(UserConsent.user_id == user.id))
    return {
        "ai_processing_consent": bool(consent and consent.ai_processing),
        "engine": "grounded external model" if llm.enabled() else "deterministic grounded synthesis",
        "external_llm_configured": llm.enabled(),
        "retrieval": "local curated evidence corpus (hybrid hashed embedding + lexical)",
        "disclaimer": DISCLAIMER,
    }


@router.post("/chat", response_model=AssistantAnswer)
def chat(payload: ChatRequest, request: Request, user: CurrentUser, db: DbSession) -> AssistantAnswer:
    _require_ai_consent(db, user.id)
    assistant_limit(request)
    answer = answer_chat(db, user, payload.message, payload.history)
    audit.record(
        db,
        user_id=user.id,
        action="assistant.chat",
        resource_type="assistant_exchange",
        detail={
            "intent": answer.intent,
            "message_length": len(payload.message),
            "citations": len(answer.citations),
            "engine": answer.engine,
        },
    )
    db.commit()
    return answer


@router.post("/explain", response_model=AssistantAnswer)
def explain(payload: ExplainRequest, request: Request, user: CurrentUser, db: DbSession) -> AssistantAnswer:
    _require_ai_consent(db, user.id)
    assistant_limit(request)
    answer = explain_entity(db, user, payload.entity)
    audit.record(
        db,
        user_id=user.id,
        action="assistant.explain",
        resource_type="assistant_exchange",
        detail={"intent": answer.intent, "entity_length": len(payload.entity), "engine": answer.engine},
    )
    db.commit()
    return answer
