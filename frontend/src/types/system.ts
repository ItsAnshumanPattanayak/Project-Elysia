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
  ai_integration: 'not_configured'
  documentation: Record<string, string>
}
