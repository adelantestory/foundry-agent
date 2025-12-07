#!/bin/bash

# =============================================================================
# Foundry Agent Infrastructure - Deployment Script
# =============================================================================
# 
# 🎓 TEACHING POINTS:
# 1. Automate infrastructure deployment (repeatability)
# 2. Validate before deploy (catch errors early)
# 3. Handle failures gracefully (rollback, retry)
# 4. Output deployment info (for app configuration)
#
# Usage:
#   ./deploy.sh dev eastus      # Deploy to dev environment
#   ./deploy.sh prod westus2    # Deploy to production
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

ENVIRONMENT=${1:-dev}
LOCATION=${2:-eastus}
RESOURCE_GROUP="rg-foundry-agent-${ENVIRONMENT}"
DEPLOYMENT_NAME="foundry-agent-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================

log_info "Starting deployment to ${ENVIRONMENT} environment in ${LOCATION}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    log_error "Azure CLI is not installed. Install from: https://aka.ms/installazurecli"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    log_error "Not logged in to Azure. Run 'az login' first."
    exit 1
fi

# Get current subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

log_info "Using subscription: ${SUBSCRIPTION_NAME} (${SUBSCRIPTION_ID})"

# Confirm deployment
if [ "$ENVIRONMENT" == "prod" ]; then
    log_warn "You are deploying to PRODUCTION!"
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_info "Deployment cancelled."
        exit 0
    fi
fi

# =============================================================================
# RESOURCE GROUP
# =============================================================================

log_info "Checking resource group: ${RESOURCE_GROUP}"

if az group exists --name ${RESOURCE_GROUP} | grep -q "false"; then
    log_info "Creating resource group: ${RESOURCE_GROUP}"
    az group create \
        --name ${RESOURCE_GROUP} \
        --location ${LOCATION} \
        --tags \
            Environment="${ENVIRONMENT}" \
            Application="Foundry-Agent" \
            ManagedBy="Bicep"
else
    log_info "Resource group already exists: ${RESOURCE_GROUP}"
fi

# =============================================================================
# VALIDATE TEMPLATE
# =============================================================================

log_info "Validating Bicep template..."

az deployment group validate \
    --resource-group ${RESOURCE_GROUP} \
    --template-file infrastructure/main.bicep \
    --parameters infrastructure/${ENVIRONMENT}.bicepparam \
    --name ${DEPLOYMENT_NAME}

if [ $? -eq 0 ]; then
    log_info "✅ Template validation successful"
else
    log_error "❌ Template validation failed"
    exit 1
fi

# =============================================================================
# DEPLOY INFRASTRUCTURE
# =============================================================================

log_info "Deploying infrastructure..."
log_info "Deployment name: ${DEPLOYMENT_NAME}"

az deployment group create \
    --resource-group ${RESOURCE_GROUP} \
    --template-file infrastructure/main.bicep \
    --parameters infrastructure/${ENVIRONMENT}.bicepparam \
    --name ${DEPLOYMENT_NAME} \
    --verbose

if [ $? -eq 0 ]; then
    log_info "✅ Deployment successful"
else
    log_error "❌ Deployment failed"
    exit 1
fi

# =============================================================================
# GET DEPLOYMENT OUTPUTS
# =============================================================================

log_info "Retrieving deployment outputs..."

# Get outputs from deployment
OUTPUTS=$(az deployment group show \
    --resource-group ${RESOURCE_GROUP} \
    --name ${DEPLOYMENT_NAME} \
    --query properties.outputs \
    -o json)

# Extract key values
AI_PROJECT_NAME=$(echo $OUTPUTS | jq -r '.aiProjectName.value')
CONNECTION_STRING=$(echo $OUTPUTS | jq -r '.connectionString.value')
OPENAI_ENDPOINT=$(echo $OUTPUTS | jq -r '.openAiEndpoint.value')
OPENAI_DEPLOYMENT=$(echo $OUTPUTS | jq -r '.openAiDeploymentName.value')

# =============================================================================
# CREATE .ENV FILE
# =============================================================================

log_info "Creating .env file for ${ENVIRONMENT} environment..."

ENV_FILE=".env.${ENVIRONMENT}"

cat > ${ENV_FILE} << EOF
# =============================================================================
# Azure AI Foundry Configuration - ${ENVIRONMENT} Environment
# Generated: $(date)
# =============================================================================

# Azure AI Project
AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}
AZURE_RESOURCE_GROUP=${RESOURCE_GROUP}
AZURE_PROJECT_NAME=${AI_PROJECT_NAME}
AZURE_ENDPOINT=$(echo $OUTPUTS | jq -r '.connectionString.value' | cut -d';' -f1)

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=${OPENAI_ENDPOINT}
AZURE_OPENAI_DEPLOYMENT_NAME=${OPENAI_DEPLOYMENT}
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Observability
APPLICATIONINSIGHTS_CONNECTION_STRING=$(echo $OUTPUTS | jq -r '.appInsightsConnectionString.value')
LOG_LEVEL=INFO

# Authentication (for local development - use managed identity in production)
# AZURE_TENANT_ID=
# AZURE_CLIENT_ID=
# AZURE_CLIENT_SECRET=

# Governance
MAX_TOKENS_PER_REQUEST=4000
ENABLE_CONTENT_FILTERING=true
ENABLE_AUDIT_LOGGING=true
EOF

log_info "✅ Environment file created: ${ENV_FILE}"

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

echo ""
echo "============================================================================="
echo "DEPLOYMENT SUMMARY"
echo "============================================================================="
echo ""
echo "Environment:        ${ENVIRONMENT}"
echo "Resource Group:     ${RESOURCE_GROUP}"
echo "Location:           ${LOCATION}"
echo "Deployment Name:    ${DEPLOYMENT_NAME}"
echo ""
echo "AI Project Name:    ${AI_PROJECT_NAME}"
echo "OpenAI Deployment:  ${OPENAI_DEPLOYMENT}"
echo ""
echo "Environment File:   ${ENV_FILE}"
echo ""
echo "============================================================================="
echo ""

# =============================================================================
# NEXT STEPS
# =============================================================================

log_info "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Copy ${ENV_FILE} to .env (or use directly)"
echo "  2. Run: python src/examples.py"
echo "  3. Configure RBAC for users:"
echo "     az role assignment create \\"
echo "       --role 'Cognitive Services OpenAI User' \\"
echo "       --assignee <user-email> \\"
echo "       --scope /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/*"
echo ""
echo "View deployment in Azure Portal:"
echo "  https://portal.azure.com/#@/resource/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/overview"
echo ""

# =============================================================================
# OPTIONAL: DESTROY SCRIPT
# =============================================================================
# 
# To clean up all resources:
#   az group delete --name ${RESOURCE_GROUP} --yes --no-wait
#
# 🎓 WARNING: This is IRREVERSIBLE! All data will be deleted.
#
# =============================================================================
