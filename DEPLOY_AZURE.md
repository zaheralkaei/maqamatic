# Deploying Maqamatic to Azure

The app runs on **Azure Container Apps**: one container, scale-to-zero, public
HTTPS, images pulled from GitHub Container Registry. Infrastructure is defined in
[`infra/main.bicep`](infra/main.bicep); continuous deployment lives in
[`.github/workflows/deploy-azure.yml`](.github/workflows/deploy-azure.yml).

Nothing in the application code is Azure-specific. The same image still runs under
`docker-compose up` and on Railway.

## What gets created

| Resource | Purpose | Approx. cost |
| --- | --- | --- |
| Container App (`maqamatic`) | Runs the gunicorn container | $0 while idle; consumption-metered when serving |
| Container Apps environment | Networking + ingress + TLS | Free |
| Log Analytics workspace | Container logs, 30-day retention | Free under the 5 GB/month ingestion grant |

With `minReplicas: 0` and hobby traffic this should sit inside the Container Apps
monthly free grant. Verify current rates in the pricing calculator before relying
on that — the figures above are magnitudes, not quotes.

## Prerequisites

- An Azure subscription.
- `az` is **not** installed on this machine. Easiest path is
  [Azure Cloud Shell](https://shell.azure.com) — browser-based, `az` preinstalled,
  nothing to set up. Steps below marked *(Cloud Shell)* run there; everything else
  runs locally.
- Local Docker (present: 28.3.2) and `gh` (present, authenticated).

---

## Step 1 — Publish the first image

The infrastructure needs an image to pull on its very first deploy. The simplest
way to get one is to let CI build it: push this branch to `main` and the workflow
builds and publishes to GHCR on its own.

**The first run will fail, and that is expected.** It fails at the *Log in to
Azure* step, because the secrets and the Container App do not exist yet. The two
steps that matter — build and push — run before it and succeed. You are using CI
purely as a build machine at this point.

If you would rather build locally (requires Docker running), grant the package
scope your token lacks and push by hand instead:

```bash
gh auth refresh -h github.com -s write:packages
```

```bash
gh auth token | docker login ghcr.io -u zaheralkaei --password-stdin && docker build -t ghcr.io/zaheralkaei/maqamatic:latest . && docker push ghcr.io/zaheralkaei/maqamatic:latest
```

### Make the package public

**This step is required and easy to miss.** New GHCR packages are private, and the
Bicep pulls anonymously — a private package fails with `UNAUTHORIZED` at deploy time.

Go to `https://github.com/users/zaheralkaei/packages/container/maqamatic/settings`
→ *Danger Zone* → *Change visibility* → **Public**.

## Step 2 — Create the infrastructure *(Cloud Shell)*

Clone the repo in Cloud Shell so it can see the Bicep file:

```bash
git clone https://github.com/zaheralkaei/maqamatic.git && cd maqamatic
```

Create the resource group and deploy:

```bash
az group create --name maqamatic-rg --location swedencentral
```

```bash
az deployment group create --resource-group maqamatic-rg --template-file infra/main.bicep --query properties.outputs.url.value -o tsv
```

The deploy takes 3–5 minutes; the Container Apps environment is the slow part.
It prints the live HTTPS URL. The first request will be slow — that is
scale-to-zero doing its job.

> **On regions.** Avoid `westeurope`: it is capacity-constrained and rejects new
> customers with `RequestDisallowedByAzure` / "region is currently not accepting
> new customers". `swedencentral` is the default here for that reason.
> `germanywestcentral`, `northeurope`, `francecentral`, and `polandcentral` are
> good fallbacks.
>
> A resource group's location cannot be changed after creation, and
> `infra/main.bicep` defaults every resource to `resourceGroup().location`. So if
> you need to switch regions, delete the (empty) group and recreate it rather
> than passing a location override — that keeps later deploys parameter-free.

## Step 3 — Wire up continuous deployment *(Cloud Shell)*

GitHub authenticates to Azure with OIDC, so there is no client secret to store or
rotate. Create the app registration and grant it rights over the resource group:

```bash
APP_ID=$(az ad app create --display-name maqamatic-github-actions --query appId -o tsv) && az ad sp create --id "$APP_ID" && echo "AZURE_CLIENT_ID=$APP_ID"
```

Register the federated credential that trusts pushes to `main`:

```bash
az ad app federated-credential create --id "$APP_ID" --parameters '{"name":"main-branch","issuer":"https://token.actions.githubusercontent.com","subject":"repo:zaheralkaei/maqamatic:ref:refs/heads/main","audiences":["api://AzureADTokenExchange"]}'
```

Give it Contributor on the resource group only — not the whole subscription:

```bash
SUB_ID=$(az account show --query id -o tsv) && az role assignment create --role Contributor --assignee "$APP_ID" --scope "/subscriptions/$SUB_ID/resourceGroups/maqamatic-rg" && echo "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)" && echo "AZURE_SUBSCRIPTION_ID=$SUB_ID"
```

Note the three printed values, then set them as repository secrets **locally**
(substituting the values from above):

```bash
gh secret set AZURE_CLIENT_ID --body "<appId>" && gh secret set AZURE_TENANT_ID --body "<tenantId>" && gh secret set AZURE_SUBSCRIPTION_ID --body "<subscriptionId>"
```

## Step 4 — Verify

Every run first executes the test suite (`pytest`, Python 3.11); the image is
only built and rolled out if the tests pass. Push to `main`, or trigger the
workflow by hand:

```bash
gh workflow run deploy-azure.yml && gh run watch
```

The run summary prints the deployed URL. Then check the app answers:

```bash
curl -fsS https://<your-fqdn>/health
```

---

## Operations

**Logs.** Live tail:

```bash
az containerapp logs show --name maqamatic --resource-group maqamatic-rg --follow
```

**Roll back.** Every deploy creates a revision tagged with its commit SHA, so
rollback is a traffic shift rather than a rebuild:

```bash
az containerapp revision list --name maqamatic --resource-group maqamatic-rg --query "[].{revision:name,created:properties.createdTime,active:properties.active}" -o table
```

```bash
az containerapp ingress traffic set --name maqamatic --resource-group maqamatic-rg --revision-weight <revision-name>=100
```

**Kill cold starts.** If the scale-to-zero delay proves annoying, this is a
one-line change — set `minReplicas` to `1` in `infra/main.bicep` and redeploy.
Expect roughly $10–20/month for an always-warm replica.

**Custom domain.** Point a CNAME at the `fqdn` output, then:

```bash
az containerapp hostname add --hostname <your-domain> --name maqamatic --resource-group maqamatic-rg
```

Managed certificates are issued free.

**Tear down everything:**

```bash
az group delete --name maqamatic-rg --yes
```

---

## Known constraints

`maxReplicas` is deliberately pinned to **1**. Two pieces of per-instance state
make horizontal scaling incorrect today:

1. **Rate limiting is in-process.** `RateLimiter` in [`web/app.py`](web/app.py) is
   a plain `OrderedDict` per gunicorn worker, so the effective limit is
   10 requests/minute × workers (2) × replicas, and the window resets on every
   deploy. It keys on the real client IP via `ProxyFix`, trusting
   `TRUSTED_PROXY_HOPS` (default `1`, the Container Apps ingress) entries of
   `X-Forwarded-For`; set it to `0` when nothing sits in front of the app.
2. **Downloads are instance-local.** `/api/download/<file_id>` reads from the
   container's `output/` directory, so a download served by a different replica
   than the one that generated the file returns 404.

Both also mean generated scores do not survive a restart — same as on Railway.
Fixing them properly means Redis for the limiter and Azure Blob Storage with SAS
URLs for the scores, at which point `maxReplicas` can be raised safely. Until
then, one replica is the correct setting, not a limitation of Azure.
