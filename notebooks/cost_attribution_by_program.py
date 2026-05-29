# Databricks notebook source
# Cost Attribution by Program
# Breaks down Anthropic API spend by institution, program, and agent.

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import datetime, timedelta

dbutils.widgets.text("days", "30", "Lookback days")
DAYS = int(dbutils.widgets.get("days"))
REPORT_START = datetime.utcnow() - timedelta(days=DAYS)

# COMMAND ----------

eval_results_df = spark.read.format("delta").load("/mnt/beacon/delta/eval_results") \
    .filter(F.col("created_at") >= REPORT_START)

eval_runs_df = spark.read.format("delta").load("/mnt/beacon/delta/eval_runs")
agent_versions_df = spark.read.format("delta").load("/mnt/beacon/delta/agent_versions")
agents_df = spark.read.format("delta").load("/mnt/beacon/delta/agents")
programs_df = spark.read.format("delta").load("/mnt/beacon/delta/programs")

# COMMAND ----------
# DBTITLE 1,Cost by program

cost_by_program = eval_results_df \
    .join(eval_runs_df.select("id", "agent_version_id"), eval_results_df.eval_run_id == eval_runs_df.id) \
    .join(agent_versions_df.select("id", "agent_id"), F.col("agent_version_id") == agent_versions_df.id) \
    .join(agents_df.select("id", "program_id", "name"), F.col("agent_id") == agents_df.id) \
    .join(programs_df.select("id", "name"), agents_df.program_id == programs_df.id) \
    .groupBy(programs_df.name.alias("program")) \
    .agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.count("*").alias("eval_results"),
        F.avg("cost_usd").alias("avg_cost_per_result"),
    ) \
    .orderBy(F.col("total_cost_usd").desc())

print(f"=== Cost by Program (last {DAYS} days) ===")
cost_by_program.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,Cost by agent

cost_by_agent = eval_results_df \
    .join(eval_runs_df.select("id", "agent_version_id"), eval_results_df.eval_run_id == eval_runs_df.id) \
    .join(agent_versions_df.select("id", "agent_id"), F.col("agent_version_id") == agent_versions_df.id) \
    .join(agents_df.select("id", "name"), F.col("agent_id") == agents_df.id) \
    .groupBy(agents_df.name.alias("agent")) \
    .agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.count("*").alias("eval_results"),
    ) \
    .orderBy(F.col("total_cost_usd").desc())

print("=== Cost by Agent ===")
cost_by_agent.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,Daily cost trend

daily_cost = eval_results_df \
    .withColumn("date", F.to_date("created_at")) \
    .groupBy("date") \
    .agg(F.sum("cost_usd").alias("daily_cost_usd")) \
    .orderBy("date")

total = eval_results_df.agg(F.sum("cost_usd")).collect()[0][0] or 0
print(f"Total cost last {DAYS} days: ${total:.4f}")
print("=== Daily Cost Trend ===")
daily_cost.show(40, truncate=False)
