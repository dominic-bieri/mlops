# Terraform

Google Cloud resources for the project.

## Files

- `versions.tf`: provider and backend setup
- `variables.tf`: inputs (`project_id`, `region`, `dataset_id`)
- `apis.tf`: list of Google Cloud APIs to turn on
- `bigquery.tf`: BigQuery dataset and tables
- `outputs.tf`: outputs

One file per service. New service: new file + its API in `apis.tf`.

## State

State lives in a GCS bucket, shared across computers. Once per project:

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate \
  --project=YOUR_PROJECT_ID \
  --location=EU \
  --uniform-bucket-level-access \
  --public-access-prevention

gcloud storage buckets update gs://YOUR_PROJECT_ID-tfstate --versioning
```

## GitHub Actions (apply on `main`)

Push to `main` with changes in `terraform/` or the [workflow](../.github/workflows/terraform.yml) -> `terraform apply`.
Login via Workload Identity Federation, no key ([ADR 4](../docs/adr/0004-github-actions-gcp-auth.md)).

One-time setup by hand ([auth action guide](https://github.com/google-github-actions/auth#preferred-direct-workload-identity-federation)):

1. Look up repo ID and owner ID on GitHub
2. Turn on the needed APIs
3. Pool + provider: Google trusts GitHub tokens, only from this repo on `main`, only for `push`, `schedule`, `workflow_dispatch`
4. Give the GitHub environment `terraform` only the roles Terraform needs (no service account)
5. On GitHub: create environment `terraform` (*Settings -> Environments*), deployment branches: `main` only, variables see below

```bash
PROJECT_ID="YOUR_PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

REPO="dominic-bieri/mlops"
REPO_JSON=$(curl -fsS https://api.github.com/repos/$REPO)
REPO_ID=$(echo "$REPO_JSON" | jq -r .id)
OWNER_ID=$(echo "$REPO_JSON" | jq -r .owner.id)
echo "$REPO_ID $OWNER_ID"   # must be numbers

gcloud services enable iam.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com \
  --project=$PROJECT_ID

gcloud iam workload-identity-pools create "github" \
  --project=$PROJECT_ID --location="global" \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc "github" \
  --project=$PROJECT_ID --location="global" \
  --workload-identity-pool="github" \
  --display-name="GitHub" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repo_env=assertion.repository_id + '/' + (has(assertion.environment) ? assertion.environment : 'none')" \
  --attribute-condition="assertion.repository_id == '$REPO_ID' && assertion.repository_owner_id == '$OWNER_ID' && assertion.ref == 'refs/heads/main' && assertion.event_name in ['push', 'schedule', 'workflow_dispatch']"

# only jobs in this repo with `environment: terraform`
TF_PRINCIPAL="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repo_env/$REPO_ID/terraform"

# apis.tf, bigquery.tf
for ROLE in roles/serviceusage.serviceUsageAdmin roles/bigquery.admin; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="$TF_PRINCIPAL" \
    --role="$ROLE" \
    --condition=None
done

# state bucket only
gcloud storage buckets add-iam-policy-binding gs://$PROJECT_ID-tfstate \
  --member="$TF_PRINCIPAL" \
  --role="roles/storage.objectAdmin"
```

New service in Terraform: add its role here.

Actions logs are public: mark secret values `sensitive = true`, so `plan` doesn't print them.

IAM changes take up to 5 minutes.

Environment variables (*Settings -> Environments -> terraform -> Environment variables*), only the `apply` job sees them:

| Name | Value |
|---|---|
| `GCP_PROJECT_ID` | `YOUR_PROJECT_ID` |
| `GCP_TFSTATE_BUCKET` | `YOUR_PROJECT_ID-tfstate` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github` |

## Local usage

```bash
cp terraform.tfvars.example terraform.tfvars
# set project_id in terraform.tfvars

gcloud auth application-default login

terraform init -backend-config="bucket=YOUR_PROJECT_ID-tfstate"
terraform plan
terraform apply
```

Second computer: same `init` command.
