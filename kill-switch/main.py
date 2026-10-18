import base64
import json
import os

import functions_framework
from google.cloud import billing_v1


@functions_framework.cloud_event
def stop_billing(cloud_event) -> None:
    data = base64.b64decode(cloud_event.data["message"]["data"])
    budget = json.loads(data)
    cost = budget["costAmount"]
    limit = budget["budgetAmount"]
    print(f"cost {cost}, budget {limit}")

    if cost <= limit:
        return

    project_name = "projects/" + os.environ["GCP_PROJECT_ID"]
    if os.environ["DRY_RUN"] == "true":
        print(f"dry run, would stop billing for {project_name}")
        return

    # empty billing account = billing off
    info = billing_v1.ProjectBillingInfo(billing_account_name="")
    client = billing_v1.CloudBillingClient()
    client.update_project_billing_info(name=project_name, project_billing_info=info)
    print(f"billing stopped for {project_name}")
