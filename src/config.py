"""
Configuration Management for Azure AI Foundry Agents

🎓 TEACHING POINTS:
1. Pydantic Settings for type-safe config (prevents runtime errors)
2. Multiple auth methods (DefaultAzureCredential for flexibility)
3. Validation at startup (fail fast if misconfigured)
4. Environment-based overrides (dev/staging/prod)
"""

from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class FoundryConfig(BaseSettings):
    """
    Configuration for Azure AI Foundry Agent
    
    🎓 Why Pydantic?
    - Type safety: Catches config errors at startup, not runtime
    - Validation: Ensures required fields exist
    - Documentation: Self-documenting configuration
    - IDE support: Autocomplete for config fields
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown env vars
    )
    
    # ===== Azure AI Project Configuration =====
    azure_subscription_id: str = Field(
        description="Azure subscription ID"
    )
    azure_resource_group: str = Field(
        description="Resource group containing AI project"
    )
    azure_project_name: str = Field(
        description="AI Foundry project name"
    )
    azure_endpoint: str = Field(
        description="AI Foundry API endpoint",
        pattern=r"^https://.*"  # Must be HTTPS
    )
    
    # ===== Authentication =====
    # 🎓 Multiple auth strategies for different deployment scenarios
    azure_tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD tenant ID (for service principal auth)"
    )
    azure_client_id: Optional[str] = Field(
        default=None,
        description="Service principal client ID"
    )
    azure_client_secret: Optional[str] = Field(
        default=None,
        description="Service principal secret (use Key Vault in prod!)"
    )
    
    # ===== Model Configuration =====
    azure_openai_deployment_name: str = Field(
        default="gpt-4o",
        description="OpenAI model deployment name"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version"
    )
    
    # ===== Observability =====
    applicationinsights_connection_string: Optional[str] = Field(
        default=None,
        description="Application Insights for telemetry"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity"
    )
    
    # ===== Governance & Security =====
    max_tokens_per_request: int = Field(
        default=4000,
        ge=1,
        le=128000,
        description="Maximum tokens per agent request"
    )
    enable_content_filtering: bool = Field(
        default=True,
        description="Enable Azure content safety filtering"
    )
    enable_audit_logging: bool = Field(
        default=True,
        description="Log all agent interactions for compliance"
    )
    max_conversation_history: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum messages to retain in thread"
    )
    
    # ===== Agent Behavior =====
    agent_timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=600,
        description="Maximum time for agent run completion"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retries for failed operations"
    )
    
    @field_validator("azure_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Ensure endpoint is properly formatted"""
        if not v.startswith("https://"):
            raise ValueError("Endpoint must use HTTPS")
        return v.rstrip("/")  # Remove trailing slash
    
    @field_validator("azure_client_secret")
    @classmethod
    def warn_plaintext_secret(cls, v: Optional[str]) -> Optional[str]:
        """
        🎓 SECURITY TEACHING POINT:
        In production, NEVER store secrets in .env files!
        Use Azure Key Vault or Managed Identity instead.
        """
        if v and not os.getenv("ALLOW_PLAINTEXT_SECRETS"):
            import warnings
            warnings.warn(
                "⚠️  Client secret in plaintext! Use Azure Key Vault in production.",
                UserWarning
            )
        return v
    
    @property
    def connection_string(self) -> str:
        """
        Generate connection string for AIProjectClient
        
        🎓 Format: endpoint;subscription;resource_group;project_name
        This is Foundry's primary connection method
        """
        return (
            f"{self.azure_endpoint};"
            f"{self.azure_subscription_id};"
            f"{self.azure_resource_group};"
            f"{self.azure_project_name}"
        )
    
    def get_auth_method(self) -> str:
        """
        Determine which authentication method to use
        
        🎓 Auth Priority:
        1. Service Principal (client_id + secret) - for automation
        2. Managed Identity - for Azure-hosted apps
        3. Azure CLI - for local development
        """
        if self.azure_client_id and self.azure_client_secret:
            return "service_principal"
        elif os.getenv("MSI_ENDPOINT"):  # Check if running in Azure
            return "managed_identity"
        else:
            return "azure_cli"


def load_config() -> FoundryConfig:
    """
    Load and validate configuration
    
    🎓 This function:
    1. Loads from .env file
    2. Validates all fields
    3. Fails fast if misconfigured
    4. Returns type-safe config object
    """
    try:
        config = FoundryConfig()
        print(f"✅ Configuration loaded successfully")
        print(f"   - Project: {config.azure_project_name}")
        print(f"   - Auth: {config.get_auth_method()}")
        print(f"   - Model: {config.azure_openai_deployment_name}")
        return config
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print(f"   Check your .env file against .env.template")
        raise


# Example usage
if __name__ == "__main__":
    config = load_config()
    print(f"\n📋 Connection String:\n{config.connection_string}")
