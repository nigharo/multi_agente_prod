"""Tools mock del agente verificador (identidad y listas de riesgo)."""

import unicodedata

from langchain_core.tools import tool

from multi_agent.common.policies import ESCALATION_RISK_LEVELS, IDENTITY_CONFIDENCE_THRESHOLD

# Escenarios deterministas para pruebas: document_id -> (verified, confidence)
IDENTITY_SCENARIOS = {
    "1712345678": (True, 0.95),  # caso feliz
    "0912345670": (True, 0.62),  # verificado con baja confianza -> escalamiento
    "1700000000": (False, 0.90),  # no coincide con el registro civil -> no apto
}

# Lista de vigilancia mock (OFAC, PEP, listas internas)
WATCHLIST = [
    {"name": "carlos riesgo alto", "document_id": "1799999999", "list": "OFAC", "risk": "high"},
    {"name": "ana expuesta", "document_id": "1788888888", "list": "PEP", "risk": "medium"},
]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


@tool
def verify_identity(document_id: str) -> dict:
    """Tool 1: verifica la identidad del prospecto contra el registro civil (mock).

    Retorna {"verified": bool, "confidence": 0.0-1.0, "requires_escalation": bool}.
    Si la confianza es menor a 0.8 se requiere escalamiento.
    """
    doc = document_id.strip()
    if doc in IDENTITY_SCENARIOS:
        verified, confidence = IDENTITY_SCENARIOS[doc]
    elif doc.isdigit() and len(doc) == 10:
        verified, confidence = True, 0.85
    else:
        verified, confidence = False, 0.10
    return {
        "verified": verified,
        "confidence": confidence,
        "requires_escalation": confidence < IDENTITY_CONFIDENCE_THRESHOLD,
    }


@tool
def check_risk_lists(name: str, document_id: str) -> dict:
    """Tool 2: consulta listas de riesgo (OFAC, PEP, internas) por nombre y documento (mock).

    Retorna {"risk_level": "low|medium|high", "matches": [...], "requires_escalation": bool}.
    Si el nivel es high se requiere escalamiento.
    """
    norm_name, doc = _normalize(name), document_id.strip()
    matches = [
        {
            "list": e["list"],
            "matched_on": "document_id" if e["document_id"] == doc else "name",
            "risk": e["risk"],
        }
        for e in WATCHLIST
        if e["document_id"] == doc or e["name"] == norm_name
    ]
    order = ["low", "medium", "high"]
    risk_level = max((m["risk"] for m in matches), key=order.index, default="low")
    return {
        "risk_level": risk_level,
        "matches": matches,
        "requires_escalation": risk_level in ESCALATION_RISK_LEVELS,
    }


TOOLS = [verify_identity, check_risk_lists]
