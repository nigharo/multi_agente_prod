"""Tools del agente de documentación: búsqueda de políticas (RAG) y Tool 3 (mock)."""

from langchain_core.tools import tool

from multi_agent.common.policies import SUPPORTED_PRODUCTS
from multi_agent.rag.vectorstore import get_vectorstore

_vectorstore = None

BASE_DOCUMENTS = ["Cédula de identidad (anverso y reverso)", "Selfie de validación biométrica"]
PRODUCT_DOCUMENTS = {
    "cuenta_ahorros": ["Planilla de servicio básico (máx. 3 meses)"],
    "cuenta_corriente": [
        "Planilla de servicio básico (máx. 3 meses)",
        "Certificado de ingresos o rol de pagos",
        "Referencia bancaria",
    ],
    "tarjeta_credito": [
        "Certificado de ingresos o rol de pagos",
        "Declaración de impuestos del último año",
        "Autorización de consulta al buró de crédito",
    ],
}


@tool
def search_policies(query: str, k: int = 4) -> str:
    """Busca fragmentos de las políticas de onboarding del banco en la DB vectorial.

    Args:
        query: pregunta o términos de búsqueda sobre políticas.
        k: número de fragmentos a recuperar.
    """
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    docs = _vectorstore.similarity_search(query, k=k)
    if not docs:
        return "No se encontraron políticas relevantes."
    return "\n\n".join(
        f"[{i}] (fuente: {d.metadata.get('source', 'desconocida')})\n{d.page_content}"
        for i, d in enumerate(docs, 1)
    )


@tool
def prepare_documentation(product: str, client_data: dict) -> dict:
    """Tool 3: retorna los documentos requeridos para abrir el producto (mock).

    Args:
        product: código del producto (cuenta_ahorros, cuenta_corriente, tarjeta_credito).
        client_data: datos del prospecto (nombre, documento, nivel de riesgo, etc.).
    """
    if product not in SUPPORTED_PRODUCTS:
        return {
            "product": product,
            "supported": False,
            "required_documents": [],
            "notes": [f"Producto no soportado. Productos válidos: {sorted(SUPPORTED_PRODUCTS)}"],
        }
    documents = BASE_DOCUMENTS + PRODUCT_DOCUMENTS[product]
    notes = []
    if client_data.get("risk_level") == "medium":
        documents = documents + ["Declaración de origen lícito de fondos"]
        notes.append("Debida diligencia reforzada por riesgo medio.")
    return {
        "product": product,
        "supported": True,
        "required_documents": documents,
        "notes": notes,
    }


TOOLS = [search_policies, prepare_documentation]
