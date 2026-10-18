# Google Cloud setup

One-time setup by hand. Everything else is in [Terraform](../terraform/README.md).

GitHub Actions log in via Workload Identity Federation, no key ([ADR 4](adr/0004-github-actions-gcp-auth.md)).
One GitHub environment per workflow, each with only its own roles.

## State bucket

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate \
  --project=YOUR_PROJECT_ID \
  --location=EU \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://YOUR_PROJECT_ID-tfstate --versioning
```

## Pool and provider

Once for all environments ([guide](https://github.com/google-github-actions/auth#preferred-direct-workload-identity-federation)):

```bash
PROJECT_ID="YOUR_PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

REPO_JSON=$(curl -fsS https://api.github.com/repos/dominic-bieri/mlops)
REPO_ID=$(echo "$REPO_JSON" | jq -r .id)
OWNER_ID=$(echo "$REPO_JSON" | jq -r .owner.id)

gcloud services enable iam.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com \
  --project=$PROJECT_ID

gcloud iam workload-identity-pools create "github" \
  --project=$PROJECT_ID --location="global" \
  --display-name="GitHub Actions"

# only this repo, only `main`, only push/schedule/manual
gcloud iam workload-identity-pools providers create-oidc "github" \
  --project=$PROJECT_ID --location="global" \
  --workload-identity-pool="github" \
  --display-name="GitHub" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repo_env=assertion.repository_id + '/' + (has(assertion.environment) ? assertion.environment : 'none')" \
  --attribute-condition="assertion.repository_id == '$REPO_ID' && assertion.repository_owner_id == '$OWNER_ID' && assertion.ref == 'refs/heads/main' && assertion.event_name in ['push', 'schedule', 'workflow_dispatch']"

# used below
PRINCIPAL="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repo_env/$REPO_ID"
```

## Environment `terraform`

Needs `PROJECT_ID` and `PRINCIPAL` from above.

```bash
for ROLE in roles/serviceusage.serviceUsageAdmin roles/bigquery.admin; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="$PRINCIPAL/terraform" --role="$ROLE" --condition=None
done

gcloud storage buckets add-iam-policy-binding gs://$PROJECT_ID-tfstate \
  --member="$PRINCIPAL/terraform" --role="roles/storage.objectAdmin"
```

| Name | Type | Value |
|---|---|---|
| `GCP_PROJECT_ID` | variable | `YOUR_PROJECT_ID` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | variable | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github` |
| `GCP_TFSTATE_BUCKET` | variable | `YOUR_PROJECT_ID-tfstate` |

## Environment `feature-pipeline`

Needs `PROJECT_ID` and `PRINCIPAL` from above.

```bash
for ROLE in roles/bigquery.jobUser roles/bigquery.dataEditor; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="$PRINCIPAL/feature-pipeline" --role="$ROLE" --condition=None
done
```

| Name | Type | Value |
|---|---|---|
| `GCP_PROJECT_ID` | variable | `YOUR_PROJECT_ID` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | variable | same as `terraform` |
| `FRED_API_KEY` | secret | your FRED key |
| `TIINGO_API_KEY` | secret | your Tiingo key |

## Cost limit

Optional, not needed to run the repo.
Stops billing above 5 CHF per month: [`kill-switch/`](../kill-switch/README.md).

## Notes

- GitHub environments: *Settings -> Environments*, deployment branches `main` only
- IAM changes take up to 5 minutes
- Actions logs are public, mark secret Terraform values `sensitive = true`
