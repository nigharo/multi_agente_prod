from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langgraph.checkpoint.memory import InMemorySaver

from multi_agent.common.llm import get_llm
from multi_agent.common.schemas import OnboardingDecision
from multi_agent.orchestrator.state import OnboardingState
from multi_agent.orchestrator.tools import TOOLS

SYSTEM_PROMPT = """Eres el Agente Orquestador del onboarding digital de clientes del banco.
No decides con conocimiento propio: delegas y consolidas.

Flujo obligatorio para una nueva solicitud:
1. `delegate_verification` con el nombre y documento del prospecto.
2. `delegate_documentation` con el producto y el contexto (incluye nivel de riesgo y
   confianza de identidad obtenidos en el paso 1).
3. Emite la decisión final:
   - "apto": identidad verificada (confianza >= 0.8), riesgo no high y elegible por política.
   - "no_apto": incumple políticas de forma clara.
   - "requiere_escalamiento": cualquier verificación falla, es ambigua o un agente no responde.
   Si el estado no es "apto", `proposed_solution` es obligatoria y debe ser accionable.
   `client_message` debe ser cordial y no revelar detalles de listas de riesgo.

En mensajes de seguimiento de la misma sesión, usa el historial; vuelve a delegar solo
si el cliente aporta datos nuevos que cambien una verificación."""


def build_agent():
    # InMemorySaver mantiene el estado por session_id; usar un checkpointer persistente
    # (langgraph-checkpoint-postgres / redis) si se escala a más de una réplica.
    return create_agent(
        get_llm(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        state_schema=OnboardingState,
        response_format=ToolStrategy(OnboardingDecision),
        checkpointer=InMemorySaver(),
        name="orchestrator",
    )
