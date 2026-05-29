# Databricks notebook source
# Weekly Safety Report
# Reads from Delta tables populated by the nightly Beacon export.
# Run: scheduled weekly on Mondays at 08:00 UTC

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import datetime, timedelta

# Report window: last 7 days
REPORT_END = datetime.utcnow()
REPORT_START = REPORT_END - timedelta(days=7)
print(f"Safety report: {REPORT_START.date()} → {REPORT_END.date()}")

# COMMAND ----------
# DBTITLE 1,Load Delta tables

traces_df = spark.read.format("delta").load("/mnt/beacon/delta/production_traces") \
    .filter(F.col("created_at").between(REPORT_START, REPORT_END))

annotations_df = spark.read.format("delta").load("/mnt/beacon/delta/annotations") \
    .filter(F.col("created_at").between(REPORT_START, REPORT_END))

queue_df = spark.read.format("delta").load("/mnt/beacon/delta/review_queue_items") \
    .filter(F.col("created_at").between(REPORT_START, REPORT_END))

# COMMAND ----------
# DBTITLE 1,Safety flag summary

safety_summary = traces_df \
    .withColumn("flag", F.explode_outer(F.col("safety_flags"))) \
    .groupBy("flag") \
    .agg(F.count("*").alias("count")) \
    .orderBy(F.col("count").desc())

print("=== Safety Flags This Week ===")
safety_summary.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,Crisis trace volume and SLA compliance

crisis_df = queue_df.filter(F.col("priority") == "crisis")
total_crisis = crisis_df.count()
acked_within_sla = crisis_df.filter(
    F.col("acknowledged_at").isNotNull() &
    (F.col("acknowledged_at") <= F.col("sla_deadline"))
).count()

sla_compliance = acked_within_sla / total_crisis if total_crisis > 0 else 1.0
print(f"=== Crisis Trace SLA Compliance ===")
print(f"Total crisis traces:  {total_crisis}")
print(f"Acknowledged on time: {acked_within_sla}")
print(f"SLA compliance:       {sla_compliance:.1%}")

if sla_compliance < 1.0:
    print(f"⚠️  {total_crisis - acked_within_sla} crisis trace(s) breached the 15-minute SLA")

# COMMAND ----------
# DBTITLE 1,Safety flag trend by day

daily_flags = traces_df \
    .withColumn("date", F.to_date("created_at")) \
    .withColumn("has_flag", F.when(F.size(F.col("safety_flags")) > 0, 1).otherwise(0)) \
    .groupBy("date") \
    .agg(
        F.count("*").alias("total_traces"),
        F.sum("has_flag").alias("flagged_traces"),
    ) \
    .withColumn("flag_rate", F.col("flagged_traces") / F.col("total_traces")) \
    .orderBy("date")

print("=== Daily Safety Flag Rate ===")
daily_flags.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,FERPA classification breakdown

ferpa_breakdown = traces_df \
    .groupBy("ferpa_classification") \
    .agg(F.count("*").alias("count")) \
    .orderBy("ferpa_classification")

print("=== FERPA Classification Breakdown ===")
ferpa_breakdown.show()

# COMMAND ----------
# DBTITLE 1,Annotation safety assessments

safety_assessments = annotations_df \
    .filter(F.col("safety_assessment").isNotNull()) \
    .groupBy("safety_assessment") \
    .agg(F.count("*").alias("count")) \
    .orderBy(F.col("count").desc())

print("=== SME Safety Assessments ===")
safety_assessments.show()

# COMMAND ----------
# DBTITLE 1,Write report summary to Delta

report_row = spark.createDataFrame([{
    "report_date": REPORT_END.date().isoformat(),
    "total_traces": traces_df.count(),
    "flagged_traces": traces_df.filter(F.size(F.col("safety_flags")) > 0).count(),
    "crisis_traces": total_crisis,
    "sla_compliance_rate": sla_compliance,
    "generated_at": datetime.utcnow().isoformat(),
}])

report_row.write.format("delta") \
    .mode("append") \
    .save("/mnt/beacon/delta/weekly_safety_reports")

print("✅ Report written to Delta")
