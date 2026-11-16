<!-- AI-assisted: drafted with Claude Code; pending review by Ravi (Tech Lead). -->
# Google Cloud setup (one-time, account owner)

Decision (see [docs/team/decisions.md](../team/decisions.md)): everything for the farmer product runs on Google Cloud with the **Global Offers** credit (US$ 300 for 90 days). Activated on Nov 14–15, 2026, it lasts until about Feb 12–13, 2027, which covers the winners announcement on Jan 26, 2027. The trial is activated by **Lucas** (story 6.1).

This page lists only the steps that need the account owner (account, billing, permissions). Build, deploy and application config are done later by the team via CLI or GitHub Actions. **Never paste credentials, tokens or card data into chat, issues, PRs or the repo.**

## 1. Activate the credit (browser, account owner)
1. Open the Google Cloud link on the Space Apps **Global Offers** page (logged in) and start the **Free Trial** with a personal Google account.
2. The card is asked **for verification only**. The Free Trial does **not** charge automatically: when the credit or the 90 days run out, resources stop unless someone clicks **Upgrade**. **Do not upgrade.**
3. In *Billing → Credits*, check the credit and its **end date**, and record the date in [docs/team/STATUS.md](../team/STATUS.md).

## 2. Project and APIs (`gcloud`, Cloud Shell or local)
Project IDs are global and must be unique. Use a neutral name, with no company brand.

```bash
gcloud auth login
PROJECT=nether-field-shift-<suffix>
gcloud projects create "$PROJECT" --name="Nether Field Shift"
gcloud billing accounts list                         # the Free Trial billing account
gcloud billing projects link "$PROJECT" --billing-account=<BILLING_ACCOUNT_ID>
gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com aiplatform.googleapis.com speech.googleapis.com \
  texttospeech.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com cloudbuild.googleapis.com
```

## 3. Budget alert (US$ 50)
Console: *Billing → Budgets & alerts → Create budget*. Scope: the project. Amount: **50** in the billing account's currency (if the account is in BRL, use the equivalent of US$ 50). Alerts at 50%, 90% and 100%, by e-mail to the account owner and the Tech Lead.
- **A budget only notifies, it does not cap spending.** The hard stop is the end of the trial credit.

## 4. Service accounts (least privilege)
One account for **deploy** (used by GitHub Actions), one for **runtime** (used by the Cloud Run services).

```bash
gcloud iam service-accounts create gh-deploy --display-name="GitHub deploy"
gcloud iam service-accounts create app-runtime --display-name="Cloud Run runtime"
DEPLOY=gh-deploy@$PROJECT.iam.gserviceaccount.com
RUNTIME=app-runtime@$PROJECT.iam.gserviceaccount.com

# deploy: push images and deploy to Cloud Run (run.admin also allows making a service public, which judges need)
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$DEPLOY" --role=roles/run.admin
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$DEPLOY" --role=roles/artifactregistry.writer
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME" --member="serviceAccount:$DEPLOY" --role=roles/iam.serviceAccountUser

# runtime: Gemini on Vertex AI and reading secrets
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$RUNTIME" --role=roles/aiplatform.user
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$RUNTIME" --role=roles/secretmanager.secretAccessor
```
Speech-to-Text and Text-to-Speech work with the APIs enabled and an authenticated service account. With **Speech v2**, also grant `roles/speech.client` to the runtime account. Check on the first call.

## 5. GitHub Actions without a JSON key (Workload Identity Federation)
No long-lived key exists, so there is nothing to leak.

```bash
gcloud iam workload-identity-pools create github --location=global --display-name="GitHub"
gcloud iam workload-identity-pools providers create-oidc github-repo --location=global \
  --workload-identity-pool=github --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='raviproenca/nether-field-shift-2026'"
POOL=$(gcloud iam workload-identity-pools describe github --location=global --format='value(name)')
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/$POOL/attribute.repository/raviproenca/nether-field-shift-2026"
gcloud iam workload-identity-pools providers describe github-repo --location=global \
  --workload-identity-pool=github --format='value(name)'   # -> GCP_WIF_PROVIDER
```

Repository **variables** (not secrets; no key is involved). Setting them needs repo admin (Tech Lead):
```bash
gh variable set GCP_PROJECT_ID  -R raviproenca/nether-field-shift-2026 --body "$PROJECT"
gh variable set GCP_WIF_PROVIDER -R raviproenca/nether-field-shift-2026 --body "<output of the last command>"
gh variable set GCP_DEPLOY_SA   -R raviproenca/nether-field-shift-2026 --body "$DEPLOY"
```

## 6. Application secrets (Secret Manager)
The Telegram bot token (from @BotFather) and, if the server needs Earthdata, its username and password. Type them in your own terminal only:
```bash
printf '%s' "<paste in your own terminal>" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-
```
Cloud Run reads secrets from Secret Manager; AI agents never see the values.

## Later (team, via CLI or GitHub Actions)
Create the Artifact Registry repository, build the images, and deploy the API, bot and voice services with `--service-account=$RUNTIME`, using `--allow-unauthenticated` only where judges need it. Pick the region: `southamerica-east1` (São Paulo) is suggested; Gemini Flash availability may require `us-central1`. Then set the Telegram webhook.
