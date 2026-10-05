# Terraform

This sets up the Google Cloud resources for the project.

## Files

- `versions.tf` — provider and backend setup
- `variables.tf` — inputs (`project_id`, `region`, `dataset_id`)
- `apis.tf` — list of Google Cloud APIs to turn on
- `bigquery.tf` — BigQuery dataset and tables
- `outputs.tf` — outputs

One file per service. New service → new file, and add its API to `apis.tf`.

## State

State is stored remotely in a GCS bucket (not locally), so it's shared across computers. One-time setup, only needed once per project:

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate \
  --project=YOUR_PROJECT_ID \
  --location=EU \
  --uniform-bucket-level-access
```

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
# set your project_id in terraform.tfvars

gcloud auth application-default login

terraform init -backend-config="bucket=YOUR_PROJECT_ID-tfstate"
terraform plan
terraform apply
```

On a second computer, just run the same `init` command with the same bucket name to use the shared state.
