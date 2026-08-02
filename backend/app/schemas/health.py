from pydantic import BaseModel


class RootResponse(BaseModel):
    name: str
    version: str
    status: str


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str
    database: str
    environment: str


class SystemInfoResponse(BaseModel):
    application: str
    version: str
    environment: str
    database_type: str
    local_first: bool
    ai_integration: str
    documentation: dict[str, str]
