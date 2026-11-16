<!-- AI-assisted: drafted with Claude Code; pending review by Ravi (Tech Lead). -->
# Cloud Run deploy of the API (issue #65)

The files are ready: [`Dockerfile`](../../Dockerfile), [`.dockerignore`](../../.dockerignore), [`apps/api/requirements.txt`](../../apps/api/requirements.txt) and [`.github/workflows/deploy-api.yml`](../../.github/workflows/deploy-api.yml). The workflow does nothing (it only prints a notice) until the variables below exist. It runs on a push to `dev` that touches the API, `src/`, the Dockerfile or the data baked into the image, and by hand (*Actions → Deploy API → Run workflow*). No JSON key, no secret, CPU only.

The image contains `src/`, `apps/api/`, the snapshots read by `/diagnosis` (`apps/web/public/data`), the ZARC tables (`data/reference/zarc`) and the IBGE municipal mesh. It has no `.netrc`, no `.env` and no Earthdata credentials, and runs as a non-root user.

## What Lucas creates (Google Cloud, owner of the account)

Steps 1 to 4 of [gcp-setup.md](gcp-setup.md) first (credit, project and APIs, budget alert, service accounts). Then:

1. **Credit window.** In *Billing → Credits*, confirm the end date is **on or after Jan 26, 2027** (winners announcement). Record the date in [STATUS.md](../team/STATUS.md). If it ends earlier, tell Ravi now.
2. **Budget alert of US$ 50** (AD-10): [gcp-setup.md, section 3](gcp-setup.md).
3. **Artifact Registry repository** for the images:
   ```bash
   gcloud artifacts repositories create field-shift --repository-format=docker --location=<REGION>
   ```
4. **Workload Identity Federation** pool and provider restricted to this repository, and the deploy service account: [gcp-setup.md, sections 4 and 5](gcp-setup.md). Roles of the deploy account for this workflow: `roles/run.developer`, `roles/artifactregistry.writer` and `roles/iam.serviceAccountUser` on the runtime account. (`roles/run.admin` from gcp-setup also works but is wider than needed.)
5. **Runtime service account** `app-runtime` (no roles are needed for the API itself: it reads no secret and calls only public weather and open-data endpoints).
6. **Make the service public, once**, after the first deploy has created it (judges need a link without login):
   ```bash
   gcloud run services add-iam-policy-binding <SERVICE> --region=<REGION> \
     --member=allUsers --role=roles/run.invoker
   ```
   Later deploys keep this setting. If an organization policy blocks `allUsers`, tell Ravi.

## What Ravi sets in GitHub (repository *Variables*, not secrets)

Settings → Secrets and variables → Actions → Variables (or `gh variable set NAME -R raviproenca/nether-field-shift-2026 --body VALUE`):

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | project id |
| `GCP_REGION` | for example `southamerica-east1` |
| `GCP_WIF_PROVIDER` | full provider name, `projects/<number>/locations/global/workloadIdentityPools/github/providers/github-repo` |
| `GCP_DEPLOY_SA` | `gh-deploy@<project>.iam.gserviceaccount.com` |
| `GCP_RUNTIME_SA` | `app-runtime@<project>.iam.gserviceaccount.com` |
| `GCP_AR_REPOSITORY` | `field-shift` (name from step 3) |
| `CLOUD_RUN_SERVICE` | for example `field-shift-api` |
| `API_CORS_ORIGINS` | `https://nether-field-map.pages.dev` (comma-separated for more origins) |

No secret is needed for the API.

## Checks

- Local build and run (done for this PR): `docker build -t field-shift-api .` then `docker run --rm -p 8080:8080 -e API_CORS_ORIGINS=https://nether-field-map.pages.dev field-shift-api`; `/health` answers without any secret, the dashboard origin gets `access-control-allow-origin`, other origins get none, and `POST /recommendation` returns the ZARC note.
- After the first deploy: open `<service URL>/health` and `<service URL>/docs`.

## Point the dashboard at the API

In [`deploy-internal-map.yml`](../../.github/workflows/deploy-internal-map.yml), give the `Build` step the variable (Vite reads it at build time) and store the service URL as the repository variable `API_URL`:

```yaml
      - name: Build
        working-directory: apps/web
        env:
          VITE_API_URL: ${{ vars.API_URL }}
        run: npm run build
```

Without `API_URL` the dashboard keeps showing the saved sample.
