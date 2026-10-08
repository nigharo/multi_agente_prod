import json
import uuid

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage

from multi_agent.common.schemas import (
    FollowUpRequest,
    HealthResponse,
    OnboardingRequest,
    OnboardingResponse,
)
from multi_agent.orchestrator.agent import build_agent

app = FastAPI(title="API Orquestador de Onboarding")
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


async def _run(session_id: str, payload: dict) -> OnboardingResponse:
    try:
        state = await get_agent().ainvoke(
            payload, config={"configurable": {"thread_id": session_id}}
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error en orquestador: {exc}") from exc
    return OnboardingResponse(
        session_id=session_id,
        decision=state["structured_response"],
        identity=state.get("identity"),
        risk=state.get("risk"),
        documentation=state.get("documentation"),
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="orchestrator")


@app.post("/api/v1/onboarding/start", response_model=OnboardingResponse)
async def start(req: OnboardingRequest) -> OnboardingResponse:
    session_id = req.session_id or str(uuid.uuid4())
    prospect = req.model_dump(exclude={"session_id"})
    message = "Nueva solicitud de onboarding:\n" + json.dumps(prospect, ensure_ascii=False)
    return await _run(
        session_id,
        {
            "messages": [HumanMessage(message)],
            "prospect": prospect,
            "identity": None,
            "risk": None,
            "verification": None,
            "documentation": None,
            "agent_errors": [],
        },
    )


@app.post("/api/v1/onboarding/{session_id}/message", response_model=OnboardingResponse)
async def follow_up(session_id: str, req: FollowUpRequest) -> OnboardingResponse:
    """Continúa la conversación de una sesión (p. ej. el cliente aporta datos para resolver
    un escalamiento). El estado previo se recupera del checkpointer."""
    snapshot = await get_agent().aget_state({"configurable": {"thread_id": session_id}})
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return await _run(session_id, {"messages": [HumanMessage(req.message)]})


@app.get("/api/v1/onboarding/{session_id}")
async def get_session(session_id: str) -> dict:
    snapshot = await get_agent().aget_state({"configurable": {"thread_id": session_id}})
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    values = snapshot.values
    return {
        "session_id": session_id,
        "prospect": values.get("prospect"),
        "identity": values.get("identity"),
        "risk": values.get("risk"),
        "documentation": values.get("documentation"),
        "agent_errors": values.get("agent_errors", []),
        "messages": [{"type": m.type, "content": m.content} for m in values.get("messages", [])],
    }
