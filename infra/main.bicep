// Maqamatic - Azure Container Apps infrastructure
//
// Deploys: Log Analytics workspace -> Container Apps environment -> Container App.
// The container image is pulled anonymously from GitHub Container Registry, so
// there is no registry resource and no pull credential to manage.
//
//   az deployment group create -g maqamatic-rg -f infra/main.bicep

targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Base name used for every resource in this deployment.')
param appName string = 'maqamatic'

@description('Container image to run. Must be publicly pullable.')
param containerImage string = 'ghcr.io/zaheralkaei/maqamatic:latest'

@description('Port the container listens on. Passed to the app as $PORT.')
param containerPort int = 5025

@description('Minimum replicas. 0 enables scale-to-zero (cheapest, but the first request after idle pays a cold start).')
@minValue(0)
param minReplicas int = 0

@description('''Maximum replicas. Pinned to 1 on purpose: the app keeps its rate-limiter
in process memory and serves generated scores from local disk, so a second replica would
double the effective rate limit and 404 downloads routed to the wrong instance.''')
@minValue(1)
param maxReplicas int = 1

@description('vCPU per replica. Must pair with memory (0.25/0.5Gi, 0.5/1Gi, 0.75/1.5Gi, 1/2Gi).')
param cpu string = '0.5'

@description('Memory per replica.')
param memory string = '1Gi'

@description('Log retention in days.')
param logRetentionInDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: logRetentionInDays
  }
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
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

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: appName
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'PORT'
              value: string(containerPort)
            }
            {
              name: 'FLASK_ENV'
              value: 'production'
            }
            {
              name: 'PYTHONUNBUFFERED'
              value: '1'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 3
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 15
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

@description('Public HTTPS URL of the deployed app.')
output url string = 'https://${containerApp.properties.configuration.ingress.fqdn}'

@description('Ingress hostname, for pointing a CNAME at later.')
output fqdn string = containerApp.properties.configuration.ingress.fqdn
