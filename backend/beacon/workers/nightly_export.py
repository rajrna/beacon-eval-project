"""
Nightly Databricks Export Worker.
Runs at 02:00 UTC. Queries Postgres for new rows since last watermark,
writes Parquet files to Azure Blob, updates watermark.
Databricks Auto Loader picks up new files and writes to Delta tables.
"""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

WATERMARK_BLOB = "exports/watermark.json"
TABLES_TO_EXPORT = [
    "production_traces",
    "eval_results",
    "eval_runs",
    "annotations",
    "review_queue_items",
    "agent_versions",
    "agents",
    "programs",
    "users",
]


def run_nightly_export() -> None:
    """Synchronous RQ job entrypoint."""
    asyncio.run(_run_export_async())


async def _run_export_async() -> None:
    from beacon.core.settings import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    settings = get_settings()
    engine = create_async_engine(settings.database_url_str, echo=False)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        await _export_tables(session)

    await engine.dispose()


async def _export_tables(session) -> None:
    from beacon.core.settings import get_settings
    settings = get_settings()

    # Read watermark
    watermark = await _read_watermark(settings)
    last_exported = watermark.get("last_exported_at", "1970-01-01T00:00:00Z")
    export_start = datetime.now(timezone.utc)

    logger.info("nightly_export_start", since=last_exported)

    exported_tables = []
    for table_name in TABLES_TO_EXPORT:
        try:
            count = await _export_table(session, table_name, last_exported, settings)
            exported_tables.append({"table": table_name, "rows": count})
            logger.info("table_exported", table=table_name, rows=count)
        except Exception as exc:
            logger.error("table_export_failed", table=table_name, error=str(exc))

    # Update watermark
    await _write_watermark(settings, {
        "last_exported_at": export_start.isoformat(),
        "tables": exported_tables,
    })

    total_rows = sum(t["rows"] for t in exported_tables)
    logger.info("nightly_export_complete", total_rows=total_rows, tables=len(exported_tables))


async def _export_table(session, table_name: str, since: str, settings) -> int:
    """Export new rows from a table to Parquet on Azure Blob."""
    from sqlalchemy import text
    import io

    query = text(f"""
        SELECT * FROM {table_name}
        WHERE created_at > :since
        ORDER BY created_at
    """)
    result = await session.execute(query, {"since": since})
    rows = result.mappings().all()

    if not rows:
        return 0

    # Convert to Parquet via pandas (available in Databricks runtime)
    try:
        import pandas as pd
        df = pd.DataFrame([dict(row) for row in rows])

        # Convert UUID and datetime columns to strings for Parquet compatibility
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str)

        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)

        # Upload to Azure Blob
        date_str = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        blob_path = f"exports/{table_name}/{date_str}/{table_name}_{datetime.now(timezone.utc).strftime('%H%M%S')}.parquet"

        await _upload_to_blob(settings, blob_path, parquet_buffer.read())
        return len(rows)
    except ImportError:
        logger.warning("pandas_not_available_skipping_parquet", table=table_name)
        return 0


async def _read_watermark(settings) -> dict:
    try:
        from azure.storage.blob.aio import BlobServiceClient
        async with BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        ) as client:
            blob = client.get_blob_client("exports", WATERMARK_BLOB)
            data = await blob.download_blob()
            content = await data.readall()
            return json.loads(content)
    except Exception:
        return {}


async def _write_watermark(settings, data: dict) -> None:
    try:
        from azure.storage.blob.aio import BlobServiceClient
        async with BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        ) as client:
            blob = client.get_blob_client("exports", WATERMARK_BLOB)
            await blob.upload_blob(json.dumps(data), overwrite=True)
    except Exception as exc:
        logger.warning("watermark_write_failed", error=str(exc))


async def _upload_to_blob(settings, blob_path: str, data: bytes) -> None:
    from azure.storage.blob.aio import BlobServiceClient
    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as client:
        blob = client.get_blob_client("exports", blob_path)
        await blob.upload_blob(data, overwrite=True)
