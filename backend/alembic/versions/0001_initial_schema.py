"""Initial schema — all tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-27 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entra_oid", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_entra_oid", "users", ["entra_oid"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_institution_id", "users", ["institution_id"])

    # ── institutions ─────────────────────────────────────────────────────────
    op.create_table(
        "institutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("accreditor", sa.String(255), nullable=True),
        sa.Column("ipeds_id", sa.String(20), nullable=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("teams_webhook_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ipeds_id"),
    )
    op.create_index("ix_institutions_slug", "institutions", ["slug"], unique=True)

    # Add FK from users.institution_id → institutions.id
    op.create_foreign_key(
        "fk_users_institution_id",
        "users",
        "institutions",
        ["institution_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── programs ─────────────────────────────────────────────────────────────
    op.create_table(
        "programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("degree_type", sa.String(50), nullable=False),
        sa.Column("format", sa.String(20), nullable=False, server_default="online"),
        sa.Column("modality", sa.String(10), nullable=False, server_default="async"),
        sa.Column("tuition_per_credit", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_credits", sa.Integer(), nullable=True),
        sa.Column("term_calendar", sa.String(20), nullable=False, server_default="semester"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_programs_institution_id", "programs", ["institution_id"])

    # ── agents ───────────────────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("owner_team", sa.String(255), nullable=True),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_program_id", "agents", ["program_id"])

    # ── agent_versions ────────────────────────────────────────────────────────
    op.create_table(
        "agent_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "model_id", sa.String(100), nullable=False, server_default="claude-sonnet-4-5"
        ),
        sa.Column("tool_definitions", postgresql.JSONB(), nullable=True),
        sa.Column("knowledge_cutoff_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safety_config", postgresql.JSONB(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])

    # ── datasets ──────────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sme_owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("langfuse_dataset_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sme_owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_program_id", "datasets", ["program_id"])

    # ── production_traces ─────────────────────────────────────────────────────
    op.create_table(
        "production_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("langfuse_trace_id", sa.String(255), nullable=True),
        sa.Column("session_hash", sa.String(64), nullable=True),
        sa.Column(
            "ferpa_classification", sa.String(20), nullable=False, server_default="public"
        ),
        sa.Column("redacted_prompt", sa.Text(), nullable=True),
        sa.Column("redacted_response", sa.Text(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column(
            "safety_flags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_priority", sa.String(10), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agent_version_id"], ["agent_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("langfuse_trace_id"),
    )
    op.create_index(
        "ix_production_traces_agent_version_created",
        "production_traces",
        ["agent_version_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_production_traces_needs_review",
        "production_traces",
        ["needs_review", "created_at"],
        postgresql_where=sa.text("needs_review = true"),
    )
    op.create_index(
        "ix_production_traces_langfuse_trace_id",
        "production_traces",
        ["langfuse_trace_id"],
        unique=True,
    )

    # ── examples ──────────────────────────────────────────────────────────────
    op.create_table(
        "examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "expected_behaviors",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "prohibited_behaviors",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("persona", sa.String(30), nullable=True),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="medium"),
        sa.Column(
            "safety_tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_safety_tagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("langfuse_item_id", sa.String(255), nullable=True),
        sa.Column("promoted_from_trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["promoted_from_trace_id"], ["production_traces.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_examples_dataset_id", "examples", ["dataset_id"])

    # ── judges ────────────────────────────────────────────────────────────────
    op.create_table(
        "judges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("judge_type", sa.String(20), nullable=False, server_default="quality"),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_judges_slug", "judges", ["slug"], unique=True)

    # ── judge_versions ────────────────────────────────────────────────────────
    op.create_table(
        "judge_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("judge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "model_id", sa.String(100), nullable=False, server_default="claude-sonnet-4-5"
        ),
        sa.Column("rubric_prompt", sa.Text(), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), nullable=False),
        sa.Column("few_shot_examples", postgresql.JSONB(), nullable=True),
        sa.Column("pass_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewer_1_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_2_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["judge_id"], ["judges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_1_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_2_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_versions_judge_id", "judge_versions", ["judge_id"])

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column(
            "judge_version_ids",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("langfuse_run_id", sa.String(255), nullable=True),
        sa.Column("rq_job_id", sa.String(255), nullable=True),
        sa.Column("total_examples", sa.Integer(), nullable=True),
        sa.Column("passed_examples", sa.Integer(), nullable=True),
        sa.Column("pass_rate", sa.Float(), nullable=True),
        sa.Column("aggregate_scores", postgresql.JSONB(), nullable=True),
        sa.Column("total_cost_usd", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("triggered_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["agent_version_id"], ["agent_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["triggered_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_agent_version_id", "eval_runs", ["agent_version_id"])
    op.create_index("ix_eval_runs_dataset_id", "eval_runs", ["dataset_id"])

    # ── eval_results ──────────────────────────────────────────────────────────
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("example_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_response", sa.Text(), nullable=True),
        sa.Column("judge_scores", postgresql.JSONB(), nullable=True),
        sa.Column(
            "safety_flags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("langfuse_observation_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["example_id"], ["examples.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eval_results_run_passed",
        "eval_results",
        ["eval_run_id", "passed"],
    )
    op.create_index("ix_eval_results_example_id", "eval_results", ["example_id"])

    # ── annotations ───────────────────────────────────────────────────────────
    op.create_table(
        "annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_quality", sa.Integer(), nullable=True),
        sa.Column("dimension_scores", postgresql.JSONB(), nullable=True),
        sa.Column("safety_assessment", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("promoted_example_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trace_id"], ["production_traces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["promoted_example_id"], ["examples.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_annotations_trace_id", "annotations", ["trace_id"])
    op.create_index("ix_annotations_reviewer_id", "annotations", ["reviewer_id"])

    # ── review_queue_items ────────────────────────────────────────────────────
    op.create_table(
        "review_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["trace_id"], ["production_traces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id"),
    )
    op.create_index("ix_review_queue_items_trace_id", "review_queue_items", ["trace_id"])

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_entity_type_id", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_correlation_id", "audit_log", ["correlation_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("review_queue_items")
    op.drop_table("annotations")
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("judge_versions")
    op.drop_table("judges")
    op.drop_table("examples")
    op.drop_table("production_traces")
    op.drop_table("datasets")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("programs")
    op.drop_constraint("fk_users_institution_id", "users", type_="foreignkey")
    op.drop_table("institutions")
    op.drop_table("users")
