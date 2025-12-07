"""
Custom Agent Tools/Skills - Extending Agent Capabilities

🎓 CRITICAL CONCEPT: Tools vs Skills
- TOOL: A function the agent CAN call (the capability)
- SKILL: A tool + metadata for the orchestrator (how/when to use it)

In Foundry, you define tools as:
1. Python functions with type hints
2. OpenAPI/Swagger specifications
3. Azure Functions (for production scale)

Compare to:
- LangGraph: @tool decorator or BaseTool class
- Google ADK: FunctionDeclaration objects
- Foundry: Similar to both, with Azure-native deployment
"""

from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
import inspect
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ===== Tool Definition Models =====

class ToolParameter(BaseModel):
    """
    Schema for tool parameters
    
    🎓 This follows OpenAPI 3.0 spec - the standard for API documentation
    Foundry uses this to tell the LLM what parameters are available
    """
    name: str
    type: str  # string, integer, number, boolean, object, array
    description: str
    required: bool = True
    enum: Optional[List[str]] = None  # For restricted values
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """
    Complete tool/function definition
    
    🎓 This is what the LLM "sees" about your tool
    - name: How to call it
    - description: What it does (be specific! LLM uses this to decide when to call)
    - parameters: What inputs it needs
    """
    name: str
    description: str
    parameters: List[ToolParameter]
    
    def to_openapi_schema(self) -> Dict[str, Any]:
        """
        Convert to OpenAPI 3.0 function schema
        
        🎓 This format is what Foundry expects for tool registration
        It's also used by OpenAI function calling, so it's portable!
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


# ===== Tool Registry =====

class ToolRegistry:
    """
    Central registry for all agent tools
    
    🎓 PATTERN: Registry Pattern
    - Single source of truth for tools
    - Enables dynamic tool loading
    - Facilitates testing (mock tools)
    - Supports tool versioning
    """
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolDefinition] = {}
        logger.info("🔧 Initialized ToolRegistry")
    
    def register(
        self,
        func: Callable,
        description: str,
        parameters: Optional[List[ToolParameter]] = None
    ) -> Callable:
        """
        Register a function as an agent tool
        
        🎓 This is like LangGraph's @tool decorator but more explicit
        
        Args:
            func: Python function to register
            description: What the function does (be detailed!)
            parameters: Parameter definitions (auto-inferred if not provided)
        """
        name = func.__name__
        
        # Auto-infer parameters from function signature if not provided
        if parameters is None:
            parameters = self._infer_parameters(func)
        
        schema = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters
        )
        
        self._tools[name] = func
        self._schemas[name] = schema
        
        logger.info(f"✅ Registered tool: {name}")
        return func
    
    def _infer_parameters(self, func: Callable) -> List[ToolParameter]:
        """
        Infer parameters from function type hints
        
        🎓 This uses Python's inspect module to extract metadata
        Similar to how FastAPI auto-generates OpenAPI docs
        """
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            
            # Infer type from annotation
            param_type = "string"  # default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                required=param.default == inspect.Parameter.empty
            ))
        
        return parameters
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get tool function by name"""
        return self._tools.get(name)
    
    def get_schema(self, name: str) -> Optional[ToolDefinition]:
        """Get tool schema by name"""
        return self._schemas.get(name)
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tool schemas in OpenAPI format
        
        🎓 This is what you'll pass to the Foundry agent
        """
        return [schema.to_openapi_schema() for schema in self._schemas.values()]
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with given arguments
        
        🎓 This is called by the orchestrator when the agent decides to use a tool
        
        Args:
            name: Tool name
            arguments: Parsed arguments from agent
        
        Returns:
            Tool execution result
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        try:
            logger.info(f"🔧 Executing tool: {name} with args: {arguments}")
            result = tool(**arguments)
            logger.info(f"✅ Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"❌ Tool {name} failed: {e}")
            raise


# ===== Example Custom Tools =====

# Initialize global registry
tool_registry = ToolRegistry()


# Tool 1: Company Knowledge Base Query
@tool_registry.register(
    description="""
    Query the company's internal knowledge base for information about policies,
    procedures, products, or services. Use this when you need to access
    company-specific information that isn't publicly available.
    
    Returns relevant documents and their metadata.
    """,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="The search query (natural language)",
            required=True
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results to return",
            required=False,
            default=5
        )
    ]
)
def query_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    🎓 TEACHING POINT: RAG Pattern
    
    This is a placeholder for Retrieval-Augmented Generation (RAG).
    In production, this would:
    1. Query Azure AI Search or vector DB
    2. Return relevant documents
    3. Agent uses results to ground its response
    
    Compare to:
    - LangGraph: Custom retriever tool
    - ADK: Similar function calling pattern
    """
    # Simulated knowledge base response
    return {
        "query": query,
        "results": [
            {
                "title": "Company Policy: Remote Work",
                "content": "Remote work is permitted for all employees...",
                "relevance_score": 0.95,
                "source": "policies/remote-work.pdf"
            }
        ],
        "total_results": 1,
        "timestamp": datetime.now().isoformat()
    }


# Tool 2: Customer Data Lookup
@tool_registry.register(
    description="""
    Look up customer information from CRM system.
    Use this to get customer details, history, or status.
    
    ⚠️ SECURITY: Only returns non-sensitive data. Audit logged.
    """,
    parameters=[
        ToolParameter(
            name="customer_id",
            type="string",
            description="Unique customer identifier (email or ID)",
            required=True
        ),
        ToolParameter(
            name="include_history",
            type="boolean",
            description="Whether to include interaction history",
            required=False,
            default=False
        )
    ]
)
def lookup_customer(customer_id: str, include_history: bool = False) -> Dict[str, Any]:
    """
    🎓 TEACHING POINT: Data Governance
    
    Notice:
    - Audit logging mentioned in description (compliance)
    - Security warning in description (guides agent behavior)
    - Explicit about what data is/isn't returned
    
    In production:
    - Log access to audit trail
    - Apply row-level security
    - Mask sensitive fields (PII)
    """
    # Simulated CRM lookup
    return {
        "customer_id": customer_id,
        "name": "Acme Corporation",
        "status": "Active",
        "tier": "Enterprise",
        "account_manager": "Jane Smith",
        "history": [
            {"date": "2024-01-15", "type": "Support Ticket", "status": "Resolved"}
        ] if include_history else []
    }


# Tool 3: Create Support Ticket
@tool_registry.register(
    description="""
    Create a new support ticket in the ticketing system.
    Use this when a customer reports an issue that requires follow-up.
    
    Returns the ticket ID and tracking information.
    """,
    parameters=[
        ToolParameter(
            name="title",
            type="string",
            description="Brief summary of the issue",
            required=True
        ),
        ToolParameter(
            name="description",
            type="string",
            description="Detailed description of the issue",
            required=True
        ),
        ToolParameter(
            name="priority",
            type="string",
            description="Ticket priority level",
            required=False,
            enum=["low", "medium", "high", "critical"],
            default="medium"
        ),
        ToolParameter(
            name="customer_id",
            type="string",
            description="Associated customer ID",
            required=False
        )
    ]
)
def create_support_ticket(
    title: str,
    description: str,
    priority: str = "medium",
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    🎓 TEACHING POINT: Action Tools
    
    This tool CHANGES state in external systems.
    Best practices:
    - Idempotent when possible
    - Return confirmation data
    - Log for audit trail
    - Handle failures gracefully
    """
    # Simulated ticket creation
    ticket_id = f"TICK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "ticket_id": ticket_id,
        "status": "created",
        "priority": priority,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "url": f"https://support.example.com/tickets/{ticket_id}"
    }


# Tool 4: Calculate Cost Estimate
@tool_registry.register(
    description="""
    Calculate cost estimate for Azure resources based on configuration.
    Use this to provide pricing information to customers.
    """,
    parameters=[
        ToolParameter(
            name="resource_type",
            type="string",
            description="Type of Azure resource",
            required=True,
            enum=["vm", "storage", "sql", "app_service", "ai_service"]
        ),
        ToolParameter(
            name="tier",
            type="string",
            description="Service tier/SKU",
            required=True
        ),
        ToolParameter(
            name="hours_per_month",
            type="integer",
            description="Expected usage hours per month",
            required=False,
            default=730  # Full month
        )
    ]
)
def calculate_azure_cost(
    resource_type: str,
    tier: str,
    hours_per_month: int = 730
) -> Dict[str, Any]:
    """
    🎓 TEACHING POINT: Stateless Tools
    
    Pure functions make the best tools:
    - Deterministic output
    - Easy to test
    - No side effects
    - Cacheable
    """
    # Simulated pricing calculation
    base_rates = {
        "vm": {"basic": 0.05, "standard": 0.15, "premium": 0.50},
        "storage": {"basic": 0.01, "standard": 0.02, "premium": 0.05},
    }
    
    rate = base_rates.get(resource_type, {}).get(tier, 0.10)
    monthly_cost = rate * hours_per_month
    
    return {
        "resource_type": resource_type,
        "tier": tier,
        "hourly_rate": rate,
        "monthly_hours": hours_per_month,
        "estimated_monthly_cost": round(monthly_cost, 2),
        "currency": "USD"
    }


# ===== Export for Agent Use =====

def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all registered tools in Foundry-compatible format
    
    🎓 Call this when creating your agent to register all tools
    """
    return tool_registry.get_all_schemas()


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Execute a tool call from the agent
    
    🎓 This is your tool execution handler
    """
    return tool_registry.execute_tool(tool_name, arguments)


if __name__ == "__main__":
    # Test tool registry
    print("🔧 Registered Tools:\n")
    for schema in get_all_tools():
        print(f"  - {schema['function']['name']}")
        print(f"    {schema['function']['description'][:100]}...")
        print()
