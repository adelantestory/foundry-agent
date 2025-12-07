// =============================================================================
// Bicep Parameters File - Development Environment
// =============================================================================
//
// 🎓 TEACHING POINT:
// Parameters files let you deploy same template to different environments
// - dev.bicepparam for development
// - staging.bicepparam for staging  
// - prod.bicepparam for production
//
// Each environment has different:
// - Resource SKUs (dev=cheap, prod=robust)
// - Monitoring levels
// - Security posture
//
// =============================================================================

using './main.bicep'

// Environment configuration
param environmentName = 'dev'
param location = 'eastus'  // Change to your preferred region

// OpenAI model configuration
param openAiConfig = {
  modelName: 'gpt-4o'
  modelVersion: '2024-05-13'
  capacity: 10  // TPM (tokens per minute) in thousands
}

// Feature flags
param enableMonitoring = true
param enableKeyVault = true

// Resource tags
param tags = {
  Environment: 'Development'
  Application: 'Foundry-Agent'
  ManagedBy: 'Bicep'
  CostCenter: 'R&D'
  Owner: 'Danny@Delante'
}

// =============================================================================
// 🎓 NOTES FOR DIFFERENT ENVIRONMENTS:
// =============================================================================
//
// DEVELOPMENT:
// - Lower SKUs (cheaper)
// - Shorter retention periods
// - Public access enabled for debugging
// - Basic monitoring
//
// STAGING:
// - Production-like SKUs
// - Same config as prod
// - Used for testing before prod deployment
//
// PRODUCTION:
// - High-performance SKUs
// - Longer retention (90+ days)
// - Private endpoints only
// - Comprehensive monitoring & alerting
// - Geo-redundancy if needed
//
// =============================================================================
