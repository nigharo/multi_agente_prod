FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.10.10
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# APP_MODULE: multi_agent.orchestrator.api:app | multi_agent.verifier.api:app | multi_agent.rag.api:app
ENV APP_MODULE=multi_agent.orchestrator.api:app PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT"]
