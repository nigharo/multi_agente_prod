from multi_agent.common.agent_app import build_agent_app
from multi_agent.verifier.agent import build_agent

app = build_agent_app("verifier-agent", build_agent)
