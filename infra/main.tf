# Despliegue en Azure Container Apps con autoescalamiento por agente.
#
#   Internet ─► orchestrator (ingress externo)  ── escala por peticiones HTTP concurrentes
#                  ├─► verifier-agent (interno) ── escala por peticiones HTTP concurrentes
#                  └─► rag-agent      (interno) ── escala por peticiones HTTP concurrentes
#                          └─► qdrant (interno, 1 réplica, Azure Files) o Qdrant Cloud
#
# Despliegue en dos fases (las imágenes deben existir en ACR antes de crear las apps):
#   terraform init
#   terraform apply -target=azurerm_container_registry.acr -var-file=terraform.tfvars
#   az acr build -r <acr_name> -t multi-agent:<image_tag> -f docker/Dockerfile .
#   terraform apply -var-file=terraform.tfvars

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ---------------------------------------------------------------- Variables

variable "subscription_id" {
  type = string
}

variable "prefix" {
  description = "Prefijo de recursos (minúsculas, sin guiones; se usa en el nombre del ACR)."
  type        = string
  default     = "onbagents"
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "azure_openai_endpoint" {
  description = "Endpoint de Azure AI Foundry (…/openai/v1)."
  type        = string
}

variable "azure_openai_api_key" {
  type      = string
  sensitive = true
}

variable "azure_openai_model" {
  type    = string
  default = "DeepSeek-V4-Flash"
}

variable "azure_openai_embedding_deployment" {
  type    = string
  default = "text-embedding-3-small"
}

variable "qdrant_external_url" {
  description = "URL de Qdrant Cloud (recomendado en producción). Vacío = desplegar Qdrant en Container Apps."
  type        = string
  default     = ""
}

variable "qdrant_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "scaling" {
  description = "Réplicas y peticiones concurrentes por réplica que disparan el escalado."
  type = map(object({
    min_replicas        = number
    max_replicas        = number
    concurrent_requests = number
    cpu                 = number
    memory              = string
  }))
  default = {
    # El orquestador guarda las sesiones en memoria (InMemorySaver): con max_replicas > 1
    # los endpoints de seguimiento pueden caer en otra réplica. Antes de subirlo, migrar a
    # un checkpointer persistente (langgraph-checkpoint-postgres).
    orchestrator   = { min_replicas = 1, max_replicas = 1, concurrent_requests = 20, cpu = 0.5, memory = "1Gi" }
    verifier-agent = { min_replicas = 1, max_replicas = 10, concurrent_requests = 10, cpu = 0.5, memory = "1Gi" }
    rag-agent      = { min_replicas = 1, max_replicas = 10, concurrent_requests = 10, cpu = 0.5, memory = "1Gi" }
  }
}

locals {
  deploy_qdrant = var.qdrant_external_url == ""
  qdrant_url    = local.deploy_qdrant ? "https://${azurerm_container_app.qdrant[0].ingress[0].fqdn}:443" : var.qdrant_external_url
  image         = "${azurerm_container_registry.acr.login_server}/multi-agent:${var.image_tag}"

  common_env = {
    AZURE_OPENAI_ENDPOINT             = var.azure_openai_endpoint
    AZURE_OPENAI_MODEL                = var.azure_openai_model
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = var.azure_openai_embedding_deployment
  }

  agents = {
    verifier-agent = {
      module = "multi_agent.verifier.api:app"
      env    = {}
    }
    rag-agent = {
      module = "multi_agent.rag.api:app"
      env    = { QDRANT_URL = local.qdrant_url }
    }
  }
}

# ---------------------------------------------------------------- Base

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}"
  location = var.location
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${var.prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_registry" "acr" {
  name                = "acr${var.prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_user_assigned_identity" "apps" {
  name                = "id-${var.prefix}-apps"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${var.prefix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

# ---------------------------------------------------------------- Qdrant (opcional)
# Qdrant desaconseja almacenamiento en red (SMB) en producción: usar Qdrant Cloud vía
# qdrant_external_url. Esta opción sirve para desarrollo/QA. No escala (1 réplica).

resource "azurerm_storage_account" "qdrant" {
  count                    = local.deploy_qdrant ? 1 : 0
  name                     = "st${var.prefix}qdrant"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_share" "qdrant" {
  count              = local.deploy_qdrant ? 1 : 0
  name               = "qdrant-storage"
  storage_account_id = azurerm_storage_account.qdrant[0].id
  quota              = 50
}

resource "azurerm_container_app_environment_storage" "qdrant" {
  count                        = local.deploy_qdrant ? 1 : 0
  name                         = "qdrant-storage"
  container_app_environment_id = azurerm_container_app_environment.env.id
  account_name                 = azurerm_storage_account.qdrant[0].name
  share_name                   = azurerm_storage_share.qdrant[0].name
  access_key                   = azurerm_storage_account.qdrant[0].primary_access_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_container_app" "qdrant" {
  count                        = local.deploy_qdrant ? 1 : 0
  name                         = "qdrant"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "qdrant"
      image  = "docker.io/qdrant/qdrant:latest"
      cpu    = 1
      memory = "2Gi"

      volume_mounts {
        name = "qdrant-storage"
        path = "/qdrant/storage"
      }
    }

    volume {
      name         = "qdrant-storage"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.qdrant[0].name
    }
  }

  ingress {
    external_enabled = false
    target_port      = 6333
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# ---------------------------------------------------------------- Agentes especializados

resource "azurerm_container_app" "agent" {
  for_each                     = local.agents
  name                         = each.key
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  depends_on                   = [azurerm_role_assignment.acr_pull]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  secret {
    name  = "qdrant-api-key"
    value = var.qdrant_api_key == "" ? "none" : var.qdrant_api_key
  }

  template {
    min_replicas = var.scaling[each.key].min_replicas
    max_replicas = var.scaling[each.key].max_replicas

    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = tostring(var.scaling[each.key].concurrent_requests)
    }

    container {
      name   = each.key
      image  = local.image
      cpu    = var.scaling[each.key].cpu
      memory = var.scaling[each.key].memory

      env {
        name  = "APP_MODULE"
        value = each.value.module
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      dynamic "env" {
        for_each = var.qdrant_api_key == "" ? {} : { QDRANT_API_KEY = "qdrant-api-key" }
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      dynamic "env" {
        for_each = merge(local.common_env, each.value.env)
        content {
          name  = env.key
          value = env.value
        }
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# ---------------------------------------------------------------- Orquestador (API pública)

resource "azurerm_container_app" "orchestrator" {
  name                         = "orchestrator"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  depends_on                   = [azurerm_role_assignment.acr_pull]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  template {
    min_replicas = var.scaling["orchestrator"].min_replicas
    max_replicas = var.scaling["orchestrator"].max_replicas

    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = tostring(var.scaling["orchestrator"].concurrent_requests)
    }

    container {
      name   = "orchestrator"
      image  = local.image
      cpu    = var.scaling["orchestrator"].cpu
      memory = var.scaling["orchestrator"].memory

      env {
        name  = "APP_MODULE"
        value = "multi_agent.orchestrator.api:app"
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      env {
        name  = "VERIFIER_AGENT_URL"
        value = "https://${azurerm_container_app.agent["verifier-agent"].ingress[0].fqdn}"
      }

      env {
        name  = "RAG_AGENT_URL"
        value = "https://${azurerm_container_app.agent["rag-agent"].ingress[0].fqdn}"
      }

      dynamic "env" {
        for_each = local.common_env
        content {
          name  = env.key
          value = env.value
        }
      }

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }

      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# ---------------------------------------------------------------- Outputs

output "orchestrator_url" {
  value = "https://${azurerm_container_app.orchestrator.ingress[0].fqdn}"
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "qdrant_url" {
  value = local.qdrant_url
}
