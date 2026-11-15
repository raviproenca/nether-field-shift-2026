<!-- AI-assisted: drafted with Claude Code; pending review by Ravi (Tech Lead). -->
# API on Azure Container Apps (trial)

Decision (Ravi, Nov 15): the product API runs on **Azure Container Apps** with the US$ 200 trial credit instead of Google Cloud. This replaces the Cloud Run plan for issue #65; the files of [cloud-run-api.md](cloud-run-api.md) and `.github/workflows/deploy-api.yml` stay in the repository but are no longer needed.

**Important limit.** Azure is only available until the trial ends (about **Dec 15, 2026**). That does **not** cover the rule that every link must stay valid until **Jan 26, 2027**. So the main submission link is the static dashboard on Cloudflare Pages (`https://nether-field-map.pages.dev`), which works without the API: it shows the saved example and the two demo pilots. The dashboard must never depend on this API to be judged.

## What the script does

[`scripts/deploy_azure_api.sh`](../../scripts/deploy_azure_api.sh) (idempotent, `set -euo pipefail`, no secret inside):

1. registers the providers and the `containerapp` CLI extension;
2. creates a resource group, an Azure Container Registry (Basic) and a Container Apps environment without a log workspace;
3. builds the [`Dockerfile`](../../Dockerfile) with `az acr build` (falls back to local `docker build` and push if ACR Tasks are not allowed on the trial);
4. creates or updates the app: external ingress, port 8080, 0.5 vCPU, 1 GiB, **min replicas 0 (scales to zero)**, max 2, `API_CORS_ORIGINS=https://nether-field-map.pages.dev`;
5. tries to create a US$ 50 cost budget (best effort; see below);
6. calls `/health` and prints the service URL.

The registry admin user is used so the app can pull the image; its password is read into a shell variable, never printed or written. After the deploy, disabling it is optional (`az acr update -n <acr> --admin-enabled false` breaks later pulls, so only do it if you switch the app to a managed identity).

## Run it

```bash
az login                      # once, in your own terminal
az account show --query state # prints "Enabled"; do not paste ids anywhere
scripts/deploy_azure_api.sh
```

Settings (all optional, environment variables): `AZ_LOCATION` (default `brazilsouth`; use `eastus` if the trial cannot create resources there), `AZ_RESOURCE_GROUP`, `AZ_ENVIRONMENT`, `AZ_APP`, `AZ_ACR_NAME`, `API_CORS_ORIGINS`, `AZ_CPU`, `AZ_MEMORY`, `AZ_MIN_REPLICAS`, `AZ_MAX_REPLICAS`, `BUDGET_AMOUNT` (USD, `0` skips it) and `BUDGET_EMAIL` (alert recipient). Running it again redeploys the current commit.

## Test

```bash
URL=https://<the printed fqdn>
curl -s "$URL/health"
# CORS: the dashboard origin is allowed, another origin is not
curl -si -H "Origin: https://nether-field-map.pages.dev" "$URL/health" | grep -i access-control-allow-origin
curl -si -H "Origin: https://example.org" "$URL/health" | grep -ic access-control-allow-origin   # prints 0
# Recommendation for the two pilots
curl -s -X POST "$URL/recommendation" -H 'content-type: application/json' \
  -d '{"lat":-10.685,"lon":-37.425,"crop":"maize","priority":"water"}'
curl -s -X POST "$URL/recommendation" -H 'content-type: application/json' \
  -d '{"lat":-10.218,"lon":-37.42,"crop":"maize","priority":"water"}'
```

The first call after idle takes a few seconds (scale from zero).

## Point the dashboard at it

Store the printed URL as the repository variable `API_URL`; the dashboard build reads it as `VITE_API_URL` (see the workflow change in its own PR). Without `API_URL` the dashboard keeps the saved example. When the trial ends, unset `API_URL` and redeploy the dashboard so it stops calling a dead address (or it will show its normal error message for live points; the demo pilots keep working either way).

## Cost and what happens when the trial ends

Approximate, check the Azure pricing page: Container Apps (consumption plan) has a monthly free grant and costs nothing while scaled to zero; with this light use the app should stay near zero. The **Container Registry Basic costs about US$ 5 per month** (about US$ 0.17 per day) and is the main cost. Total for the trial: a few US dollars of the US$ 200.

The budget alert only notifies; it does not stop spending. If `az consumption budget create` is refused on the trial, create it in the portal (*Cost Management → Budgets*, US$ 50 for the resource group).

When the trial ends (about Dec 15) or the credit runs out, Azure disables the subscription: the API goes offline and the resources are deleted after a retention period unless the subscription is upgraded to pay-as-you-go (do not upgrade). Nothing else breaks: the Cloudflare dashboard, the saved example and the demo pilots do not use the API. To remove everything earlier: `az group delete --name rg-field-shift --yes`.
