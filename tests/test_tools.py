from multi_agent.rag.tools import prepare_documentation
from multi_agent.verifier.tools import check_risk_lists, verify_identity


def test_verify_identity_happy_path():
    r = verify_identity.invoke({"document_id": "1712345678"})
    assert r == {"verified": True, "confidence": 0.95, "requires_escalation": False}


def test_verify_identity_low_confidence_escalates():
    assert verify_identity.invoke({"document_id": "0912345670"})["requires_escalation"]


def test_verify_identity_invalid_format():
    r = verify_identity.invoke({"document_id": "abc"})
    assert not r["verified"] and r["requires_escalation"]


def test_risk_low():
    r = check_risk_lists.invoke({"name": "Juan Perez", "document_id": "1712345678"})
    assert r["risk_level"] == "low" and r["matches"] == []


def test_risk_high_by_name_escalates():
    r = check_risk_lists.invoke({"name": "Carlos  Riesgo ALTO", "document_id": "1"})
    assert r["risk_level"] == "high" and r["requires_escalation"]


def test_prepare_documentation_medium_risk_adds_document():
    r = prepare_documentation.invoke(
        {"product": "cuenta_ahorros", "client_data": {"risk_level": "medium"}}
    )
    assert "Declaración de origen lícito de fondos" in r["required_documents"]


def test_prepare_documentation_unsupported_product():
    r = prepare_documentation.invoke({"product": "hipoteca", "client_data": {}})
    assert r["supported"] is False
