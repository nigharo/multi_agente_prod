"""Fábrica de la API HTTP que expone cada agente especializado en su contenedor."""

import json

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, ToolMessage

from multi_agent.common.schemas import AgentRequest, AgentResponse, HealthResponse


def _collect_tool_results(messages) -> dict:
    results = {}
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name:
            try:
                results[msg.name] = json.loads(msg.content)
            except (TypeError, json.JSONDecodeError):
                results[msg.name] = msg.content
    return results


def build_agent_app(name: str, agent_factory) -> FastAPI:
    app = FastAPI(title=name)
    agent = None

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(service=name)

    @app.post("/invoke", response_model=AgentResponse)
    async def invoke(req: AgentRequest) -> AgentResponse:
        nonlocal agent
        if agent is None:
            agent = agent_factory()
        try:
            result = await agent.ainvoke({"messages": [HumanMessage(req.query)]})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Error en {name}: {exc}") from exc
        structured = result.get("structured_response")
        return AgentResponse(
            agent=name,
            answer=result["messages"][-1].content,
            structured=structured.model_dump() if structured is not None else None,
            tool_results=_collect_tool_results(result["messages"]),
        )

    return app
