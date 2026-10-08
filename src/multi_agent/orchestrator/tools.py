"""Tools de delegación del orquestador.

Cada tool llama por HTTP al contenedor del agente especializado y guarda el resultado
en el estado del grafo (Command(update=...)).
"""

import json

import httpx
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from multi_agent.common.config import get_settings
from multi_agent.common.schemas import AgentResponse


async def _call_agent(base_url: str, query: str) -> AgentResponse:
    async with httpx.AsyncClient(timeout=get_settings().agent_timeout_seconds) as client:
        resp = await client.post(f"{base_url}/invoke", json={"query": query})
        resp.raise_for_status()
        return AgentResponse.model_validate(resp.json())


def _error_command(runtime: ToolRuntime, agent: str, exc: Exception) -> Command:
    error = f"{agent} no disponible: {type(exc).__name__} {exc}"
    return Command(
        update={
            "agent_errors": [*runtime.state.get("agent_errors", []), error],
            "messages": [ToolMessage(error, tool_call_id=runtime.tool_call_id, status="error")],
        }
    )


@tool
async def delegate_verification(
    prospect_name: str, document_id: str, runtime: ToolRuntime
) -> Command:
    """Delega al Agente Verificador: verificación de identidad y consulta de listas de riesgo.

    Args:
        prospect_name: nombre completo del prospecto.
        document_id: número de documento de identidad.
    """
    query = (
        "Verifica al prospecto y consulta listas de riesgo.\n"
        f"Nombre: {prospect_name}\nDocumento: {document_id}"
    )
    try:
        result = await _call_agent(get_settings().verifier_agent_url, query)
    except httpx.HTTPError as exc:
        return _error_command(runtime, "Agente verificador", exc)
    payload = {"summary": result.structured or result.answer, "tool_results": result.tool_results}
    return Command(
        update={
            "identity": result.tool_results.get("verify_identity"),
            "risk": result.tool_results.get("check_risk_lists"),
            "verification": result.structured,
            "messages": [
                ToolMessage(
                    json.dumps(payload, ensure_ascii=False), tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )


@tool
async def delegate_documentation(
    product: str, client_context: str, runtime: ToolRuntime
) -> Command:
    """Delega al Agente de Documentación: políticas aplicables (RAG) y documentos requeridos.

    Args:
        product: código del producto solicitado (p. ej. cuenta_ahorros).
        client_context: datos del prospecto y resultados de verificación relevantes
            (nombre, documento, nivel de riesgo, confianza de identidad).
    """
    query = (
        f"Producto solicitado: {product}\nContexto del prospecto: {client_context}\n"
        "Determina políticas aplicables, elegibilidad y documentos requeridos."
    )
    try:
        result = await _call_agent(get_settings().rag_agent_url, query)
    except httpx.HTTPError as exc:
        return _error_command(runtime, "Agente de documentación", exc)
    payload = {"summary": result.structured or result.answer, "tool_results": result.tool_results}
    return Command(
        update={
            "documentation": result.structured
            or {"tool_results": result.tool_results, "answer": result.answer},
            "messages": [
                ToolMessage(
                    json.dumps(payload, ensure_ascii=False), tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )


TOOLS = [delegate_verification, delegate_documentation]
