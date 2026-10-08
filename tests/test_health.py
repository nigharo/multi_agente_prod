import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test")


@pytest.mark.parametrize(
    "module",
    ["multi_agent.orchestrator.api", "multi_agent.verifier.api", "multi_agent.rag.api"],
)
def test_health(module):
    import importlib

    app = importlib.import_module(module).app
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
