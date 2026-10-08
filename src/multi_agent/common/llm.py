from langchain_deepseek import ChatDeepSeek
from langchain_openai import OpenAIEmbeddings

from multi_agent.common.config import get_settings


def get_llm() -> ChatDeepSeek:
    s = get_settings()
    return ChatDeepSeek(
        model=s.azure_openai_model,
        api_key=s.azure_openai_api_key,
        api_base=s.foundry_base_url,
        temperature=s.llm_temperature,
        max_retries=2,
    )


def get_embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(
        model=s.azure_openai_embedding_deployment,
        api_key=s.azure_openai_api_key,
        base_url=s.foundry_base_url,
        # Envía texto plano (no tokens de tiktoken): requerido fuera de api.openai.com
        check_embedding_ctx_length=False,
    )
