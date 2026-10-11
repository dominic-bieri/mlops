# 4. GitHub Actions login to Google Cloud

## Context

Terraform should `apply` on its own after a merge to `main`.
Later the pipeline workflows also need Google Cloud.
The repository is public.

## Decision

- Workload Identity Federation, direct: no key, no service account
- Google only accepts tokens from this repo (by ID), on `main`, from `push`, `schedule` or `workflow_dispatch`
- Roles go to the GitHub environment `terraform`, not the whole repo, only the ones Terraform needs
- No `plan` on pull requests, no `pull_request_target` workflows

## Consequences

- No secret to rotate or leak
- One-time manual setup (see `terraform/README.md`)
- Whoever can push to `main` can change the project, so `main` needs branch protection
- Pipeline workflows later get their own environment and roles
- New service in Terraform needs a new role
- Cloud Run doesn't support direct access, it will need a service account
