# Beacon Databricks Notebooks

Analytics notebooks that run against Delta tables populated by the nightly export.

## Notebooks

| Notebook | Schedule | Description |
|---|---|---|
| `weekly_safety_report.py` | Monday 08:00 UTC | Safety flag trends, SLA compliance, FERPA breakdown |
| `agent_version_comparison.py` | On-demand | Pass rate and judge scores across agent versions |
| `sme_annotation_throughput.py` | Weekly | SME velocity, quality scores, promotion rates |
| `cost_attribution_by_program.py` | Weekly | Anthropic API spend by institution, program, agent |

## Delta table schema

The nightly export writes these Delta tables under `/mnt/beacon/delta/`:

```
production_traces/
eval_runs/
eval_results/
annotations/
review_queue_items/
agent_versions/
agents/
programs/
users/
weekly_safety_reports/     ← written by weekly_safety_report notebook
```

## Running locally (Databricks Connect)

```bash
pip install databricks-connect
databricks-connect configure
python notebooks/weekly_safety_report.py
```

## Import to Databricks workspace

Export format is Python (`.py`) with `# COMMAND ----------` cell separators —
compatible with Databricks notebook import directly.
