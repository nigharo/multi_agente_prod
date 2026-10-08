from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure AI Foundry (endpoint OpenAI-compatible /openai/v1)
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_model: str = "DeepSeek-V4-Flash"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    llm_temperature: float = 0.0

    @property
    def foundry_base_url(self) -> str:
        """Normaliza el endpoint a https://<recurso>.services.ai.azure.com/openai/v1."""
        url = self.azure_openai_endpoint.rstrip("/").removesuffix("/chat/completions")
        url = url.removesuffix("/embeddings")
        return url if url.endswith("/openai/v1") else f"{url}/openai/v1"

    # Vector DB (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "documentacion"
    embedding_dimensions: int = 1536  # text-embedding-3-small

    # URLs de los agentes especializados (vistas desde el orquestador)
    verifier_agent_url: str = "http://localhost:8001"
    rag_agent_url: str = "http://localhost:8002"
    agent_timeout_seconds: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
