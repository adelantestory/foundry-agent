// =============================================================================
// Azure AI Foundry Agent - Infrastructure as Code
// =============================================================================
// 
// 🎓 TEACHING POINTS:
// 1. Infrastructure as Code = Repeatable, version-controlled deployments
// 2. Bicep = Azure's native IaC language (cleaner than ARM JSON)
// 3. This template creates ALL resources needed for production agents
//
// Deploy with:
//   az deployment group create \
//     --resource-group <rg-name> \
//     --template-file main.bicep \
//     --parameters main.bicepparam
//
// =============================================================================

targetScope = 'resourceGroup'

// =============================================================================
// PARAMETERS
// =============================================================================

@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environmentName string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Unique suffix for resource naming')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Azure OpenAI deployment configuration')
param openAiConfig object = {
  modelName: 'gpt-4o'
  modelVersion: '2024-05-13'
  capacity: 10  // TPM in thousands
}

@description('Enable Application Insights for monitoring')
param enableMonitoring bool = true

@description('Enable Azure Key Vault for secrets')
param enableKeyVault bool = true

@description('Tags for all resources')
param tags object = {
  Environment: environmentName
  Application: 'Foundry-Agent'
  ManagedBy: 'Bicep'
}

// =============================================================================
// VARIABLES
// =============================================================================

var namingPrefix = 'foundry-${environmentName}'
var aiHubName = '${namingPrefix}-hub-${uniqueSuffix}'
var aiProjectName = '${namingPrefix}-project-${uniqueSuffix}'
var openAiName = '${namingPrefix}-openai-${uniqueSuffix}'
var searchName = '${namingPrefix}-search-${uniqueSuffix}'
var storageName = 'foundry${environmentName}${take(uniqueSuffix, 8)}'
var keyVaultName = '${namingPrefix}-kv-${take(uniqueSuffix, 8)}'
var appInsightsName = '${namingPrefix}-insights-${uniqueSuffix}'
var logAnalyticsName = '${namingPrefix}-logs-${uniqueSuffix}'

// =============================================================================
// EXISTING RESOURCES (Dependencies)
// =============================================================================

// 🎓 In production, you might already have these resources
// This template can reference existing or create new

// =============================================================================
// STORAGE ACCOUNT
// =============================================================================
// 🎓 Required for: AI Hub data storage, checkpoints, artifacts

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Allow'  // 🎓 In prod: 'Deny' + private endpoints
      bypass: 'AzureServices'
    }
  }
}

// Blob service for storage account
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

// Container for agent artifacts
resource agentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'agent-artifacts'
  properties: {
    publicAccess: 'None'
  }
}

// =============================================================================
// KEY VAULT (Optional but recommended)
// =============================================================================
// 🎓 Store secrets securely: API keys, connection strings, credentials

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = if (enableKeyVault) {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true  // 🎓 Use RBAC instead of access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'  // 🎓 In prod: 'Deny' + private endpoint
      bypass: 'AzureServices'
    }
  }
}

// =============================================================================
// APPLICATION INSIGHTS & LOG ANALYTICS
// =============================================================================
// 🎓 Observability stack for monitoring agent performance

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (enableMonitoring) {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environmentName == 'prod' ? 90 : 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = if (enableMonitoring) {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: enableMonitoring ? logAnalytics.id : null
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =============================================================================
// AZURE OPENAI
// =============================================================================
// 🎓 The LLM brain for your agents

resource openAi 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAiName
  location: location
  tags: tags
  sku: {
    name: 'S0'  // Standard pricing tier
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'  // 🎓 In prod: consider private endpoint
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Deploy GPT-4o model
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAi
  name: openAiConfig.modelName
  sku: {
    name: 'Standard'
    capacity: openAiConfig.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: openAiConfig.modelName
      version: openAiConfig.modelVersion
    }
    raiPolicyName: 'Microsoft.Default'  // 🎓 Content filtering policy
  }
}

// =============================================================================
// AZURE AI SEARCH (Optional - for RAG)
// =============================================================================
// 🎓 Vector database for knowledge base / RAG scenarios

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  tags: tags
  sku: {
    name: 'basic'  // 🎓 Upgrade to 'standard' for prod workloads
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      bypass: 'AzurePortal'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// =============================================================================
// AZURE AI HUB
// =============================================================================
// 🎓 Central management for AI projects and resources

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiHubName
  location: location
  tags: tags
  kind: 'hub'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Foundry Agent Hub (${environmentName})'
    description: 'AI Hub for managing Foundry agents and projects'
    storageAccount: storage.id
    keyVault: enableKeyVault ? keyVault.id : null
    applicationInsights: enableMonitoring ? appInsights.id : null
    
    // Associated AI services
    associatedWorkspaces: [
      openAi.id
    ]
    
    publicNetworkAccess: 'Enabled'
    
    // 🎓 Managed network: Isolate hub from internet
    managedNetwork: {
      isolationMode: 'AllowInternetOutbound'  // Change to 'AllowOnlyApprovedOutbound' for prod
    }
  }
}

// =============================================================================
// AZURE AI PROJECT
// =============================================================================
// 🎓 Project = isolated workspace for a team/application

resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: aiProjectName
  location: location
  tags: tags
  kind: 'project'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Foundry Agent Project (${environmentName})'
    description: 'Project for deploying production Foundry agents'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
}

// =============================================================================
// RBAC ASSIGNMENTS
// =============================================================================
// 🎓 Grant necessary permissions using Role-Based Access Control

// Cognitive Services OpenAI User role for AI Project
resource openAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, openAi.id, 'OpenAIUser')
  scope: openAi
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')  // Cognitive Services OpenAI User
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Search Index Data Reader for AI Project (if search enabled)
resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, search.id, 'SearchIndexDataReader')
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')  // Search Index Data Reader
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Storage Blob Data Contributor for AI Hub
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiHub.id, storage.id, 'BlobContributor')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')  // Storage Blob Data Contributor
    principalId: aiHub.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =============================================================================
// OUTPUTS
// =============================================================================
// 🎓 Export values needed for application configuration

output aiProjectName string = aiProject.name
output aiProjectId string = aiProject.id
output aiHubName string = aiHub.name

output connectionString string = '${aiProject.properties.discoveryUrl};${subscription().subscriptionId};${resourceGroup().name};${aiProject.name}'

output openAiEndpoint string = openAi.properties.endpoint
output openAiDeploymentName string = modelDeployment.name

output searchEndpoint string = 'https://${search.name}.search.windows.net'
output storageAccountName string = storage.name

output appInsightsConnectionString string = enableMonitoring ? appInsights.properties.ConnectionString : ''
output appInsightsInstrumentationKey string = enableMonitoring ? appInsights.properties.InstrumentationKey : ''

output keyVaultName string = enableKeyVault ? keyVault.name : ''
output keyVaultUri string = enableKeyVault ? keyVault.properties.vaultUri : ''

// Connection details for .env file
output envFileContent string = '''
# Generated by Bicep deployment
AZURE_SUBSCRIPTION_ID=${subscription().subscriptionId}
AZURE_RESOURCE_GROUP=${resourceGroup().name}
AZURE_PROJECT_NAME=${aiProject.name}
AZURE_ENDPOINT=${aiProject.properties.discoveryUrl}

AZURE_OPENAI_DEPLOYMENT_NAME=${modelDeployment.name}
AZURE_OPENAI_ENDPOINT=${openAi.properties.endpoint}

${enableMonitoring ? 'APPLICATIONINSIGHTS_CONNECTION_STRING=${appInsights.properties.ConnectionString}' : ''}

# Use managed identity in Azure, or set these for local dev:
# AZURE_TENANT_ID=
# AZURE_CLIENT_ID=
# AZURE_CLIENT_SECRET=
'''

// =============================================================================
// DEPLOYMENT NOTES
// =============================================================================
// 
// 🎓 POST-DEPLOYMENT STEPS:
// 
// 1. Copy output values to your .env file
// 2. Assign users "Cognitive Services OpenAI User" role on OpenAI resource
// 3. Configure managed identity for production deployments
// 4. Set up private endpoints for network isolation (prod)
// 5. Configure content filtering policies in Azure OpenAI
// 6. Set up alerts in Application Insights
// 
// 🎓 SECURITY HARDENING (Production):
// 
// 1. Enable private endpoints for all services
// 2. Disable public network access
// 3. Use managed identities (no secrets!)
// 4. Enable diagnostic logs
// 5. Set up Azure Policy compliance
// 6. Configure resource locks
// 7. Enable Microsoft Defender for Cloud
// 
// =============================================================================
