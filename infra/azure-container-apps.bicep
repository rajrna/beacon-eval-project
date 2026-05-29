@description('Beacon Container Apps deployment')
param location string = resourceGroup().location
param environmentName string = 'beacon-dev'
param acrLoginServer string
param acrUsername string
@secure()
param acrPassword string
param imageTag string = 'latest'
param keyVaultName string

// ── Container Apps Environment ────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${environmentName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ── Managed Identity ──────────────────────────────────────────────────────────

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${environmentName}-identity'
  location: location
}

// ── API Container App ─────────────────────────────────────────────────────────

resource apiApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'beacon-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [{
        server: acrLoginServer
        username: acrUsername
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acrPassword }
      ]
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [{
        name: 'beacon-api'
        image: '${acrLoginServer}/beacon-api:${imageTag}'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        command: ['uvicorn', 'beacon.main:app', '--host', '0.0.0.0', '--port', '8000']
        env: [
          { name: 'ENVIRONMENT', value: 'dev' }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'REDIS_URL', secretRef: 'redis-url' }
          { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [{
          name: 'http-scale'
          http: { metadata: { concurrentRequests: '50' } }
        }]
      }
    }
  }
}

// ── Worker Container App ──────────────────────────────────────────────────────

resource workerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'beacon-worker'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      registries: [{
        server: acrLoginServer
        username: acrUsername
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acrPassword }
      ]
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [{
        name: 'beacon-worker'
        image: '${acrLoginServer}/beacon-worker:${imageTag}'
        resources: { cpu: json('1.0'), memory: '2Gi' }
        command: ['rq', 'worker', '--url', 'redis://$(REDIS_URL)', 'beacon-eval', 'beacon-safety', 'beacon-export']
        env: [
          { name: 'ENVIRONMENT', value: 'dev' }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'REDIS_URL', secretRef: 'redis-url' }
          { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [{
          name: 'redis-scale'
          custom: {
            type: 'redis'
            metadata: { queueName: 'beacon-eval', queueLength: '10' }
          }
        }]
      }
    }
  }
}

// ── Web Container App ─────────────────────────────────────────────────────────

resource webApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'beacon-web'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      registries: [{
        server: acrLoginServer
        username: acrUsername
        passwordSecretRef: 'acr-password'
      }]
      secrets: [
        { name: 'acr-password', value: acrPassword }
      ]
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [{
        name: 'beacon-web'
        image: '${acrLoginServer}/beacon-web:${imageTag}'
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output apiUrl string = 'https://${apiApp.properties.configuration.ingress.fqdn}'
output webUrl string = 'https://${webApp.properties.configuration.ingress.fqdn}'
