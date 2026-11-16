<!-- AI-assisted: updated with Codex; review pending by Ravi (Tech Lead). -->
# Crop Helper web deployment and Azure API trial

This runbook documents the existing Crop Helper deployment and how to reproduce the app locally. It does not create Azure or Cloudflare resources. The current product uses a manual Cloudflare Pages Direct Upload; no GitHub Actions workflow deploys Crop Helper.

## Current deployment

- **Public app:** [https://crop-helper.pages.dev](https://crop-helper.pages.dev/)
- **Cloudflare Pages project:** crop-helper, Direct Upload.
- **Published web code commit:** 37552552250d42a74f61a3a9ca1676a59a38693f, reported by Ravi as the code used for the 2026-11-16 deployment. This is the published app revision, not a later documentation commit.
- **Product API:** https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io
- **API CORS origin:** https://crop-helper.pages.dev (API_CORS_ORIGINS).
- **Azure status:** Ravi/Satélite reported revision field-shift-api--0000002 running image cf835d52a54d; /health returned 200. A public browser smoke after the Pages release received a live recommendation response.

The API runs under a time-limited Azure trial. The earlier operational note estimated expiry around Dec 15, 2026, but the account's Azure portal is authoritative; do not promise API availability on a specific date or through the Jan 26, 2027 winners announcement. Do not upgrade the subscription to pay-as-you-go as an automatic fallback.

The static web build is durable relative to the API: saved demo JSON is committed under apps/web/public/demo/. With VITE_API_URL empty, the app reads those saved results and explains when the selected crop history was not applied. With VITE_API_URL configured, it calls the API and reports an error if the service is unavailable; it does not substitute a saved recommendation.

## Reproduce locally without cloud resources

Requirements: Node.js 24 or newer, uv, and Python 3.12.

    uv venv -p 3.12 .venv
    uv pip install -r requirements-dev.txt -r apps/api/requirements.txt
    cd apps/web
    npm ci

From the repository root, start the API on loopback in one terminal:

    API_CORS_ORIGINS=http://localhost:5173 .venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

Start the web app in another terminal. For the saved demo, leave the API URL empty:

    cd apps/web
    VITE_API_URL= npm run dev

For local live mode, point the web app at the local API:

    cd apps/web
    VITE_API_URL=http://localhost:8000 npm run dev

To exercise the public Azure trial instead, use the public endpoint shown above as VITE_API_URL. It is public configuration, not a credential. Never put passwords, tokens or private API keys in a VITE_* variable; Vite embeds these values in browser assets.

Focused web/API contract checks:

    cd apps/web
    npm test
    npm run lint
    npm run typecheck
    cd ..
    .venv/bin/python -m pytest -m "not network"

The network marker is for tests that call live data services. A local build and test run do not create cloud resources or deploy anything.

## Build and upload to the existing Pages project

Build the live variant from the repository root:

    cd apps/web
    npm ci
    VITE_API_URL=https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io npm run build
    test -f dist/index.html

For a durable demo-only build, set VITE_API_URL to an empty value instead:

    VITE_API_URL= npm run build
    test -f dist/index.html

To upload, sign in to the Cloudflare dashboard in the operator's browser, open **Workers & Pages → crop-helper → Deployments → Create a new deployment**, choose the production environment, and upload the apps/web/dist folder (or a ZIP whose root contains index.html). Select **Save and Deploy**. Use the existing crop-helper project; do not create a new project or change its name. See Cloudflare's [Direct Upload guide](https://developers.cloudflare.com/pages/get-started/direct-upload/).

The same upload can also be made with Wrangler after authenticating locally with npx wrangler login:

    npx wrangler pages deploy dist --project-name=crop-helper

Do not store Cloudflare credentials in this repository. The existing [internal-map workflow](../../.github/workflows/deploy-internal-map.yml) deploys a different Pages project, nether-field-map; it must not be repointed to Crop Helper. The existing [API workflow](../../.github/workflows/deploy-api.yml) is the legacy Google Cloud Run path, not the current Azure service.

## Verify the API and CORS

    API_URL=https://field-shift-api.kindpebble-07cb9fe8.brazilsouth.azurecontainerapps.io
    curl -fsS "$API_URL/health"
    curl -i -X OPTIONS "$API_URL/recommendation" \
      -H 'Origin: https://crop-helper.pages.dev' \
      -H 'Access-Control-Request-Method: POST' \
      -H 'Access-Control-Request-Headers: content-type'
    curl -fsS -X POST "$API_URL/recommendation" \
      -H 'Origin: https://crop-helper.pages.dev' \
      -H 'Content-Type: application/json' \
      --data '{"lat":-10.685,"lon":-37.425,"radius_km":5,"crop":"maize","previous_crops":["beans"],"priority":"water","lang":"pt-BR"}'

The recommendation contract separates the intended crop from previous_crops. Unsupported history is rejected; empty or unknown history must not create a score bonus or a pest-cycle claim. Cache keys include the crop history. Treat a live request as successful only when it returns a valid recommendation for those inputs.

## Roll back or return to demo mode

To restore a previous production upload, open **Workers & Pages → crop-helper → Deployments**, find a successful production deployment, open its three-dot menu, and select **Rollback to this deployment**. Cloudflare documents that a successful production deployment is a valid rollback target; preview deployments are not. See [Cloudflare Pages rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/).

If the Azure trial expires, the API may stop responding while the Pages assets remain available. To keep the same public URL usable, upload the demo-only build with empty VITE_API_URL, or roll back to a known successful demo-only deployment. Verify that the selected demo clearly says its saved history was not applied where relevant. Do not leave an expired API URL baked into a build that is presented as working live mode.

## Infrastructure guard

[scripts/deploy_azure_api.sh](../../scripts/deploy_azure_api.sh) provisions Azure resources, including a resource group, registry and Container Apps environment. It is not part of local reproduction or the Pages Direct Upload procedure. Do not run it or create new infrastructure as part of routine builds; API provisioning, subscription changes and infrastructure removal require a separate explicit instruction from Ravi. The old Google Cloud Run plan and its workflow remain in the repository as historical material.
