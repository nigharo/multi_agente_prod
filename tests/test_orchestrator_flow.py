"""Flujo end-to-end del orquestador con un LLM falso y los sub-agentes HTTP mockeados."""

import pytest
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from multi_agent.common.schemas import AgentResponse, OnboardingDecision
from multi_agent.orchestrator import api, tools
from multi_agent.orchestrator.agent import SYSTEM_PROMPT
from multi_agent.orchestrator.state import OnboardingState


class ToolCallingFake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _call(name, args, i):
    return {"name": name, "args": args, "id": f"call_{i}", "type": "tool_call"}


def _script(status):
    return [
        AIMessage(
            "",
            tool_calls=[
                _call(
                    "delegate_verification", {"prospect_name": "Juan Perez", "document_id": "x"}, 1
                )
            ],
        ),
        AIMessage(
            "",
            tool_calls=[
                _call(
                    "delegate_documentation",
                    {"product": "cuenta_ahorros", "client_context": "x"},
                    2,
                )
            ],
        ),
        AIMessage(
            "",
            tool_calls=[
                _call(
                    "OnboardingDecision",
                    {"status": status, "reasons": ["LLM"], "client_message": "Hola"},
                    3,
                )
            ],
        ),
    ]


@pytest.fixture
def client(monkeypatch, request):
    identity, status = request.param
    agent = create_agent(
        ToolCallingFake(responses=_script(status)),
        tools=tools.TOOLS,
        system_prompt=SYSTEM_PROMPT,
        state_schema=OnboardingState,
        response_format=OnboardingDecision,
        checkpointer=InMemorySaver(),
    )
    monkeypatch.setattr(api, "_agent", agent)

    async def fake_call_agent(base_url, query):
        if "Verifica" in query:
            return AgentResponse(
                agent="verifier",
                answer="ok",
                tool_results={
                    "verify_identity": identity,
                    "check_risk_lists": {"risk_level": "low", "matches": []},
                },
            )
        return AgentResponse(
            agent="documentation",
            answer="ok",
            structured={
                "product": "cuenta_ahorros",
                "product_supported": True,
                "required_documents": ["Cédula"],
                "applicable_policies": [],
                "eligible_by_policy": True,
                "policy_gaps": [],
            },
        )

    monkeypatch.setattr(tools, "_call_agent", fake_call_agent)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test")
    return TestClient(api.app)


BODY = {"prospect_name": "Juan Perez", "document_id": "1712345678", "product": "cuenta_ahorros"}


@pytest.mark.parametrize(
    "client", [({"verified": True, "confidence": 0.95}, "apto")], indirect=True
)
def test_flow_apto_and_session_state(client):
    r = client.post("/api/v1/onboarding/start", json=BODY).json()
    assert r["decision"]["status"] == "apto"
    assert r["identity"]["confidence"] == 0.95
    assert r["documentation"]["required_documents"] == ["Cédula"]

    session = client.get(f"/api/v1/onboarding/{r['session_id']}").json()
    assert session["prospect"]["document_id"] == "1712345678"
    assert session["risk"]["risk_level"] == "low"


def test_unknown_session_404(monkeypatch):
    monkeypatch.setattr(
        api,
        "_agent",
        create_agent(
            ToolCallingFake(responses=[]),
            tools=tools.TOOLS,
            state_schema=OnboardingState,
            checkpointer=InMemorySaver(),
        ),
    )
    assert TestClient(api.app).get("/api/v1/onboarding/nope").status_code == 404
