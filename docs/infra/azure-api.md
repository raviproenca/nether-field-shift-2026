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

## Known issues from the first run (Nov 15, 2026)

- **`az extension add --name containerapp` fails with "Pip failed with status code 1".** An Azure CLI installed as a `uv` tool has a virtual environment without `pip`, and `az` installs extensions with pip. Fix used: `uv pip install --python ~/.local/share/uv/tools/azure-cli/bin/python pip`, then run the command again. Alternatively install the Azure CLI another way (the Microsoft package or installer), which ships with pip.
- **`az consumption budget create` returns 400** ("Invalid budget configuration, please use filter interface with 2019-05-01-preview"). The script treats the budget as best effort and goes on. Create the US$ 50 budget in the portal instead: *Cost Management → Budgets*, scope the resource group `rg-field-shift`, add alerts at 50%, 90% and 100%. A budget only sends alerts; it does not stop the spending.

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

**Current deployment (Nov 15, 2026):** `https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io` in Brazil South. Validated after the deploy:

- `/health` answers 200 with no secret in the response.
- CORS: `https://nether-field-map.pages.dev` is allowed (GET and the POST preflight); another origin (`https://example.org`) receives no `access-control-allow-origin` header.
- `POST /recommendation` for both pilots returns 200 with 3 strategies, the 15-day forecast available and the municipality code (Itabaiana 2802908: "inside the zoning"; Nossa Senhora da Glória 2804508: "only partly inside the ZARC").
- `/docs` answers 200.

**Cold start.** The app scales to zero, so the first request after a quiet period waits for a container to start (a few seconds). Pilot pre-warming (#111, #54) removes the slow part for the two pilots: their responses are built at image build time and served from the on-disk cache, so those calls do not wait for the weather and open-data services. It does not remove the container start itself, and other points are still computed on demand (then cached by rounded coordinates). Keep `AZ_MIN_REPLICAS=1` only if a live demo needs zero wait; that costs a little compute for as long as it runs.

## Point the dashboard at it

Store the printed URL as the repository variable `API_URL`; the dashboard build reads it as `VITE_API_URL` (see the workflow change in its own PR). Without `API_URL` the dashboard keeps the saved example. When the trial ends, unset `API_URL` and redeploy the dashboard so it stops calling a dead address (or it will show its normal error message for live points; the demo pilots keep working either way).

## Cost and what happens when the trial ends

Approximate, check the Azure pricing page: Container Apps (consumption plan) has a monthly free grant and costs nothing while scaled to zero; with this light use the app should stay near zero. The **Container Registry Basic costs about US$ 5 per month** (about US$ 0.17 per day) and is the main cost. Total for the trial: a few US dollars of the US$ 200.

The budget alert only notifies; it does not stop spending. If `az consumption budget create` is refused on the trial, create it in the portal (*Cost Management → Budgets*, US$ 50 for the resource group).

When the trial ends (about Dec 15) or the credit runs out, Azure disables the subscription: the API goes offline and the resources are deleted after a retention period unless the subscription is upgraded to pay-as-you-go (do not upgrade). Nothing else breaks: the Cloudflare dashboard, the saved example and the demo pilots do not use the API. To remove everything earlier (the registry, the environment and the app): `az group delete --name rg-field-shift --yes`. If the API disappears for any reason, the dashboard returns to its saved example and the demo pilots; clear the repository variable `API_URL` and redeploy the dashboard so it stops pointing at a dead address.
