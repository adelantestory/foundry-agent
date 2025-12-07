"""
Usage Examples - Learn by Doing

🎓 LEARNING PATH:
1. Basic conversation (hello world)
2. Tool usage (agent autonomy)
3. Multi-turn conversation (context management)
4. Error handling (production resilience)
5. Metrics & observability (monitoring)

Run these examples to understand each capability!
"""

import asyncio
import logging
from typing import List, Dict, Any

from config import load_config
from client import FoundryClientManager
from agent import FoundryAgent

# Configure logging for examples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Example 1: Basic Conversation =====

async def example_basic_conversation():
    """
    🎓 LESSON: Agent Creation & Simple Interaction
    
    Learn:
    - How to initialize the agent
    - Create a conversation thread
    - Send a message and get response
    - Clean up resources
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Conversation")
    print("="*60 + "\n")
    
    # Load configuration
    config = load_config()
    
    # Create client manager
    client_manager = FoundryClientManager(config)
    
    try:
        # Create agent
        agent = FoundryAgent(
            config=config,
            client_manager=client_manager,
            name="example-basic-agent"
        )
        
        # Initialize agent in Foundry
        await agent.create()
        print("✅ Agent created\n")
        
        # Create conversation thread
        thread_id = await agent.create_thread(
            metadata={"example": "basic_conversation"}
        )
        print(f"✅ Thread created: {thread_id}\n")
        
        # Add user message
        await agent.add_message(
            thread_id=thread_id,
            content="Hello! Can you introduce yourself?"
        )
        print("📤 Sent: Hello! Can you introduce yourself?\n")
        
        # Run agent
        result = await agent.run(thread_id)
        print(f"📥 Response: {result['response']}\n")
        print(f"⏱️  Duration: {result['duration_seconds']:.2f}s")
        print(f"🎫 Tokens used: {result['tokens_used']}\n")
        
        # Cleanup
        await agent.cleanup()
        print("✅ Cleanup complete")
        
    finally:
        client_manager.close()


# ===== Example 2: Tool Usage =====

async def example_tool_usage():
    """
    🎓 LESSON: Agent Autonomy with Tools
    
    Learn:
    - How agents decide when to use tools
    - Tool calling flow
    - Tool result integration
    - Observing agent reasoning
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Tool Usage (Agent Autonomy)")
    print("="*60 + "\n")
    
    config = load_config()
    client_manager = FoundryClientManager(config)
    
    try:
        agent = FoundryAgent(config, client_manager, name="tool-demo-agent")
        await agent.create()
        
        thread_id = await agent.create_thread(
            metadata={"example": "tool_usage"}
        )
        
        # Ask question that requires tool usage
        query = "What is the estimated monthly cost for a standard tier VM running 24/7?"
        print(f"📤 Query: {query}\n")
        
        await agent.add_message(thread_id, query)
        
        # Run and observe tool calls
        print("🤖 Agent is thinking and calling tools...\n")
        result = await agent.run(thread_id)
        
        print(f"📥 Response: {result['response']}\n")
        print(f"🔧 Tool calls made: {result.get('metrics', {}).get('tool_calls', 0)}")
        print(f"⏱️  Duration: {result['duration_seconds']:.2f}s\n")
        
        await agent.cleanup()
        
    finally:
        client_manager.close()


# ===== Example 3: Multi-Turn Conversation =====

async def example_multi_turn():
    """
    🎓 LESSON: Context Management
    
    Learn:
    - How threads maintain conversation history
    - Context window management
    - Follow-up questions
    - Conversation flow
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Multi-Turn Conversation (Context)")
    print("="*60 + "\n")
    
    config = load_config()
    client_manager = FoundryClientManager(config)
    
    try:
        agent = FoundryAgent(config, client_manager, name="context-demo-agent")
        await agent.create()
        
        thread_id = await agent.create_thread(
            metadata={"example": "multi_turn"}
        )
        
        # Conversation sequence
        conversation = [
            "Look up customer information for customer ID 'CUST-001'",
            "What was their tier?",  # Follow-up question
            "Create a support ticket for them about a billing issue",
        ]
        
        for i, message in enumerate(conversation, 1):
            print(f"\n--- Turn {i} ---")
            print(f"📤 User: {message}")
            
            await agent.add_message(thread_id, message)
            result = await agent.run(thread_id)
            
            print(f"📥 Agent: {result['response']}")
        
        # Show conversation stats
        print("\n--- Conversation Stats ---")
        context = agent.threads[thread_id]
        print(f"Total messages: {context.get_message_count()}")
        print(f"Duration: {datetime.now() - context.created_at}")
        
        await agent.cleanup()
        
    finally:
        client_manager.close()


# ===== Example 4: Error Handling =====

async def example_error_handling():
    """
    🎓 LESSON: Production Resilience
    
    Learn:
    - Graceful error handling
    - Retry logic
    - Timeout management
    - Error recovery
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Error Handling & Resilience")
    print("="*60 + "\n")
    
    config = load_config()
    client_manager = FoundryClientManager(config)
    
    try:
        agent = FoundryAgent(config, client_manager, name="resilient-agent")
        await agent.create()
        
        thread_id = await agent.create_thread()
        
        # Test 1: Malformed tool request
        print("Test 1: Handling malformed tool requests")
        try:
            await agent.add_message(
                thread_id,
                "Calculate cost for an invalid resource type"
            )
            result = await agent.run(thread_id)
            print(f"✅ Handled gracefully: {result['response'][:100]}...\n")
        except Exception as e:
            print(f"❌ Error caught: {e}\n")
        
        # Test 2: Empty message
        print("Test 2: Handling edge cases")
        try:
            # Agent should handle this gracefully
            await agent.add_message(thread_id, "")
            result = await agent.run(thread_id)
            print(f"✅ Handled empty message\n")
        except Exception as e:
            print(f"❌ Error caught: {e}\n")
        
        # Show metrics even with errors
        print("--- Agent Metrics ---")
        metrics = agent.get_metrics()
        print(f"Success rate: {metrics['success_rate']:.1%}")
        print(f"Total runs: {metrics['total_runs']}")
        
        await agent.cleanup()
        
    finally:
        client_manager.close()


# ===== Example 5: Observability =====

async def example_observability():
    """
    🎓 LESSON: Monitoring & Metrics
    
    Learn:
    - Performance tracking
    - Token usage monitoring
    - Cost estimation
    - SLA compliance
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Observability & Metrics")
    print("="*60 + "\n")
    
    config = load_config()
    client_manager = FoundryClientManager(config)
    
    try:
        agent = FoundryAgent(config, client_manager, name="monitored-agent")
        await agent.create()
        
        # Run multiple interactions
        queries = [
            "What is your purpose?",
            "Calculate cost for a basic VM",
            "Look up customer CUST-123",
        ]
        
        for query in queries:
            thread_id = await agent.create_thread()
            await agent.add_message(thread_id, query)
            await agent.run(thread_id)
        
        # Display comprehensive metrics
        print("\n--- Performance Metrics ---")
        metrics = agent.get_metrics()
        
        print(f"Total runs: {metrics['total_runs']}")
        print(f"Success rate: {metrics['success_rate']:.1%}")
        print(f"Average response time: {metrics['avg_response_time_seconds']:.2f}s")
        print(f"Total tokens used: {metrics['total_tokens']}")
        print(f"Tool calls made: {metrics['tool_calls']}")
        
        # Cost estimation (example rates)
        # 🎓 Track costs for customer billing
        gpt4_input_cost_per_1k = 0.01
        gpt4_output_cost_per_1k = 0.03
        estimated_cost = (metrics['total_tokens'] / 1000) * 0.02  # Average
        print(f"Estimated cost: ${estimated_cost:.4f}")
        
        await agent.cleanup()
        
    finally:
        client_manager.close()


# ===== Example 6: Production Pattern =====

async def example_production_pattern():
    """
    🎓 LESSON: Production Deployment Pattern
    
    This is how you'd structure agent usage in production:
    - Single agent instance (reuse)
    - Thread per conversation
    - Proper error handling
    - Metrics collection
    - Resource cleanup
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Production Pattern")
    print("="*60 + "\n")
    
    config = load_config()
    client_manager = FoundryClientManager(config)
    
    # Create long-lived agent (init once)
    agent = FoundryAgent(
        config, 
        client_manager, 
        name="production-agent",
        instructions="""You are a customer support agent for Delante Solutions.
        
        Your role is to:
        - Answer questions about Azure services
        - Help with cost estimates
        - Create support tickets for issues
        - Provide excellent customer service
        
        Always be professional, accurate, and helpful."""
    )
    
    try:
        await agent.create()
        print("✅ Production agent initialized\n")
        
        # Simulate handling multiple customer sessions
        customer_sessions = [
            {
                "customer_id": "CUST-001",
                "messages": ["Hi, I need help with Azure costs"]
            },
            {
                "customer_id": "CUST-002",
                "messages": ["Can you look up my account?"]
            }
        ]
        
        for session in customer_sessions:
            # Each customer gets their own thread
            thread_id = await agent.create_thread(
                metadata={"customer_id": session["customer_id"]}
            )
            
            print(f"🔷 Session for {session['customer_id']}")
            
            for message in session["messages"]:
                await agent.add_message(thread_id, message)
                result = await agent.run(thread_id)
                print(f"  Agent: {result['response'][:80]}...")
            
            print(f"  ✅ Session complete\n")
        
        # Show aggregate metrics
        print("--- Production Metrics ---")
        print(agent.get_metrics())
        
    except Exception as e:
        logger.error(f"Production error: {e}")
        # In production: send alert, log to monitoring system
    
    finally:
        await agent.cleanup()
        client_manager.close()


# ===== Main Runner =====

async def run_all_examples():
    """Run all examples in sequence"""
    examples = [
        ("Basic Conversation", example_basic_conversation),
        ("Tool Usage", example_tool_usage),
        ("Multi-Turn Conversation", example_multi_turn),
        ("Error Handling", example_error_handling),
        ("Observability", example_observability),
        ("Production Pattern", example_production_pattern),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {e}")
        
        # Pause between examples
        await asyncio.sleep(2)


async def run_single_example(example_num: int):
    """Run a specific example by number"""
    examples = [
        example_basic_conversation,
        example_tool_usage,
        example_multi_turn,
        example_error_handling,
        example_observability,
        example_production_pattern,
    ]
    
    if 1 <= example_num <= len(examples):
        await examples[example_num - 1]()
    else:
        print(f"Invalid example number. Choose 1-{len(examples)}")


if __name__ == "__main__":
    import sys
    from datetime import datetime
    
    print("\n" + "="*60)
    print("Azure AI Foundry Agent - Learning Examples")
    print("="*60)
    
    if len(sys.argv) > 1:
        # Run specific example
        example_num = int(sys.argv[1])
        asyncio.run(run_single_example(example_num))
    else:
        # Run all examples
        print("\nRunning all examples...\n")
        asyncio.run(run_all_examples())
    
    print("\n" + "="*60)
    print("Examples complete!")
    print("="*60 + "\n")
