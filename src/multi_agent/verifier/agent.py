from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel, Field

from multi_agent.common.llm import get_llm
from multi_agent.verifier.tools import TOOLS

SYSTEM_PROMPT = """Eres el Agente Verificador de Identidad y Listas de Riesgo de un banco.
Para cada prospecto SIEMPRE ejecuta ambas tools:
1. `verify_identity(document_id)`
2. `check_risk_lists(name, document_id)`
Resume los resultados sin alterar los valores retornados por las tools.
Si alguna tool indica `requires_escalation`, explica el motivo y sugiere una acción
de mitigación concreta (p. ej. validación biométrica, revisión de oficial de cumplimiento)."""


class VerificationResult(BaseModel):
    identity_verified: bool
    identity_confidence: float
    risk_level: str
    requires_escalation: bool
    findings: list[str] = Field(description="Hallazgos relevantes de las verificaciones.")
    suggested_mitigation: str | None = None


def build_agent():
    return create_agent(
        get_llm(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(VerificationResult),
        name="verifier",
    )
