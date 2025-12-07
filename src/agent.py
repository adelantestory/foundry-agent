"""
Core Agent Implementation - Production-Ready Azure AI Foundry Agent

🎓 KEY ARCHITECTURE:
This is the "orchestration layer" that brings together:
1. AIProjectClient (connection)
2. Agent (the autonomous entity)
3. Thread (conversation context)
4. Run (execution instance)
5. Tools (capabilities)

Compare Mental Models:
- LangGraph: Graph → Nodes → State → Execution
- Google ADK: Agent → Session → Turn → Response
- Foundry: Agent → Thread → Run → Messages
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import logging

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    Agent,
    AgentThread,
    ThreadMessage,
    MessageRole,
    RunStatus
)

from config import FoundryConfig
from client import FoundryClientManager
from tools import get_all_tools, execute_tool_call

logger = logging.getLogger(__name__)


# ===== Agent State Management =====

class AgentStatus(Enum):
    """
    Agent lifecycle states
    
    🎓 State machine pattern for tracking agent status
    """
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentMetrics:
    """
    Observability metrics for agent performance
    
    🎓 OBSERVABILITY TEACHING POINT:
    Track these metrics for:
    - Performance optimization
    - Cost monitoring
    - SLA compliance
    - Debugging
    """
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_tokens_used: int = 0
    average_response_time: float = 0.0
    tool_calls_made: int = 0
    
    def record_run(self, success: bool, duration: float, tokens: int, tool_calls: int):
        """Record metrics for a completed run"""
        self.total_runs += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1
        
        self.total_tokens_used += tokens
        self.tool_calls_made += tool_calls
        
        # Update rolling average
        self.average_response_time = (
            (self.average_response_time * (self.total_runs - 1) + duration)
            / self.total_runs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metrics for logging/telemetry"""
        return {
            "total_runs": self.total_runs,
            "success_rate": self.successful_runs / max(self.total_runs, 1),
            "total_tokens": self.total_tokens_used,
            "avg_response_time_seconds": round(self.average_response_time, 2),
            "tool_calls": self.tool_calls_made
        }


@dataclass
class ConversationContext:
    """
    Maintains conversation state and history
    
    🎓 This is like LangGraph's State or ADK's session context
    """
    thread_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    
    def get_message_count(self) -> int:
        """Get total message count"""
        return len(self.messages)
    
    def truncate_history(self, max_messages: int):
        """
        Truncate old messages to manage context window
        
        🎓 CONTEXT WINDOW MANAGEMENT:
        - Keep recent messages
        - Summarize or drop old ones
        - Prevents token limit errors
        """
        if len(self.messages) > max_messages:
            # Keep system message (if first) + recent messages
            if self.messages[0].get("role") == "system":
                self.messages = [self.messages[0]] + self.messages[-(max_messages-1):]
            else:
                self.messages = self.messages[-max_messages:]
            
            logger.info(f"📝 Truncated conversation history to {max_messages} messages")


# ===== Main Agent Class =====

class FoundryAgent:
    """
    Production-ready Azure AI Foundry Agent
    
    🎓 ARCHITECTURE OVERVIEW:
    
    Components:
    1. Agent Definition (instructions, model, tools)
    2. Thread Management (conversation context)
    3. Run Orchestration (execution control)
    4. Tool Integration (capabilities)
    5. Observability (metrics, logging)
    
    Lifecycle:
    create() → add_thread() → run() → get_response() → [repeat] → cleanup()
    """
    
    def __init__(
        self,
        config: FoundryConfig,
        client_manager: FoundryClientManager,
        name: str = "base-production-agent",
        instructions: Optional[str] = None
    ):
        """
        Initialize agent
        
        Args:
            config: Configuration object
            client_manager: Client manager for Foundry connection
            name: Agent name/identifier
            instructions: System instructions (agent's "personality")
        """
        self.config = config
        self.client_manager = client_manager
        self.name = name
        self.instructions = instructions or self._default_instructions()
        
        # State
        self.status = AgentStatus.INITIALIZING
        self.agent: Optional[Agent] = None
        self.threads: Dict[str, ConversationContext] = {}
        self.metrics = AgentMetrics()
        
        logger.info(f"🤖 Initializing agent: {name}")
    
    def _default_instructions(self) -> str:
        """
        Default system instructions
        
        🎓 PROMPT ENGINEERING TEACHING POINT:
        System instructions define:
        - Agent's role/persona
        - Capabilities and constraints
        - Response format
        - Escalation rules
        
        This is like LangGraph's system message or ADK's agent instructions
        """
        return """You are a helpful AI assistant for an enterprise environment.

ROLE:
You help users with information retrieval, task automation, and problem-solving.

CAPABILITIES:
- Query internal knowledge bases
- Look up customer information
- Create support tickets
- Calculate cost estimates
- Search the web for current information

GUIDELINES:
1. Always be professional and concise
2. Use tools when you need specific information
3. Cite sources when providing facts
4. Escalate to humans for sensitive decisions
5. Never expose sensitive data in logs or responses

SECURITY:
- Validate all inputs before processing
- Follow data privacy regulations
- Log all actions for audit compliance

RESPONSE FORMAT:
- Be clear and structured
- Explain your reasoning
- Provide actionable next steps when relevant"""
    
    async def create(self) -> "FoundryAgent":
        """
        Create the agent in Azure AI Foundry
        
        🎓 ASYNC PATTERN:
        Foundry SDK operations are async for:
        - Non-blocking I/O
        - Better concurrency
        - Scalability
        
        Returns:
            Self (for method chaining)
        """
        try:
            client = self.client_manager.get_client()
            
            # Get tool definitions
            tools = get_all_tools()
            logger.info(f"🔧 Registering {len(tools)} tools with agent")
            
            # Create agent
            # 🎓 This is the KEY SDK call that creates the agent entity
            self.agent = await client.agents.create_agent(
                model=self.config.azure_openai_deployment_name,
                name=self.name,
                instructions=self.instructions,
                tools=tools,
                # Foundry-specific settings
                tool_resources={},  # Add file/vector stores here
                metadata={
                    "created_by": "foundry-sdk",
                    "version": "1.0.0",
                    "environment": "production"
                }
            )
            
            self.status = AgentStatus.READY
            logger.info(f"✅ Agent created successfully: {self.agent.id}")
            
            return self
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"❌ Failed to create agent: {e}")
            raise
    
    async def create_thread(
        self,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation thread
        
        🎓 THREAD CONCEPT:
        A thread is an isolated conversation context, like:
        - A customer support ticket
        - A chat session
        - A task execution context
        
        Compare to:
        - LangGraph: Thread ID for checkpointer
        - ADK: Session/conversation ID
        
        Args:
            metadata: Optional metadata for the thread
        
        Returns:
            Thread ID
        """
        try:
            client = self.client_manager.get_client()
            
            # Create thread
            thread = await client.agents.create_thread(
                metadata=metadata or {}
            )
            
            # Track thread context
            context = ConversationContext(
                thread_id=thread.id,
                metadata=metadata or {}
            )
            self.threads[thread.id] = context
            
            logger.info(f"📝 Created thread: {thread.id}")
            return thread.id
            
        except Exception as e:
            logger.error(f"❌ Failed to create thread: {e}")
            raise
    
    async def add_message(
        self,
        thread_id: str,
        content: str,
        role: str = "user"
    ) -> str:
        """
        Add a message to a thread
        
        🎓 MESSAGE TYPES:
        - user: From the human
        - assistant: From the agent
        - system: Instructions/context (less common in threads)
        
        Args:
            thread_id: Thread to add message to
            content: Message content
            role: Message role (user/assistant)
        
        Returns:
            Message ID
        """
        try:
            client = self.client_manager.get_client()
            
            # Add message to thread
            message = await client.agents.create_message(
                thread_id=thread_id,
                role=role,
                content=content
            )
            
            # Update local context
            if thread_id in self.threads:
                self.threads[thread_id].add_message(role, content)
            
            logger.debug(f"💬 Added {role} message to thread {thread_id}")
            return message.id
            
        except Exception as e:
            logger.error(f"❌ Failed to add message: {e}")
            raise
    
    async def run(
        self,
        thread_id: str,
        instructions_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent on a thread
        
        🎓 RUN LIFECYCLE:
        1. Create run (queued)
        2. Agent processes messages
        3. Agent may call tools
        4. Run completes (or fails)
        5. Response available
        
        This is the CORE orchestration method!
        
        Args:
            thread_id: Thread to run on
            instructions_override: Optional instructions override for this run
        
        Returns:
            Run result with response
        """
        if not self.agent:
            raise RuntimeError("Agent not created. Call create() first.")
        
        self.status = AgentStatus.RUNNING
        start_time = time.time()
        
        try:
            client = self.client_manager.get_client()
            
            # Create run
            run = await client.agents.create_run(
                thread_id=thread_id,
                agent_id=self.agent.id,
                instructions=instructions_override
            )
            
            logger.info(f"🏃 Started run: {run.id} on thread {thread_id}")
            
            # Poll for completion
            # 🎓 Foundry uses polling pattern (not streaming yet in all SDKs)
            run = await self._poll_run_completion(client, thread_id, run.id)
            
            # Get response
            duration = time.time() - start_time
            response = await self._extract_response(client, thread_id, run)
            
            # Record metrics
            tokens_used = getattr(run, 'usage', {}).get('total_tokens', 0)
            tool_calls = len(getattr(run, 'required_action', {}).get('tool_calls', []))
            self.metrics.record_run(
                success=True,
                duration=duration,
                tokens=tokens_used,
                tool_calls=tool_calls
            )
            
            self.status = AgentStatus.COMPLETED
            logger.info(f"✅ Run completed in {duration:.2f}s")
            
            return {
                "run_id": run.id,
                "status": run.status,
                "response": response,
                "duration_seconds": duration,
                "tokens_used": tokens_used,
                "metrics": self.metrics.to_dict()
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record_run(
                success=False,
                duration=duration,
                tokens=0,
                tool_calls=0
            )
            self.status = AgentStatus.FAILED
            logger.error(f"❌ Run failed after {duration:.2f}s: {e}")
            raise
    
    async def _poll_run_completion(
        self,
        client: AIProjectClient,
        thread_id: str,
        run_id: str
    ):
        """
        Poll for run completion
        
        🎓 POLLING PATTERN:
        Why polling instead of webhooks?
        - Simpler for development
        - Works in all environments
        - No webhook endpoint needed
        
        Production consideration:
        - Consider streaming API when available
        - Implement exponential backoff
        - Add timeout safeguards
        """
        timeout = self.config.agent_timeout_seconds
        poll_interval = 1  # seconds
        elapsed = 0
        
        while elapsed < timeout:
            run = await client.agents.get_run(thread_id, run_id)
            
            if run.status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED]:
                return run
            
            # Handle tool calls (if required)
            if run.status == RunStatus.REQUIRES_ACTION:
                await self._handle_tool_calls(client, thread_id, run_id, run)
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Run timed out after {timeout} seconds")
    
    async def _handle_tool_calls(
        self,
        client: AIProjectClient,
        thread_id: str,
        run_id: str,
        run
    ):
        """
        Handle tool execution during run
        
        🎓 TOOL CALLING FLOW:
        1. Agent decides to call tool
        2. Run enters REQUIRES_ACTION state
        3. We execute tool locally
        4. Submit tool outputs
        5. Agent continues with results
        
        This is the "agentic loop"!
        """
        if not run.required_action:
            return
        
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []
        
        for tool_call in tool_calls:
            logger.info(f"🔧 Executing tool: {tool_call.function.name}")
            
            try:
                # Parse arguments
                arguments = json.loads(tool_call.function.arguments)
                
                # Execute tool
                result = execute_tool_call(tool_call.function.name, arguments)
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result)
                })
                
            except Exception as e:
                logger.error(f"❌ Tool execution failed: {e}")
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps({"error": str(e)})
                })
        
        # Submit tool outputs
        await client.agents.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )
    
    async def _extract_response(
        self,
        client: AIProjectClient,
        thread_id: str,
        run
    ) -> str:
        """
        Extract agent response from completed run
        
        🎓 Response extraction gets the final assistant message
        """
        messages = await client.agents.list_messages(
            thread_id=thread_id,
            order="desc",
            limit=1
        )
        
        if messages.data:
            message = messages.data[0]
            if message.role == "assistant":
                # Extract text content
                content_parts = []
                for content in message.content:
                    if hasattr(content, 'text'):
                        content_parts.append(content.text.value)
                return "\n".join(content_parts)
        
        return "No response generated"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return self.metrics.to_dict()
    
    async def cleanup(self):
        """
        Cleanup agent resources
        
        🎓 Resource cleanup:
        - Delete agent
        - Clear threads
        - Release connections
        """
        try:
            if self.agent:
                client = self.client_manager.get_client()
                await client.agents.delete_agent(self.agent.id)
                logger.info(f"🗑️  Deleted agent: {self.agent.id}")
            
            self.threads.clear()
            self.status = AgentStatus.INITIALIZING
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


# Note: Missing import for asyncio - will add in usage example
import asyncio
import json
