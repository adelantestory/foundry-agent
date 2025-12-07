# Azure AI Foundry Agent - Production Template

**🎓 A comprehensive learning resource and production template for building enterprise-grade AI agents with Azure AI Foundry.**

Built for MSPs and enterprises who need secure, observable, and governable agentic AI systems.

---

## 🏗️ Architecture Overview

### Component Structure

```
foundry-agent/
├── src/
│   ├── config.py          # Configuration management (Pydantic)
│   ├── client.py          # Foundry client with auth & retries
│   ├── tools.py           # Custom tool/skill definitions
│   ├── agent.py           # Core agent implementation
│   └── examples.py        # Learning examples
├── requirements.txt       # Python dependencies
├── .env.template          # Configuration template
└── README.md             # This file
```

### Key Design Patterns

1. **Configuration as Code**: Type-safe, validated configuration with Pydantic
2. **Factory Pattern**: Client manager handles connection lifecycle
3. **Registry Pattern**: Centralized tool management
4. **Context Manager**: Automatic resource cleanup
5. **Async/Await**: Non-blocking operations for scalability

<img width="400" height="814" alt="image" src="https://github.com/user-attachments/assets/0ba0f144-e644-49ab-af39-20d54a2340ae" />

---

## 📚 Learning Path

### Core Concepts (Read First)

**What is an Agent?**
- Not just a model - it's an autonomous system
- Has: Instructions, Tools, Memory, Orchestration
- Can: Plan, Execute, Learn, Adapt

**Foundry Architecture:**
```
Agent (business logic)
  ↓ uses
Orchestrator (planning/routing) ← Foundry manages this
  ↓ calls
Skills/Tools (capabilities) ← You define these
  ↓ powered by
Models (GPT-4, etc.) ← Azure OpenAI
  ↓ grounded in
Data (RAG, memory, indexes) ← Azure AI Search, etc.
```

### Component Deep Dives

#### 1. **AIProjectClient** (client.py)
- Your connection to Foundry
- Handles authentication (Service Principal, Managed Identity, CLI)
- Implements retry logic and connection pooling
- **Compare to**: LangGraph's custom client init

#### 2. **Agent** (agent.py)
- The autonomous entity with instructions and tools
- Persistent across conversations
- **Compare to**: LangGraph's CompiledGraph, ADK's Agent config

#### 3. **Thread** (agent.py - ConversationContext)
- Isolated conversation context
- Maintains message history
- **Compare to**: LangGraph's thread/state, ADK's session

#### 4. **Run** (agent.py - run method)
- Single execution instance
- Orchestrates: Message → Reasoning → Tool Calls → Response
- **Compare to**: LangGraph's invoke(), ADK's generate_content()

#### 5. **Tools/Skills** (tools.py)
- Functions the agent can call
- Defined via OpenAPI schemas
- **Compare to**: LangGraph's @tool, ADK's FunctionDeclaration

---

## 🔄 Platform Comparison

### Microsoft Foundry vs LangGraph vs Google ADK

| Feature | Foundry | LangGraph | Google ADK |
|---------|---------|-----------|------------|
| **Deployment** | Azure-managed | Self-hosted | Google-managed |
| **Orchestration** | Built-in | Custom graphs | Built-in |
| **Tools** | OpenAPI specs | Python functions | Function declarations |
| **Auth** | Azure AD/RBAC | API keys | Google Auth |
| **State Management** | Automatic | Checkpointers | Session state |
| **Observability** | Azure Monitor | Custom logging | Cloud Monitoring |
| **Multi-agent** | Native swarms | Subgraphs | Multi-agent systems |
| **Vendor Lock-in** | Medium | Low | Medium |

### When to Choose Each

**Choose Foundry if:**
- Already on Azure
- Need enterprise security/compliance
- Want managed infrastructure
- Require Azure service integration

**Choose LangGraph if:**
- Need maximum control
- Want vendor independence
- Require complex state graphs
- Self-hosting is acceptable

**Choose Google ADK if:**
- Using Google Cloud
- Need Google service integration
- Want managed simplicity
- Vertex AI is your platform

---

## 🚀 Quick Start

### Prerequisites

1. **Azure Subscription** with AI Foundry enabled
2. **Azure AI Studio Project** created
3. **Model Deployment** (GPT-4 or GPT-4o recommended)
4. **Python 3.9+**

### Setup

1. **Clone/Copy the project structure**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.template .env
# Edit .env with your Azure details
```

4. **Required environment variables:**
```bash
# From Azure AI Studio → Project Settings
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=<your-resource-group>
AZURE_PROJECT_NAME=<your-project-name>
AZURE_ENDPOINT=https://<your-project>.api.azureml.ms

# Model deployment name (from Azure AI Studio → Deployments)
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Run Examples

```bash
# Run all learning examples
python src/examples.py

# Run specific example
python src/examples.py 1  # Basic conversation
python src/examples.py 2  # Tool usage
python src/examples.py 6  # Production pattern
```

---

## 🔧 Extending the Agent

### Adding Custom Tools

1. **Define your function in tools.py:**
```python
@tool_registry.register(
    description="What your tool does (be specific!)",
    parameters=[
        ToolParameter(
            name="input_param",
            type="string",
            description="What this parameter is for",
            required=True
        )
    ]
)
def my_custom_tool(input_param: str) -> Dict[str, Any]:
    # Your logic here
    return {"result": "success"}
```

2. **The agent automatically gets the tool** - no code changes needed!

### Tool Design Best Practices

1. **Clear descriptions**: The LLM uses these to decide when to call
2. **Type hints**: Enable validation and better UX
3. **Idempotent when possible**: Same input → same output
4. **Error handling**: Return errors, don't raise (let agent handle)
5. **Logging**: Always log for audit/debugging

---

## 🔒 Security & Governance

### Authentication Options (Priority Order)

1. **Managed Identity** (Production - most secure)
   - No secrets needed
   - Automatic credential rotation
   - Works in Azure VMs, Container Apps, Functions

2. **Service Principal** (CI/CD & Automation)
   - Granular RBAC control
   - Store secrets in Azure Key Vault
   - Use for GitHub Actions, Azure DevOps

3. **Azure CLI** (Local Development)
   - Use your `az login` session
   - No secrets in code
   - Perfect for dev/testing

### Content Filtering

Foundry includes Azure Content Safety:
- **Enabled by default** in this template
- Filters: Hate, sexual, violence, self-harm
- Configurable severity levels
- See config.py: `enable_content_filtering`

### Audit Logging

Every agent interaction is logged:
- Who (user/system)
- What (query + response)
- When (timestamp)
- Why (tool calls + reasoning)

Configure in config.py: `enable_audit_logging`

### Data Privacy

- Never log sensitive data (PII, credentials)
- Use Azure Key Vault for secrets
- Implement row-level security in tools
- Follow GDPR/compliance requirements

---

## 📊 Observability

### Built-in Metrics

The agent tracks:
- Total runs
- Success rate
- Average response time
- Token usage
- Tool call frequency

Access via: `agent.get_metrics()`

### Application Insights Integration

Set in .env:
```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=<your-connection-string>
```

Tracks:
- Request telemetry
- Dependency calls
- Exceptions
- Custom events

### Monitoring Queries (Log Analytics)

```kusto
// Failed agent runs
AgentRuns
| where Status == "failed"
| summarize count() by ErrorType

// Average response time by tool
AgentRuns
| summarize avg(Duration) by ToolUsed

// Token usage over time
AgentRuns
| summarize sum(TokensUsed) by bin(Timestamp, 1h)
```

---

## 🏭 Production Deployment

### Option 1: Azure Container Apps

```bash
# Build container
docker build -t foundry-agent:latest .

# Deploy to Container Apps
az containerapp create \
  --name foundry-agent \
  --resource-group $RG \
  --image foundry-agent:latest \
  --environment $ENV \
  --managed-identity system
```

### Option 2: Azure Functions

- Best for event-driven agents
- Serverless scaling
- Consumption or Premium plan

### Option 3: AKS (Kubernetes)

- Full control
- Multi-tenant isolation
- Advanced networking

### Scaling Considerations

- **Single Agent Instance**: Handles ~100 concurrent threads
- **Multiple Instances**: Use agent ID for routing
- **Thread Management**: Clean up old threads periodically
- **Rate Limiting**: Implement per-customer quotas

---

## 🧪 Testing Strategy

### Unit Tests
- Test individual tools
- Mock AIProjectClient
- Validate tool schemas

### Integration Tests
- Test agent creation
- Test thread management
- Test tool orchestration

### End-to-End Tests
- Full conversation flows
- Multi-turn scenarios
- Error recovery paths

---

## 💰 Cost Optimization

### Token Usage Tips

1. **Shorter instructions**: Be concise but clear
2. **Truncate history**: Don't send full conversation history every time
3. **Efficient tools**: Return only necessary data
4. **Caching**: Cache tool results when possible

### Model Selection

- **GPT-4o**: Best for complex reasoning, tool use
- **GPT-4o-mini**: Cost-effective for simple queries
- **Mix models**: Route by complexity

### Monitoring Costs

```python
# Track costs in metrics
cost_per_1k_tokens = 0.01  # Update with actual rates
total_cost = (metrics['total_tokens'] / 1000) * cost_per_1k_tokens
```

---

## 🐛 Troubleshooting

### Common Issues

**"Authentication failed"**
- Check Azure credentials
- Verify RBAC permissions (Cognitive Services User role)
- Ensure project exists

**"Tool not found"**
- Verify tool registration
- Check tool name spelling
- Ensure tools.py is imported

**"Run timeout"**
- Increase `agent_timeout_seconds` in config
- Check tool execution time
- Review model performance

**"Token limit exceeded"**
- Reduce `max_tokens_per_request`
- Truncate conversation history
- Simplify tool responses

---

## 📖 Learning Resources

### Foundry Documentation
- [Azure AI Foundry Docs](https://learn.microsoft.com/azure/ai-studio/)
- [Agent SDK Reference](https://learn.microsoft.com/python/api/azure-ai-projects/)

### Comparison Platforms
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Google ADK Documentation](https://ai.google.dev/adk)

### Best Practices
- [Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Azure AI Best Practices](https://learn.microsoft.com/azure/ai-services/responsible-use-of-ai-overview)

---

## 🤝 Contributing

This template is designed for learning and production use. Feedback welcome!

### Areas for Enhancement
- Streaming responses
- Advanced RAG integration
- Multi-agent orchestration
- Custom evaluation metrics

---

## 📄 License

MIT License - Use freely for commercial and educational purposes.

---

## 🎓 Next Steps

1. **Run the examples** - Understand each capability
2. **Customize tools** - Add your business logic
3. **Deploy to Azure** - Production-ready template
4. **Monitor & optimize** - Track metrics, reduce costs
5. **Explore advanced features** - Multi-agent, RAG, etc.

---

**Built by Danny @ Delante Solutions**  
*Microsoft AI Cloud Partner - Empowering MSPs with Agentic AI*
