# Databricks notebook source
# Agent Version Comparison
# Compare eval run results across agent versions for a given agent.

# COMMAND ----------

# Parameters — set these in a Databricks job or widget
dbutils.widgets.text("agent_id", "", "Agent ID (UUID)")
AGENT_ID = dbutils.widgets.get("agent_id")

if not AGENT_ID:
    raise ValueError("agent_id parameter is required")

print(f"Comparing versions for agent: {AGENT_ID}")

# COMMAND ----------

from pyspark.sql import functions as F

eval_runs_df = spark.read.format("delta").load("/mnt/beacon/delta/eval_runs")
eval_results_df = spark.read.format("delta").load("/mnt/beacon/delta/eval_results")
agent_versions_df = spark.read.format("delta").load("/mnt/beacon/delta/agent_versions") \
    .filter(F.col("agent_id") == AGENT_ID)

# COMMAND ----------
# DBTITLE 1,Pass rate by version

version_comparison = eval_runs_df \
    .join(agent_versions_df, eval_runs_df.agent_version_id == agent_versions_df.id) \
    .filter(eval_runs_df.status == "succeeded") \
    .groupBy("agent_version_id", "version_number") \
    .agg(
        F.avg("pass_rate").alias("avg_pass_rate"),
        F.avg("total_cost_usd").alias("avg_cost_usd"),
        F.avg("total_latency_ms").alias("avg_latency_ms"),
        F.count("*").alias("run_count"),
        F.max("created_at").alias("last_run_at"),
    ) \
    .orderBy("version_number")

print("=== Pass Rate by Agent Version ===")
version_comparison.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,Per-judge score comparison

from pyspark.sql.types import MapType, FloatType, StringType

# Explode judge_scores JSONB column
judge_scores_df = eval_results_df \
    .join(eval_runs_df.select("id", "agent_version_id"), eval_results_df.eval_run_id == eval_runs_df.id) \
    .join(agent_versions_df.select("id", "version_number"), F.col("agent_version_id") == agent_versions_df.id) \
    .select("version_number", "judge_scores") \
    .withColumn("judge_entry", F.explode(F.from_json(F.col("judge_scores"), MapType(StringType(), MapType(StringType(), StringType()))))) \
    .select("version_number", F.col("judge_entry._1").alias("judge_slug"), F.col("judge_entry._2.score").cast("float").alias("score"))

judge_comparison = judge_scores_df \
    .groupBy("version_number", "judge_slug") \
    .agg(F.avg("score").alias("avg_score"), F.count("*").alias("example_count")) \
    .orderBy("version_number", "judge_slug")

print("=== Per-Judge Score by Version ===")
judge_comparison.show(50, truncate=False)

# COMMAND ----------
# DBTITLE 1,Cost and latency trend

cost_trend = eval_runs_df \
    .join(agent_versions_df, eval_runs_df.agent_version_id == agent_versions_df.id) \
    .filter(eval_runs_df.status == "succeeded") \
    .select("version_number", "total_cost_usd", "total_latency_ms", "created_at") \
    .orderBy("created_at")

print("=== Cost & Latency by Run ===")
cost_trend.show(truncate=False)
