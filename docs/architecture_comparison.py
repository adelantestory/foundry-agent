"""
Platform Architecture Deep Dive: Foundry vs LangGraph vs Google ADK

🎓 TEACHING GOAL:
Understand the fundamental architectural differences between platforms
so you can make informed decisions and translate concepts across them.

This is your "Rosetta Stone" for agentic AI platforms.
"""

# ============================================================================
# CONCEPTUAL MAPPING
# ============================================================================

CONCEPTUAL_MAP = {
    "AGENT_DEFINITION": {
        "Foundry": {
            "concept": "Agent",
            "created_via": "client.agents.create_agent()",
            "persisted": True,
            "reusable": True,
            "code_example": """
                agent = await client.agents.create_agent(
                    model="gpt-4o",
                    name="my-agent",
                    instructions="You are a helpful assistant",
                    tools=[...]
                )
            """
        },
        "LangGraph": {
            "concept": "CompiledGraph",
            "created_via": "graph.compile()",
            "persisted": False,  # Unless checkpointed
            "reusable": True,
            "code_example": """
                from langgraph.graph import StateGraph
                
                graph = StateGraph(AgentState)
                graph.add_node("agent", agent_node)
                graph.add_edge(START, "agent")
                compiled = graph.compile()
            """
        },
        "Google ADK": {
            "concept": "Agent Config",
            "created_via": "Agent() constructor",
            "persisted": False,
            "reusable": True,
            "code_example": """
                from google.genai import Agent
                
                agent = Agent(
                    model="gemini-2.0-flash",
                    name="my-agent",
                    instructions="You are a helpful assistant",
                    functions=[...]
                )
            """
        },
        "key_difference": """
            - Foundry: Server-side entity (persistent, Azure-managed)
            - LangGraph: Client-side graph (you manage state)
            - ADK: Client-side config (Google-managed execution)
        """
    },
    
    "CONVERSATION_CONTEXT": {
        "Foundry": {
            "concept": "Thread",
            "scope": "Per conversation/session",
            "persistence": "Azure-managed",
            "code_example": """
                thread = await client.agents.create_thread()
                # Thread persists until deleted
            """
        },
        "LangGraph": {
            "concept": "Thread (with checkpointer)",
            "scope": "Per conversation/session",
            "persistence": "Your checkpointer (Memory, Redis, Postgres)",
            "code_example": """
                from langgraph.checkpoint.memory import MemorySaver
                
                checkpointer = MemorySaver()
                graph = graph.compile(checkpointer=checkpointer)
                
                result = graph.invoke(
                    input_data,
                    config={"configurable": {"thread_id": "conv-123"}}
                )
            """
        },
        "Google ADK": {
            "concept": "Session",
            "scope": "Per conversation",
            "persistence": "Google-managed",
            "code_example": """
                session = agent.start_session()
                # Session handles state automatically
            """
        },
        "key_difference": """
            - Foundry: Threads are first-class Azure resources
            - LangGraph: Threads via checkpointer (you control storage)
            - ADK: Sessions are implicit, Google-managed
        """
    },
    
    "EXECUTION_UNIT": {
        "Foundry": {
            "concept": "Run",
            "lifecycle": "queued → in_progress → [requires_action] → completed",
            "blocking": "Async with polling",
            "code_example": """
                run = await client.agents.create_run(
                    thread_id=thread.id,
                    agent_id=agent.id
                )
                
                # Poll until complete
                while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS]:
                    run = await client.agents.get_run(thread.id, run.id)
                    await asyncio.sleep(1)
            """
        },
        "LangGraph": {
            "concept": "Invocation",
            "lifecycle": "Single pass through graph",
            "blocking": "Sync or async",
            "code_example": """
                # Synchronous
                result = graph.invoke(input_data, config)
                
                # Asynchronous
                result = await graph.ainvoke(input_data, config)
                
                # Streaming
                async for chunk in graph.astream(input_data, config):
                    print(chunk)
            """
        },
        "Google ADK": {
            "concept": "Turn/Generate",
            "lifecycle": "Request → response (single turn)",
            "blocking": "Sync or async",
            "code_example": """
                response = agent.generate_content("Your query")
                
                # Or with session
                response = session.send_message("Your query")
            """
        },
        "key_difference": """
            - Foundry: Run is a server-side job (async by nature)
            - LangGraph: Invocation is code execution (sync or async)
            - ADK: Generate is API call (sync or async)
        """
    },
    
    "TOOL_DEFINITION": {
        "Foundry": {
            "format": "OpenAPI 3.0 function schema",
            "registration": "During agent creation",
            "execution": "SDK calls your function",
            "code_example": """
                tools = [{
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City name"
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }]
                
                agent = await client.agents.create_agent(tools=tools)
            """
        },
        "LangGraph": {
            "format": "Python function with @tool decorator",
            "registration": "Added to agent node",
            "execution": "Direct function call",
            "code_example": """
                from langchain_core.tools import tool
                
                @tool
                def get_weather(location: str) -> str:
                    '''Get current weather for a location.'''
                    return f"Weather in {location}: Sunny"
                
                # Bind to LLM
                model_with_tools = model.bind_tools([get_weather])
            """
        },
        "Google ADK": {
            "format": "FunctionDeclaration",
            "registration": "In agent config",
            "execution": "Your callback function",
            "code_example": """
                from google.genai.types import FunctionDeclaration
                
                get_weather = FunctionDeclaration(
                    name="get_weather",
                    description="Get current weather",
                    parameters={
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                )
                
                agent = Agent(functions=[get_weather])
            """
        },
        "key_difference": """
            - Foundry: Tools via OpenAPI (portable, Azure-native)
            - LangGraph: Tools as Python functions (most flexible)
            - ADK: Tools via declarations (Google format)
        """
    },
    
    "ORCHESTRATION": {
        "Foundry": {
            "approach": "Built-in autonomous orchestrator",
            "control": "Limited (via instructions)",
            "flow": "Agent decides via LLM reasoning",
            "code_example": """
                # Orchestration is implicit in instructions
                agent = await client.agents.create_agent(
                    instructions='''
                    When user asks for weather:
                    1. Use get_weather tool
                    2. Format response nicely
                    3. Ask if they need anything else
                    '''
                )
            """
        },
        "LangGraph": {
            "approach": "Explicit state graph",
            "control": "Full control",
            "flow": "You define edges/conditional routing",
            "code_example": """
                from langgraph.graph import StateGraph
                
                graph = StateGraph(AgentState)
                graph.add_node("agent", agent_node)
                graph.add_node("tools", tool_node)
                
                # Conditional routing
                graph.add_conditional_edges(
                    "agent",
                    should_continue,
                    {"continue": "tools", "end": END}
                )
                
                graph.add_edge("tools", "agent")
            """
        },
        "Google ADK": {
            "approach": "Built-in orchestration",
            "control": "Limited (via instructions)",
            "flow": "Agent decides via LLM reasoning",
            "code_example": """
                # Orchestration via instructions
                agent = Agent(
                    instructions="Use tools when needed",
                    functions=[...]
                )
                
                # Automatic tool calling
                response = agent.generate_content("Query")
            """
        },
        "key_difference": """
            - Foundry: Black-box orchestrator (trust Azure)
            - LangGraph: White-box orchestrator (you control)
            - ADK: Black-box orchestrator (trust Google)
            
            Trade-off: Control vs Convenience
        """
    },
    
    "MULTI_AGENT": {
        "Foundry": {
            "pattern": "Agent Swarms",
            "coordination": "Handoffs via orchestrator",
            "code_example": """
                # Define handoff conditions
                sales_agent = await client.agents.create_agent(
                    name="sales-agent",
                    handoff_agents=["support-agent"]
                )
                
                support_agent = await client.agents.create_agent(
                    name="support-agent"
                )
                
                # Orchestrator routes between agents
            """
        },
        "LangGraph": {
            "pattern": "Subgraphs or supervisor pattern",
            "coordination": "Explicit routing in graph",
            "code_example": """
                # Supervisor pattern
                graph.add_node("supervisor", supervisor_node)
                graph.add_node("sales_agent", sales_node)
                graph.add_node("support_agent", support_node)
                
                graph.add_conditional_edges(
                    "supervisor",
                    route_to_agent,
                    {
                        "sales": "sales_agent",
                        "support": "support_agent"
                    }
                )
            """
        },
        "Google ADK": {
            "pattern": "Multi-agent systems",
            "coordination": "Agent delegation",
            "code_example": """
                # Create specialized agents
                sales_agent = Agent(name="sales")
                support_agent = Agent(name="support")
                
                # Coordinator agent delegates
                coordinator = Agent(
                    functions=[delegate_to_sales, delegate_to_support]
                )
            """
        },
        "key_difference": """
            - Foundry: Native agent swarms (Azure-managed)
            - LangGraph: Custom graph topology (full flexibility)
            - ADK: Agent delegation (Google-managed)
        """
    },
    
    "STATE_MANAGEMENT": {
        "Foundry": {
            "approach": "Automatic (thread history)",
            "storage": "Azure-managed",
            "access": "Via thread messages",
            "code_example": """
                # State is implicit in thread messages
                messages = await client.agents.list_messages(thread_id)
                
                # Add context
                await client.agents.create_message(
                    thread_id=thread_id,
                    role="user",
                    content="Remember this: user prefers JSON"
                )
            """
        },
        "LangGraph": {
            "approach": "Explicit state object",
            "storage": "Your checkpointer",
            "access": "Via state dictionary",
            "code_example": """
                from typing import TypedDict
                
                class AgentState(TypedDict):
                    messages: list
                    user_preferences: dict
                    context: str
                
                # State flows through graph
                def agent_node(state: AgentState):
                    # Access/modify state
                    state["messages"].append(new_message)
                    return state
            """
        },
        "Google ADK": {
            "approach": "Session-based state",
            "storage": "Google-managed",
            "access": "Via session object",
            "code_example": """
                session = agent.start_session()
                
                # State persists in session
                response1 = session.send_message("My name is Danny")
                response2 = session.send_message("What's my name?")
                # Agent remembers from session context
            """
        },
        "key_difference": """
            - Foundry: State = Message history (implicit)
            - LangGraph: State = Explicit typed dict (full control)
            - ADK: State = Session context (implicit)
        """
    }
}


# ============================================================================
# DECISION MATRIX
# ============================================================================

DECISION_CRITERIA = {
    "CHOOSE_FOUNDRY_IF": [
        "✅ Already invested in Azure ecosystem",
        "✅ Need enterprise security (Azure AD, RBAC)",
        "✅ Want managed infrastructure (no DevOps)",
        "✅ Require compliance certifications (SOC 2, HIPAA)",
        "✅ Integrating with Azure services (AI Search, Cosmos DB)",
        "✅ Prefer declarative over imperative",
        "✅ Team is less experienced with Python/orchestration",
    ],
    
    "CHOOSE_LANGGRAPH_IF": [
        "✅ Need maximum control over orchestration",
        "✅ Want vendor independence/portability",
        "✅ Have complex state management requirements",
        "✅ Need custom evaluation/testing frameworks",
        "✅ Self-hosting is acceptable",
        "✅ Team has strong Python/engineering skills",
        "✅ Budget conscious (more control over costs)",
    ],
    
    "CHOOSE_GOOGLE_ADK_IF": [
        "✅ Already on Google Cloud Platform",
        "✅ Using Vertex AI or Gemini models",
        "✅ Need Google Workspace integration",
        "✅ Want simplicity over control",
        "✅ Gemini models meet your needs",
        "✅ Prefer Google's managed services",
        "✅ Team comfortable with Google ecosystem",
    ]
}


# ============================================================================
# MIGRATION PATTERNS
# ============================================================================

MIGRATION_PATTERNS = {
    "LANGGRAPH_TO_FOUNDRY": {
        "steps": [
            "1. Map your StateGraph nodes to agent instructions",
            "2. Convert @tool functions to OpenAPI schemas",
            "3. Replace checkpointer with Foundry threads",
            "4. Replace graph.invoke() with agent runs",
            "5. Migrate state dict to thread metadata",
        ],
        "challenges": [
            "❌ Loss of explicit control flow",
            "❌ Less visibility into orchestration logic",
            "❌ Adapting to async/polling pattern",
        ],
        "benefits": [
            "✅ No infrastructure management",
            "✅ Built-in security & compliance",
            "✅ Native Azure integration",
        ]
    },
    
    "FOUNDRY_TO_LANGGRAPH": {
        "steps": [
            "1. Extract agent instructions → system prompts",
            "2. Convert OpenAPI tools → @tool functions",
            "3. Design explicit state graph",
            "4. Implement checkpointer for persistence",
            "5. Add conditional routing logic",
        ],
        "challenges": [
            "❌ Need to implement orchestration yourself",
            "❌ Manage infrastructure/scaling",
            "❌ Build monitoring & observability",
        ],
        "benefits": [
            "✅ Full control over execution flow",
            "✅ Vendor independence",
            "✅ Advanced debugging capabilities",
        ]
    },
    
    "ADK_TO_FOUNDRY": {
        "steps": [
            "1. Map Agent configs to Foundry agents",
            "2. Convert FunctionDeclarations to OpenAPI",
            "3. Replace sessions with threads",
            "4. Adapt from sync to async patterns",
            "5. Migrate to Azure services",
        ],
        "challenges": [
            "❌ Different model ecosystem (Gemini → GPT)",
            "❌ Different cloud platforms",
            "❌ Different API patterns",
        ],
        "benefits": [
            "✅ Similar managed approach",
            "✅ Better Azure integration",
            "✅ More mature enterprise features",
        ]
    }
}


# ============================================================================
# PRACTICAL SCENARIOS
# ============================================================================

SCENARIO_RECOMMENDATIONS = {
    "CUSTOMER_SUPPORT_BOT": {
        "best_fit": "Foundry",
        "reasoning": [
            "High security requirements (customer data)",
            "Need audit logging & compliance",
            "Simple orchestration (RAG + ticketing)",
            "Azure AD for employee auth",
        ],
        "second_choice": "Google ADK (if on GCP)",
    },
    
    "COMPLEX_RESEARCH_AGENT": {
        "best_fit": "LangGraph",
        "reasoning": [
            "Complex multi-step workflows",
            "Need custom evaluation metrics",
            "Requires sophisticated state management",
            "Team can handle orchestration complexity",
        ],
        "second_choice": "Foundry (if simpler is acceptable)",
    },
    
    "INTERNAL_PRODUCTIVITY_TOOL": {
        "best_fit": "Google ADK",
        "reasoning": [
            "Workspace integration (Gmail, Drive, Calendar)",
            "Simpler use case (info retrieval)",
            "Team already on Google Cloud",
            "Want fastest time to market",
        ],
        "second_choice": "Foundry (if on Azure)",
    },
    
    "MULTI_TENANT_MSP_PLATFORM": {
        "best_fit": "Foundry",
        "reasoning": [
            "Need tenant isolation (Azure AD)",
            "Compliance requirements (SOC 2)",
            "Want managed infrastructure",
            "Azure integration for customer services",
        ],
        "second_choice": "LangGraph (if need custom multi-tenancy)",
    }
}


# ============================================================================
# COST COMPARISON (Rough Estimates)
# ============================================================================

COST_CONSIDERATIONS = """
🎓 COST MODELS:

FOUNDRY:
- Model costs: Same as Azure OpenAI (pay per token)
- No platform fees (included in Azure OpenAI)
- Infrastructure: Minimal (managed service)
- Total: ~$0.01-0.03 per 1K tokens (model dependent)

LANGGRAPH:
- Model costs: Varies by provider (OpenAI, Anthropic, etc.)
- Platform: Free (open source)
- Infrastructure: You pay for hosting (VMs, containers, etc.)
- Total: Model costs + infrastructure costs

GOOGLE ADK:
- Model costs: Gemini pricing (competitive)
- Platform: Free (included with Gemini)
- Infrastructure: Minimal (managed service)
- Total: ~$0.0007-0.007 per 1K tokens (Gemini rates)

VERDICT:
- Cheapest models: Google ADK (Gemini rates)
- Most predictable: Foundry/ADK (managed)
- Most control: LangGraph (optimize everything)
"""


if __name__ == "__main__":
    print("🎓 Platform Comparison Guide")
    print("=" * 60)
    print("\nThis file contains architectural comparisons.")
    print("Import the dictionaries to explore specific concepts.")
    print("\nExample:")
    print("  from architecture_comparison import CONCEPTUAL_MAP")
    print("  print(CONCEPTUAL_MAP['AGENT_DEFINITION'])")
