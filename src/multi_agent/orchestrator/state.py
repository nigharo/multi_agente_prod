from typing import Any, NotRequired

from langchain.agents import AgentState


class OnboardingState(AgentState):
    """Estado del flujo de onboarding, persistido por session_id (thread_id)."""

    prospect: NotRequired[dict[str, Any]]
    identity: NotRequired[dict[str, Any] | None]
    risk: NotRequired[dict[str, Any] | None]
    verification: NotRequired[dict[str, Any] | None]
    documentation: NotRequired[dict[str, Any] | None]
    agent_errors: NotRequired[list[str]]
