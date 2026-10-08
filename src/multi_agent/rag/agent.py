from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel, Field

from multi_agent.common.llm import get_llm
from multi_agent.rag.tools import TOOLS

SYSTEM_PROMPT = """Eres el Agente de Documentación y Políticas de onboarding de un banco.
1. Usa `search_policies` para recuperar las políticas aplicables al producto y al perfil
   del prospecto (riesgo, verificación de identidad).
2. Usa `prepare_documentation` para obtener los documentos requeridos.
Basa tus conclusiones solo en las políticas recuperadas y cita las fuentes como [n].
Si las políticas no cubren el caso o son ambiguas, indícalo en `policy_gaps`."""


class DocumentationResult(BaseModel):
    product: str
    product_supported: bool
    required_documents: list[str]
    applicable_policies: list[str] = Field(description="Reglas de política aplicables, con cita.")
    eligible_by_policy: bool | None = Field(
        description="True/False según políticas; None si no se puede determinar."
    )
    policy_gaps: list[str] = Field(default_factory=list)


def build_agent():
    return create_agent(
        get_llm(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(DocumentationResult),
        name="documentation",
    )
