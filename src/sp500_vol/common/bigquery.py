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

    def read_table(self, table: str) -> pd.DataFrame:
        table_id = self.get_table_id(table)
        sql = f"SELECT * FROM `{table_id}`"

        return self.client.query(sql).to_dataframe()

    def get_dates(self, table: str) -> set[date]:
        table_id = self.get_table_id(table)
        sql = f"SELECT date FROM `{table_id}`"

        return {row["date"] for row in self.client.query(sql).result()}

    def append(self, df: pd.DataFrame, table: str) -> None:
        if df.empty:
            return

        table_id = self.get_table_id(table)
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
