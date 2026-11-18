
from enum import Enum
from pydantic import BaseModel, Field


class ProviderStatus(str, Enum):
    PLANNED = "planned"
    AVAILABLE = "available"
    LIMITED = "limited"
    DISABLED = "disabled"


class IntegrationMode(str, Enum):
    API = "api"
    EXTERNAL_WORKSPACE = "external_workspace"
    UNDETERMINED = "undetermined"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    NOT_AVAILABLE = "not_available"


class AgePolicyStatus(str, Enum):
    APPROVED = "approved"
    REQUIRES_GUARDIAN = "requires_guardian"
    RESTRICTED = "restricted"
    NOT_REVIEWED = "not_reviewed"


class ProviderModel(BaseModel):
    id: str
    name: str
    description: str = ""


class ProviderCapability(BaseModel):
    id: str
    name: str
    description: str = ""


class ProviderInfo(BaseModel):
    id: str
    name: str
    company: str

    status: ProviderStatus = ProviderStatus.PLANNED
    enabled: bool = False

    integration_mode: IntegrationMode = IntegrationMode.UNDETERMINED

    api_status: VerificationStatus = VerificationStatus.NOT_VERIFIED
    age_policy_status: AgePolicyStatus = AgePolicyStatus.NOT_REVIEWED
    region_status: VerificationStatus = VerificationStatus.NOT_VERIFIED

    models: list[ProviderModel] = Field(default_factory=list)
    capabilities: list[ProviderCapability] = Field(default_factory=list)
