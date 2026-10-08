from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Contrato entre orquestador y agentes especializados (/invoke) ---


class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1)


class AgentResponse(BaseModel):
    agent: str
    answer: str
    structured: dict[str, Any] | None = None
    # Salidas crudas de las tools ejecutadas ({tool_name: resultado}); el orquestador
    # aplica las reglas de política sobre estos datos, no sobre el texto del LLM.
    tool_results: dict[str, Any] = Field(default_factory=dict)


# --- API pública del orquestador ---


class OnboardingRequest(BaseModel):
    prospect_name: str = Field(..., min_length=1, examples=["Juan Perez"])
    document_id: str = Field(..., min_length=1, examples=["1712345678"])
    product: str = Field(..., min_length=1, examples=["cuenta_ahorros"])
    session_id: str | None = None


class FollowUpRequest(BaseModel):
    message: str = Field(..., min_length=1)


OnboardingStatus = Literal["apto", "no_apto", "requiere_escalamiento"]


class OnboardingDecision(BaseModel):
    """Decisión final del orquestador (structured output del LLM)."""

    status: OnboardingStatus
    reasons: list[str] = Field(description="Motivos de la decisión, citando cada verificación.")
    required_documents: list[str] = Field(default_factory=list)
    proposed_solution: str | None = Field(
        default=None,
        description="Obligatoria si status != 'apto': acción concreta para resolver el caso.",
    )
    client_message: str = Field(description="Mensaje final, cordial y claro, para el cliente.")


class OnboardingResponse(BaseModel):
    session_id: str
    decision: OnboardingDecision
    identity: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    documentation: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
