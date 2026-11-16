#!/usr/bin/env bash
# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
# Deploys the product API (apps/api) to Azure Container Apps. Idempotent: run it again to redeploy.
# Needs the Azure CLI, already signed in (`az login`), and docker only if ACR Tasks are not allowed.
# No secret is stored here; everything is configured by environment variables (defaults below).
# Usage: scripts/deploy_azure_api.sh
set -euo pipefail

: "${AZ_LOCATION:=brazilsouth}"                 # use eastus if the subscription cannot create resources there
: "${AZ_RESOURCE_GROUP:=rg-field-shift}"
: "${AZ_ENVIRONMENT:=cae-field-shift}"
: "${AZ_APP:=field-shift-api}"
: "${API_CORS_ORIGINS:=https://nether-field-map.pages.dev}"
: "${AZ_CPU:=0.5}"
: "${AZ_MEMORY:=1Gi}"
: "${AZ_MIN_REPLICAS:=0}"                        # scales to zero when idle
: "${AZ_MAX_REPLICAS:=2}"
: "${PORT:=8080}"
: "${BUDGET_AMOUNT:=50}"                         # USD; set BUDGET_AMOUNT=0 to skip the budget
: "${BUDGET_EMAIL:=}"                            # where the budget alerts go (optional)

cd "$(git rev-parse --show-toplevel)"

az account show --query "{name:name,state:state}" -o none 2>/dev/null \
  || { echo "error: not signed in. Run 'az login' first." >&2; exit 1; }

# The registry name is global and must be unique: derive a stable suffix from the subscription id (never printed).
if [ -z "${AZ_ACR_NAME:-}" ]; then
  suffix=$(az account show --query id -o tsv | sha1sum | cut -c1-8)
  AZ_ACR_NAME="fieldshift${suffix}"
fi
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
IMAGE_NAME="field-shift-api:${IMAGE_TAG}"

echo "==> Providers and CLI extension"
az extension add --name containerapp --upgrade --yes -o none
for ns in Microsoft.App Microsoft.ContainerRegistry Microsoft.OperationalInsights; do
  az provider register --namespace "$ns" --wait -o none
done

echo "==> Resource group ${AZ_RESOURCE_GROUP} (${AZ_LOCATION})"
az group create --name "$AZ_RESOURCE_GROUP" --location "$AZ_LOCATION" -o none

echo "==> Container registry (Basic)"
if ! az acr show --name "$AZ_ACR_NAME" --resource-group "$AZ_RESOURCE_GROUP" -o none 2>/dev/null; then
  az acr create --name "$AZ_ACR_NAME" --resource-group "$AZ_RESOURCE_GROUP" --sku Basic \
    --admin-enabled true --location "$AZ_LOCATION" -o none
fi
ACR_SERVER=$(az acr show --name "$AZ_ACR_NAME" --resource-group "$AZ_RESOURCE_GROUP" --query loginServer -o tsv)

echo "==> Build and push ${IMAGE_NAME}"
if ! az acr build --registry "$AZ_ACR_NAME" --image "$IMAGE_NAME" --file Dockerfile . ; then
  echo "ACR Tasks unavailable; building with local docker instead."
  az acr login --name "$AZ_ACR_NAME" -o none
  docker build -t "${ACR_SERVER}/${IMAGE_NAME}" .
  docker push "${ACR_SERVER}/${IMAGE_NAME}"
fi

echo "==> Container Apps environment (no log workspace, to avoid its cost)"
if ! az containerapp env show --name "$AZ_ENVIRONMENT" --resource-group "$AZ_RESOURCE_GROUP" -o none 2>/dev/null; then
  az containerapp env create --name "$AZ_ENVIRONMENT" --resource-group "$AZ_RESOURCE_GROUP" \
    --location "$AZ_LOCATION" --logs-destination none -o none
fi

# Registry credentials are read into shell variables only; they are never printed or written to disk.
ACR_USER=$(az acr credential show --name "$AZ_ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show --name "$AZ_ACR_NAME" --query "passwords[0].value" -o tsv)

echo "==> Container app ${AZ_APP}"
if az containerapp show --name "$AZ_APP" --resource-group "$AZ_RESOURCE_GROUP" -o none 2>/dev/null; then
  az containerapp registry set --name "$AZ_APP" --resource-group "$AZ_RESOURCE_GROUP" \
    --server "$ACR_SERVER" --username "$ACR_USER" --password "$ACR_PASS" -o none
  az containerapp update --name "$AZ_APP" --resource-group "$AZ_RESOURCE_GROUP" \
    --image "${ACR_SERVER}/${IMAGE_NAME}" --cpu "$AZ_CPU" --memory "$AZ_MEMORY" \
    --min-replicas "$AZ_MIN_REPLICAS" --max-replicas "$AZ_MAX_REPLICAS" \
    --set-env-vars "API_CORS_ORIGINS=${API_CORS_ORIGINS}" -o none
else
  az containerapp create --name "$AZ_APP" --resource-group "$AZ_RESOURCE_GROUP" \
    --environment "$AZ_ENVIRONMENT" --image "${ACR_SERVER}/${IMAGE_NAME}" \
    --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port "$PORT" --cpu "$AZ_CPU" --memory "$AZ_MEMORY" \
    --min-replicas "$AZ_MIN_REPLICAS" --max-replicas "$AZ_MAX_REPLICAS" \
    --env-vars "API_CORS_ORIGINS=${API_CORS_ORIGINS}" "PORT=${PORT}" -o none
fi
unset ACR_USER ACR_PASS

if [ "$BUDGET_AMOUNT" != "0" ]; then
  echo "==> Cost budget of ${BUDGET_AMOUNT} USD (best effort)"
  start=$(date -u +%Y-%m-01)
  end=$(date -u -d "${start} +3 months" +%Y-%m-%d)
  args=(--budget-name field-shift --amount "$BUDGET_AMOUNT" --category cost --time-grain monthly
        --start-date "$start" --end-date "$end" --resource-group "$AZ_RESOURCE_GROUP")
  [ -n "$BUDGET_EMAIL" ] && args+=(--notifications "[{\"threshold\":90,\"operator\":\"GreaterThan\",\"contact-emails\":[\"${BUDGET_EMAIL}\"]}]")
  az consumption budget create "${args[@]}" -o none \
    || echo "warning: could not create the budget (the trial may not allow it). Create it in the portal: Cost Management > Budgets."
fi

FQDN=$(az containerapp show --name "$AZ_APP" --resource-group "$AZ_RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)
URL="https://${FQDN}"
echo "==> Smoke test ${URL}/health (the first call may take a few seconds: scale from zero)"
for attempt in 1 2 3 4 5 6; do
  if curl -fsS "${URL}/health"; then echo; break; fi
  sleep 10
done
echo "Service URL: ${URL}"
