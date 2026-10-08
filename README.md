# Orquestador multi-agente de Onboarding Digital (LangChain + Azure OpenAI)

Basado en `DIAGRAMA_SOLUCION.png` e `instructs.txt`.

```
Cliente ─► API Orquestador :8000   POST /api/v1/onboarding/start · /health
             └─ Agente Orquestador (create_agent, estado OnboardingState por session_id)
                  ├─ HTTP ─► Agente Verificador :8001   verify_identity (Tool 1), check_risk_lists (Tool 2)
                  └─ HTTP ─► Agente Documentación (RAG) :8002   search_policies, prepare_documentation (Tool 3)
                                         └─► Qdrant :6333 (embeddings text-embedding-3-small)
```

## Estructura
```
src/multi_agent/
  common/        config (.env), LLM/embeddings Azure, esquemas, umbrales de política,
                 fábrica de la API de sub-agentes (/health, /invoke)
  orchestrator/  api.py, agent.py, state.py (estado), tools.py (delegación HTTP)
  verifier/      api.py, agent.py, tools.py (mocks Tool 1 y Tool 2)
  rag/           api.py, agent.py, tools.py (RAG + mock Tool 3), vectorstore.py, ingest.py
docker/Dockerfile   imagen única; el servicio se elige con APP_MODULE
docker-compose.yml  orchestrator, verifier-agent, rag-agent, qdrant
data/docs/          políticas del banco a indexar (pdf, md, txt)
tests/              tools y flujo end-to-end con LLM falso
```

## Diseño
- **Control de herramientas por agente**: cada sub-agente solo tiene sus tools y corre en su
  propio contenedor; el orquestador solo puede delegar (no accede a las tools directamente).
- **Estado**: `OnboardingState` (prospecto, identidad, riesgo, documentación, errores) se
  actualiza desde las tools con `Command(update=...)` y se persiste con un checkpointer por
  `session_id` (`InMemorySaver`; cambiar a Postgres/Redis para varias réplicas).
- **Incertidumbre**: el orquestador decide (structured output `OnboardingDecision`) según las
  reglas de su prompt: confianza < 0.8, riesgo high o agente caído ⇒ `requiere_escalamiento`
  con `proposed_solution`.

## Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Salud del servicio |
| POST | `/api/v1/onboarding/start` | Inicia onboarding `{"prospect_name","document_id","product"}` |
| POST | `/api/v1/onboarding/{session_id}/message` | Seguimiento conversacional de la sesión |
| GET | `/api/v1/onboarding/{session_id}` | Estado de la sesión |

Escenarios mock: `1712345678` apto · `0912345670` confianza 0.62 (escalamiento) ·
`1700000000` identidad no coincide · `1799999999` o nombre "Carlos Riesgo Alto" riesgo high ·
`1788888888` PEP riesgo medio.

## Uso
```bash
cp .env.example .env            # completar credenciales y deployments de Azure OpenAI
BUILDX_BUILDER=default docker compose up -d --build   # ver nota de DNS abajo
docker compose exec rag-agent rag-ingest data/docs   # indexar políticas en Qdrant
curl -X POST localhost:8000/api/v1/onboarding/start -H 'content-type: application/json' \
  -d '{"prospect_name": "Juan Perez", "document_id": "1712345678", "product": "cuenta_ahorros"}'
```

Local sin Docker: `docker compose up -d qdrant`, `uv run rag-ingest`, y en terminales separadas
`uv run uvicorn multi_agent.verifier.api:app --port 8001`,
`uv run uvicorn multi_agent.rag.api:app --port 8002`,
`uv run uvicorn multi_agent.orchestrator.api:app --port 8000`.

Tests: `uv run pytest`

## Nota de build (DNS)
El builder `secure-builder` (docker-container) tiene congelado el DNS `192.168.0.1` de otra red
y no resuelve registros. Usa `BUILDX_BUILDER=default` o recréalo:
`docker buildx rm secure-builder && docker buildx create --name secure-builder --use`.

## Despliegue en Azure (Terraform, autoescalamiento)
`infra/main.tf` crea Azure Container Apps (un app por agente), ACR, Log Analytics y Qdrant.
Cada agente escala según las peticiones HTTP concurrentes (`var.scaling`: 1–10 réplicas).
Los sub-agentes y Qdrant solo tienen ingress interno; únicamente el orquestador es público.

```bash
cd infra && cp terraform.tfvars.example terraform.tfvars   # completar
terraform init
terraform apply -target=azurerm_container_registry.acr      # 1) crear el registro
az acr build -r acr<prefix> -t multi-agent:<image_tag> -f docker/Dockerfile ..   # 2) imagen
terraform apply                                             # 3) apps
az containerapp exec -g rg-<prefix> -n rag-agent --command "rag-ingest data/docs"  # 4) indexar
```

- El orquestador queda en 1 réplica: las sesiones viven en memoria (`InMemorySaver`). Para
  escalarlo, migrar a `langgraph-checkpoint-postgres` y subir `max_replicas`.
- Qdrant en Container Apps (Azure Files, 1 réplica) es para dev/QA; en producción usar
  Qdrant Cloud con `qdrant_external_url` / `qdrant_api_key`.
