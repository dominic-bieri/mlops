import uuid
from datetime import UTC, date, datetime, timedelta

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

    def get_latest_dates(self, tables: list[str]) -> dict[str, date | None]:
        # one query for all tables, saves a BigQuery job round trip per table
        selects = []
        for table in tables:
            table_id = self.get_table_id(table)
            selects.append(f"(SELECT MAX(date) FROM `{table_id}`) AS `{table}`")
        sql = "SELECT " + ", ".join(selects)

        query_job = self.client.query(sql)
        rows = list(query_job.result())
        row = rows[0]

        latest_dates = {}
        for table in tables:
            latest_dates[table] = row[table]
        return latest_dates

    def upsert(self, df: pd.DataFrame, table: str) -> None:
        if df.empty:
            return

        # MERGE fails on duplicate dates
        df = df.drop_duplicates(subset="date", keep="last")

        table_id = self.get_table_id(table)
        # unique name, so runs at the same time do not share a staging table
        staging_id = f"{table_id}_staging_{uuid.uuid4().hex}"

        target_table = self.client.get_table(table_id)
        staging_table = bigquery.Table(staging_id, schema=target_table.schema)
        # BigQuery deletes it by itself if this process is killed before the cleanup below
        staging_table.expires = datetime.now(UTC) + timedelta(hours=1)

        job_config = bigquery.LoadJobConfig(
            schema=target_table.schema,
            write_disposition="WRITE_APPEND",
        )
        merge_sql = build_merge_sql(table_id, staging_id, list(df.columns))

        try:
            self.client.create_table(staging_table)
            load_job = self.client.load_table_from_dataframe(df, staging_id, job_config=job_config)
            load_job.result()
            merge_job = self.client.query(merge_sql)
            merge_job.result()
        finally:
            self.client.delete_table(staging_id, not_found_ok=True)


def build_merge_sql(table_id: str, staging_id: str, columns: list[str]) -> str:
    quoted_columns = []
    updates = []
    for column in columns:
        quoted_columns.append(f"`{column}`")
        if column != "date":
            updates.append(f"`{column}` = S.`{column}`")

    column_list = ", ".join(quoted_columns)

    # with only a date column there is nothing to update, and an empty UPDATE SET is invalid
    matched_clause = ""
    if updates:
        update_list = ", ".join(updates)
        matched_clause = f"WHEN MATCHED THEN UPDATE SET {update_list}"

    return f"""
        MERGE `{table_id}` T
        USING `{staging_id}` S
        ON T.date = S.date
        {matched_clause}
        WHEN NOT MATCHED THEN INSERT ({column_list}) VALUES ({column_list})
    """
