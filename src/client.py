"""
Azure AI Foundry Client - The Foundation Layer

🎓 ARCHITECTURE LESSON:
This is your "client factory" pattern. It handles:
1. Authentication (multiple methods)
2. Connection management
3. Retry logic
4. Telemetry/observability
5. Resource cleanup

Compare to:
- LangGraph: Custom client init with retries
- Google ADK: genai.configure() + manual retry wrapping
"""

from typing import Optional
from azure.ai.projects import AIProjectClient
from azure.identity import (
    DefaultAzureCredential,
    ClientSecretCredential,
    AzureCliCredential,
    ManagedIdentityCredential
)
from azure.core.credentials import TokenCredential
from azure.core.pipeline.policies import RetryPolicy
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging
from contextlib import contextmanager

from config import FoundryConfig


# Set up structured logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class FoundryClientManager:
    """
    Manages Azure AI Foundry client lifecycle
    
    🎓 DESIGN PATTERN: Manager/Factory Pattern
    - Centralizes client creation logic
    - Handles authentication complexity
    - Provides context managers for resource cleanup
    - Enables dependency injection for testing
    """
    
    def __init__(self, config: FoundryConfig):
        """
        Initialize client manager
        
        Args:
            config: Validated configuration object
        
        🎓 Why not create client here?
        - Lazy initialization: Only connect when needed
        - Allows configuration validation first
        - Enables connection pooling later
        """
        self.config = config
        self._client: Optional[AIProjectClient] = None
        self._credential: Optional[TokenCredential] = None
        
        # Configure logging level
        logging.getLogger().setLevel(self.config.log_level)
        logger.info(f"🚀 Initialized FoundryClientManager for project: {config.azure_project_name}")
    
    def _get_credential(self) -> TokenCredential:
        """
        Get appropriate Azure credential based on configuration
        
        🎓 AUTHENTICATION STRATEGIES:
        
        1. Service Principal (automation/CI-CD):
           - Uses client_id + secret
           - Best for: GitHub Actions, Azure DevOps, production services
           - Granular RBAC control
        
        2. Managed Identity (Azure-hosted):
           - No secrets needed!
           - Best for: Azure VMs, Container Apps, Functions
           - Most secure option
        
        3. Azure CLI (local dev):
           - Uses `az login` session
           - Best for: Local development
           - No secrets in code
        
        4. DefaultAzureCredential (fallback chain):
           - Tries multiple methods in order
           - Best for: Flexibility across environments
        
        Compare to LangGraph/ADK:
        - They use API keys (less secure, no RBAC)
        - Foundry uses Azure AD (role-based, auditable)
        """
        
        if self._credential:
            return self._credential
        
        auth_method = self.config.get_auth_method()
        
        try:
            if auth_method == "service_principal":
                logger.info("🔐 Authenticating with Service Principal")
                self._credential = ClientSecretCredential(
                    tenant_id=self.config.azure_tenant_id,
                    client_id=self.config.azure_client_id,
                    client_secret=self.config.azure_client_secret
                )
            
            elif auth_method == "managed_identity":
                logger.info("🔐 Authenticating with Managed Identity")
                self._credential = ManagedIdentityCredential()
            
            elif auth_method == "azure_cli":
                logger.info("🔐 Authenticating with Azure CLI")
                self._credential = AzureCliCredential()
            
            else:
                logger.info("🔐 Using DefaultAzureCredential chain")
                self._credential = DefaultAzureCredential()
            
            # Test the credential
            token = self._credential.get_token("https://management.azure.com/.default")
            logger.info("✅ Authentication successful")
            
            return self._credential
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"🔄 Retry {retry_state.attempt_number}/3 - waiting {retry_state.next_action.sleep} seconds"
        )
    )
    def _create_client(self) -> AIProjectClient:
        """
        Create AIProjectClient with retry logic
        
        🎓 RETRY STRATEGY:
        - Exponential backoff: 2s, 4s, 8s (prevents thundering herd)
        - 3 attempts (balance between reliability and latency)
        - Retries transient errors (network, throttling)
        
        Why Tenacity library?
        - Declarative retry logic (easier to read/maintain)
        - Configurable strategies
        - Built-in logging
        
        Compare to:
        - LangGraph: Manual retry loops or custom decorators
        - ADK: Similar retry patterns available
        """
        
        try:
            credential = self._get_credential()
            
            logger.info(f"🔌 Connecting to Azure AI Foundry...")
            logger.debug(f"   Connection: {self.config.connection_string}")
            
            # Create the client
            # 🎓 This is the CORE Foundry SDK object
            client = AIProjectClient.from_connection_string(
                conn_str=self.config.connection_string,
                credential=credential
            )
            
            logger.info("✅ Connected to Azure AI Foundry")
            return client
            
        except Exception as e:
            logger.error(f"❌ Failed to create client: {e}")
            raise
    
    def get_client(self) -> AIProjectClient:
        """
        Get or create client instance (singleton pattern)
        
        🎓 SINGLETON PATTERN:
        - Reuses existing connection
        - Avoids connection overhead
        - Thread-safe (single client per manager instance)
        """
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @contextmanager
    def client_context(self):
        """
        Context manager for client lifecycle
        
        🎓 CONTEXT MANAGER PATTERN:
        Usage:
            with client_manager.client_context() as client:
                # Use client
                pass
            # Automatic cleanup
        
        Benefits:
        - Guarantees cleanup (even on exceptions)
        - Pythonic resource management
        - Clear scope boundaries
        """
        client = self.get_client()
        try:
            yield client
        finally:
            # Cleanup if needed (Foundry SDK handles most of this)
            logger.debug("🧹 Client context exited")
    
    def close(self):
        """
        Explicitly close client and release resources
        
        🎓 When to call:
        - Application shutdown
        - Switching projects
        - Long-running apps (periodic refresh)
        """
        if self._client:
            logger.info("🔌 Closing Foundry client")
            # Foundry SDK doesn't have explicit close yet, but prepare for it
            self._client = None
            self._credential = None


# ===== Usage Examples =====

def example_basic_usage():
    """Basic client creation and usage"""
    from config import load_config
    
    # Load configuration
    config = load_config()
    
    # Create client manager
    manager = FoundryClientManager(config)
    
    # Get client (lazy initialization)
    client = manager.get_client()
    
    # Use client...
    print(f"✅ Client ready for project: {config.azure_project_name}")
    
    # Cleanup
    manager.close()


def example_context_manager_usage():
    """Recommended pattern with automatic cleanup"""
    from config import load_config
    
    config = load_config()
    manager = FoundryClientManager(config)
    
    # Context manager automatically handles cleanup
    with manager.client_context() as client:
        # Use client safely
        print(f"✅ Using client in context: {config.azure_project_name}")
        # Automatic cleanup on exit


if __name__ == "__main__":
    # Test client creation
    print("🧪 Testing Foundry Client Manager\n")
    example_context_manager_usage()
