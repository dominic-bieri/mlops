# Terraform

Google Cloud resources: APIs (`apis.tf`), BigQuery (`bigquery.tf`) and the model bucket (`storage.tf`).
New service: new file, add its API to `apis.tf`.

One-time setup first: [`docs/google-cloud.md`](../docs/google-cloud.md).

## Run

On push to `main`, [GitHub Actions](../.github/workflows/terraform.yml) runs `terraform apply`.

Local:

```bash
cp terraform.tfvars.example terraform.tfvars   # set project_id and model_region
gcloud auth application-default login

terraform init -backend-config="bucket=YOUR_PROJECT_ID-tfstate"
terraform apply
```
