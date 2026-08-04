export interface RootStatus {
  name: string
  version: string
  status: string
}

export interface HealthStatus {
  status: 'healthy'
  application: string
  version: string
  database: 'connected'
  environment: string
}

export interface SystemInfo {
  application: string
  version: string
  environment: string
  database_type: string
  local_first: boolean
  ai_integration:
    | 'ready'
    | 'unavailable'
    | 'model_not_configured'
    | 'model_not_installed'
  documentation: Record<string, string>
}

export type AIState =
  | 'ready'
  | 'unavailable'
  | 'model_not_configured'
  | 'model_not_installed'

export interface AIStatus {
  provider: 'ollama'
  available: boolean
  state: AIState
  version: string | null
  configured_model: string | null
  model_ready: boolean
  base_url: string
  error_code: string | null
  message: string
}

export interface AIModel {
  name: string
  modified_at: string | null
  size: number
  digest: string
  details: {
    family: string | null
    parameter_size: string | null
    quantization_level: string | null
    format: string | null
    context_length: number | null
  }
  is_configured: boolean
}
