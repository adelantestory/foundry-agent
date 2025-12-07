# 🚀 Quick Start Guide - Get Running in 15 Minutes

This guide gets you from zero to running your first Foundry agent.

---

## Step 1: Prerequisites (2 minutes)

### Required
```bash
# Check Python version (need 3.9+)
python --version

# Check Azure CLI
az --version

# Login to Azure
az login
```

### Set Your Subscription
```bash
# List subscriptions
az account list --output table

# Set the subscription you want to use
az account set --subscription "Your Subscription Name"
```

---

## Step 2: Azure Setup (5 minutes)

### Option A: Use Existing Project (Fastest)

If you already have an Azure AI Studio project:

1. Go to https://ai.azure.com
2. Open your project
3. Click **Settings** (bottom left)
4. Copy these values:
   - Subscription ID
   - Resource Group
   - Project Name
   - Endpoint URL

Skip to Step 3!

### Option B: Create New Project (If Needed)

```bash
# Create resource group
az group create \
  --name rg-foundry-quickstart \
  --location eastus

# Deploy infrastructure (takes ~5 minutes)
cd /path/to/foundry-agent
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh dev eastus
```

The script will output a `.env.dev` file with everything configured!

---

## Step 3: Install & Configure (3 minutes)

### Install Dependencies
```bash
# Navigate to project
cd /path/to/foundry-agent

# Install requirements
pip install -r requirements.txt
```

### Configure Environment

**If you used deployment script:**
```bash
cp .env.dev .env
```

**If using existing project:**
```bash
cp .env.template .env
# Edit .env with your values from Azure portal
```

Your `.env` should look like:
```bash
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_PROJECT_NAME=your-project-name
AZURE_ENDPOINT=https://your-project.api.azureml.ms
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

---

## Step 4: First Run (5 minutes)

### Test Configuration
```bash
python -c "from src.config import load_config; load_config()"
```

Expected output:
```
✅ Configuration loaded successfully
   - Project: your-project-name
   - Auth: azure_cli
   - Model: gpt-4o
```

### Run First Example
```bash
python src/examples.py 1
```

This runs **Example 1: Basic Conversation**

You should see:
```
============================================================
EXAMPLE 1: Basic Conversation
============================================================

✅ Agent created

✅ Thread created: thread_abc123...

📤 Sent: Hello! Can you introduce yourself?

🤖 Agent is processing...

📥 Response: Hello! I'm a helpful AI assistant...

⏱️  Duration: 2.34s
🎫 Tokens used: 156
```

**🎉 Congratulations! Your first agent is working!**

---

## Step 5: Explore Examples (Ongoing)

Run each example to learn different capabilities:

```bash
# Example 1: Basic conversation
python src/examples.py 1

# Example 2: Tool usage (agent autonomy)
python src/examples.py 2

# Example 3: Multi-turn conversation
python src/examples.py 3

# Example 4: Error handling
python src/examples.py 4

# Example 5: Observability
python src/examples.py 5

# Example 6: Production pattern
python src/examples.py 6

# Run ALL examples
python src/examples.py
```

---

## What Each Example Teaches

### Example 1: Basic Conversation
- Agent creation
- Thread management
- Simple query/response
- **Learn:** Core SDK usage

### Example 2: Tool Usage
- How agents decide to call tools
- Tool execution flow
- Result integration
- **Learn:** Agent autonomy

### Example 3: Multi-Turn
- Conversation context
- Follow-up questions
- Memory management
- **Learn:** Context handling

### Example 4: Error Handling
- Graceful failures
- Retry logic
- Edge cases
- **Learn:** Production resilience

### Example 5: Observability
- Metrics tracking
- Performance monitoring
- Cost estimation
- **Learn:** Monitoring

### Example 6: Production Pattern
- Long-lived agents
- Multiple conversations
- Best practices
- **Learn:** Real deployment

---

## Next Steps

### Immediate (15-30 minutes)
1. ✅ Run all 6 examples
2. ✅ Read the README.md
3. ✅ Review code comments in `src/agent.py`

### Short-term (1-2 hours)
1. **Customize a tool** in `src/tools.py`
   - Add your own business logic
   - Test with the agent

2. **Create custom instructions**
   - Modify agent personality
   - Add domain expertise
   - Test different behaviors

3. **Experiment with parameters**
   - Change model temperature
   - Adjust token limits
   - Try different models

### Medium-term (This week)
1. **Follow learning path** in `docs/LEARNING_PATH.md`
2. **Build a small project**
   - Choose from project ideas
   - Apply what you learned
3. **Deploy to Azure**
   - Use Container Apps
   - Set up monitoring

---

## Troubleshooting Common Issues

### "Authentication failed"
```bash
# Re-login to Azure
az login

# Verify you're on correct subscription
az account show
```

### "Agent not created" / API errors
```bash
# Check your project has model deployed
az cognitiveservices account deployment list \
  --name your-openai-resource \
  --resource-group your-resource-group
```

### "Module not found"
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### "Configuration error"
```bash
# Verify .env file exists and has correct values
cat .env

# Test configuration
python -c "from src.config import load_config; config = load_config(); print(config)"
```

---

## Getting Help

### Documentation
- **This project:** Start with `README.md`
- **Azure AI Foundry:** https://learn.microsoft.com/azure/ai-studio/
- **SDK Reference:** https://learn.microsoft.com/python/api/azure-ai-projects/

### Compare with Other Platforms
- See `docs/architecture_comparison.py` to understand differences
- LangGraph: https://langchain-ai.github.io/langgraph/
- Google ADK: https://ai.google.dev/adk

### Support Channels
- Azure AI Discord
- Stack Overflow: tag `azure-ai-studio`
- GitHub Issues on this repo

---

## Quick Reference Card

### Essential Commands
```bash
# Run specific example
python src/examples.py <1-6>

# Test configuration
python -c "from src.config import load_config; load_config()"

# View logs
tail -f app.log  # (if you enable file logging)

# Azure CLI - list resources
az resource list --resource-group rg-foundry-quickstart --output table
```

### Key Files
```
src/
├── config.py       # Configuration & authentication
├── client.py       # Foundry client management
├── tools.py        # Custom tool definitions
├── agent.py        # Core agent implementation
└── examples.py     # Learning examples (START HERE)

docs/
├── LEARNING_PATH.md              # Full curriculum
└── architecture_comparison.py    # Platform comparison

infrastructure/
├── main.bicep      # Azure resources
└── deploy.sh       # Deployment automation
```

### Important Concepts
```
Agent     = Autonomous entity (persistent, has skills)
Thread    = Conversation context (isolated session)
Run       = Single execution (one processing cycle)
Tool      = Function agent can call (capability)
```

---

## Success Checklist

After this quick start, you should be able to:
- ✅ Create agents programmatically
- ✅ Define custom tools
- ✅ Handle conversations
- ✅ Understand the architecture
- ✅ Know where to learn more

**Ready to dive deeper? Check out `docs/LEARNING_PATH.md`!** 🚀

---

## Time Investment Guide

- **Quick Start (this guide):** 15 minutes
- **Run all examples:** 30 minutes
- **Customize first tool:** 1 hour
- **Build small project:** 1 day
- **Production deployment:** 2-3 days
- **Expert mastery:** 2-4 weeks

Start small, iterate often, ship to production! 🎯
