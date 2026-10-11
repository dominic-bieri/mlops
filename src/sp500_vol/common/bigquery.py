from datetime import date

import pandas as pd
from google.cloud import bigquery

from sp500_vol.common.config import get_bq_dataset, get_gcp_project_id


class BigQueryClient:
    def __init__(self) -> None:
        self.project = get_gcp_project_id()
        self.dataset = get_bq_dataset()
        self.client = bigquery.Client(project=self.project)

    def get_table_id(self, table: str) -> str:
        return f"{self.project}.{self.dataset}.{table}"

    def get_latest_date(self, table: str) -> date | None:
        table_id = self.get_table_id(table)
        sql = f"SELECT MAX(date) AS latest FROM `{table_id}`"

        rows = list(self.client.query(sql).result())
        return rows[0]["latest"]

    def read_table(self, table: str) -> pd.DataFrame:
        table_id = self.get_table_id(table)
        sql = f"SELECT * FROM `{table_id}`"

        return self.client.query(sql).to_dataframe()

    def replace_from(self, df: pd.DataFrame, table: str, start: date) -> None:
        # empty fetch would only delete
        if df.empty:
            return

        table_id = self.get_table_id(table)

        delete_sql = f"DELETE FROM `{table_id}` WHERE date >= '{start.isoformat()}'"
        self.client.query(delete_sql).result()

        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
        self.client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    def replace_all(self, df: pd.DataFrame, table: str) -> None:
        # empty result would wipe the table
        if df.empty:
            return

        table_id = self.get_table_id(table)

        # keeps schema from Terraform
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE_DATA")
        self.client.load_table_from_dataframe(df, table_id, job_config=job_config).result()
