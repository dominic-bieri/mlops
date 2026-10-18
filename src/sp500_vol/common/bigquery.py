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

        # REST is enough for small tables, no Storage API warning
        return self.client.query(sql).to_dataframe(create_bqstorage_client=False)

    def get_dates(self, table: str) -> set[date]:
        table_id = self.get_table_id(table)
        sql = f"SELECT date FROM `{table_id}`"

        dates = set()
        for row in self.client.query(sql).result():
            dates.add(row["date"])
        return dates

    def append(self, df: pd.DataFrame, table: str) -> None:
        self.load(df, table, "WRITE_APPEND")

    def replace_all(self, df: pd.DataFrame, table: str) -> None:
        # keeps schema from Terraform
        self.load(df, table, "WRITE_TRUNCATE_DATA")

    # read-only copy (ADR 2)
    def create_snapshot(self, table: str, snapshot: str, description: str) -> None:
        table_id = self.get_table_id(table)
        snapshot_id = self.get_table_id(snapshot)
        sql = (
            f"CREATE SNAPSHOT TABLE `{snapshot_id}` CLONE `{table_id}` "
            f"OPTIONS (description = '{description}')"
        )

        self.client.query(sql).result()

    def get_latest_snapshot(self, prefix: str) -> str:
        dataset_id = f"{self.project}.{self.dataset}"

        names = []
        for table in self.client.list_tables(dataset_id):
            if table.table_type == "SNAPSHOT" and table.table_id.startswith(prefix):
                names.append(table.table_id)
        return max(names)

    def load(self, df: pd.DataFrame, table: str, write_disposition: str) -> None:
        # empty replace would wipe the table
        if df.empty:
            return

        table_id = self.get_table_id(table)
        job_config = bigquery.LoadJobConfig(write_disposition=write_disposition)
        self.client.load_table_from_dataframe(df, table_id, job_config=job_config).result()
