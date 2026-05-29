# Databricks notebook source
# SME Annotation Throughput
# Tracks annotation velocity, quality, and promotion rates by reviewer.

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import datetime, timedelta

WINDOW_DAYS = 30
REPORT_START = datetime.utcnow() - timedelta(days=WINDOW_DAYS)
print(f"SME throughput report: last {WINDOW_DAYS} days")

# COMMAND ----------

annotations_df = spark.read.format("delta").load("/mnt/beacon/delta/annotations") \
    .filter(F.col("created_at") >= REPORT_START)

users_df = spark.read.format("delta").load("/mnt/beacon/delta/users")

# COMMAND ----------
# DBTITLE 1,Annotations per SME

throughput = annotations_df \
    .join(users_df.select("id", "display_name", "email"), annotations_df.reviewer_id == users_df.id) \
    .groupBy("reviewer_id", "display_name") \
    .agg(
        F.count("*").alias("total_annotations"),
        F.avg("overall_quality").alias("avg_quality_score"),
        F.sum(F.when(F.col("promoted_example_id").isNotNull(), 1).otherwise(0)).alias("promotions"),
        F.min("created_at").alias("first_annotation"),
        F.max("created_at").alias("last_annotation"),
    ) \
    .withColumn("promotion_rate", F.col("promotions") / F.col("total_annotations")) \
    .orderBy(F.col("total_annotations").desc())

print("=== SME Annotation Throughput ===")
throughput.show(truncate=False)

# COMMAND ----------
# DBTITLE 1,Daily annotation volume

daily_volume = annotations_df \
    .withColumn("date", F.to_date("created_at")) \
    .groupBy("date") \
    .agg(F.count("*").alias("annotations")) \
    .orderBy("date")

print("=== Daily Annotation Volume ===")
daily_volume.show(40, truncate=False)

# COMMAND ----------
# DBTITLE 1,Quality score distribution

quality_dist = annotations_df \
    .filter(F.col("overall_quality").isNotNull()) \
    .groupBy("overall_quality") \
    .agg(F.count("*").alias("count")) \
    .orderBy("overall_quality")

print("=== Quality Score Distribution (1-5) ===")
quality_dist.show()

# COMMAND ----------
# DBTITLE 1,Promotions to golden set

promotions = annotations_df \
    .filter(F.col("promoted_example_id").isNotNull()) \
    .join(users_df.select("id", "display_name"), annotations_df.reviewer_id == users_df.id) \
    .groupBy("display_name") \
    .agg(F.count("*").alias("golden_promotions")) \
    .orderBy(F.col("golden_promotions").desc())

print("=== Golden Set Promotions by SME ===")
promotions.show()

# COMMAND ----------
# DBTITLE 1,Weekly pace vs target (50 traces/week)

TARGET_PER_WEEK = 50

weekly = annotations_df \
    .withColumn("week", F.date_trunc("week", F.col("created_at"))) \
    .groupBy("week") \
    .agg(F.count("*").alias("annotations")) \
    .withColumn("vs_target", F.col("annotations") - TARGET_PER_WEEK) \
    .orderBy("week")

print(f"=== Weekly Annotations vs Target ({TARGET_PER_WEEK}/week) ===")
weekly.show(truncate=False)
