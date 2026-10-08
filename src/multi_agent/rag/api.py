from multi_agent.common.agent_app import build_agent_app
from multi_agent.rag.agent import build_agent

app = build_agent_app("documentation-agent", build_agent)
