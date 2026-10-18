# Kill switch

Turns off billing for the project above 5 CHF per month. Optional.
Everything in the project stops, and costs show up hours late.

budget -> Pub/Sub topic -> function -> unlinks the billing account

[Google guide](https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications), [roles](https://docs.cloud.google.com/billing/docs/how-to/modify-project#disable_billing_for_a_project)

## 1. Variables

```bash
PROJECT_ID="YOUR_PROJECT_ID"
BILLING_ACCOUNT=$(gcloud billing projects describe $PROJECT_ID --format="value(billingAccountName)" | cut -d/ -f2)
REGION="europe-west6"
SA="billing-kill-switch@$PROJECT_ID.iam.gserviceaccount.com"
```

## 2. APIs, topic, service account

```bash
gcloud services enable billingbudgets.googleapis.com cloudbilling.googleapis.com \
  cloudfunctions.googleapis.com cloudbuild.googleapis.com eventarc.googleapis.com \
  run.googleapis.com pubsub.googleapis.com artifactregistry.googleapis.com \
  --project=$PROJECT_ID

gcloud pubsub topics create billing-kill-switch --project=$PROJECT_ID

gcloud iam service-accounts create billing-kill-switch --project=$PROJECT_ID
for ROLE in roles/billing.projectManager roles/browser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" --role="$ROLE" --condition=None
done
gcloud billing accounts add-iam-policy-binding $BILLING_ACCOUNT \
  --member="serviceAccount:$SA" --role="roles/billing.viewer"
```

## 3. Function

`DRY_RUN=true`: only logs, doesn't stop billing.

```bash
DRY_RUN=true

# from the repo root
gcloud functions deploy billing-kill-switch --gen2 --runtime=python314 --region=$REGION \
  --source=kill-switch --entry-point=stop_billing --trigger-topic=billing-kill-switch \
  --service-account=$SA --trigger-service-account=$SA \
  --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,DRY_RUN=$DRY_RUN --project=$PROJECT_ID

gcloud run services add-iam-policy-binding billing-kill-switch --region=$REGION \
  --member="serviceAccount:$SA" --role=roles/run.invoker --project=$PROJECT_ID
```

## 4. Budget

```bash
gcloud billing budgets create --billing-account=$BILLING_ACCOUNT --billing-project=$PROJECT_ID \
  --display-name="kill switch $PROJECT_ID" --budget-amount=5CHF \
  --filter-projects=projects/$PROJECT_ID \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0 \
  --notifications-rule-pubsub-topic=projects/$PROJECT_ID/topics/billing-kill-switch
```

## 5. Test

Log should say `dry run, would stop billing`:

```bash
gcloud pubsub topics publish billing-kill-switch --project=$PROJECT_ID \
  --message='{"costAmount": 15, "budgetAmount": 10}'
gcloud functions logs read billing-kill-switch --region=$REGION --project=$PROJECT_ID
```

## 6. Turn on

Drop the test messages, then run the deploy from step 3 with `DRY_RUN=false`:

```bash
SUB=$(gcloud pubsub topics list-subscriptions billing-kill-switch --project=$PROJECT_ID --format="value(.)")
gcloud pubsub subscriptions seek $SUB --time=$(date -u +%Y-%m-%dT%H:%M:%SZ) --project=$PROJECT_ID
```

## After a stop

Link the billing account again under *Billing*.
