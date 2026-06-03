"""
Base judge framework.
Every judge in Beacon follows this interface:
  - name, slug, is_safety_critical
  - rubric_prompt (rendered with example + response)
  - output_schema (validated JSON the LLM must return)
  - evaluate(example, agent_response) → JudgeResult
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from beacon.integrations.anthropic_client import complete_structured, estimate_cost

logger = structlog.get_logger(__name__)


@dataclass
class JudgeResult:
    judge_slug: str
    score: float          # 0.0 – 1.0
    passed: bool
    reasoning: str
    flags: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw_output: str = ""


JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator assessing AI agent responses in a higher-education context.
Your role is to score the agent's response against a provided rubric.

CRITICAL RULES:
- Respond ONLY with a valid JSON object matching the exact schema provided.
- No markdown fences, no preamble, no explanation outside the JSON.
- Be calibrated: reserve scores of 0.9+ for genuinely excellent responses.
- Be consistent: identical inputs should yield identical scores.
"""


class BaseJudge:
    slug: str = ""
    name: str = ""
    description: str = ""
    is_safety_critical: bool = False
    model_id: str | None = None   # None = use settings.bedrock_model_id
    pass_threshold: float = 0.7
    temperature: float = 0.0
    max_tokens: int = 512

    # Subclasses override these
    rubric_template: str = ""
    output_schema: dict[str, Any] = {}

    def _render_rubric(
        self,
        query: str,
        agent_response: str,
        expected_behaviors: list[str],
        prohibited_behaviors: list[str],
        persona: str | None = None,
        reference_answer: str | None = None,
    ) -> str:
        expected = "\n".join(f"  - {b}" for b in expected_behaviors) or "  (none specified)"
        prohibited = "\n".join(f"  - {b}" for b in prohibited_behaviors) or "  (none specified)"
        persona_line = f"\nStudent persona: {persona}" if persona else ""
        reference_line = f"\n\nREFERENCE ANSWER:\n{reference_answer}" if reference_answer else ""

        return self.rubric_template.format(
            query=query,
            agent_response=agent_response,
            expected_behaviors=expected,
            prohibited_behaviors=prohibited,
            persona_line=persona_line,
            reference_line=reference_line,
            schema=json.dumps(self.output_schema, indent=2),
        )

    async def evaluate(
        self,
        query: str,
        agent_response: str,
        expected_behaviors: list[str] | None = None,
        prohibited_behaviors: list[str] | None = None,
        persona: str | None = None,
        reference_answer: str | None = None,
    ) -> JudgeResult:
        prompt = self._render_rubric(
            query=query,
            agent_response=agent_response,
            expected_behaviors=expected_behaviors or [],
            prohibited_behaviors=prohibited_behaviors or [],
            persona=persona,
            reference_answer=reference_answer,
        )
        try:
            raw_text = await complete_structured(
                prompt=prompt,
                system=JUDGE_SYSTEM_PROMPT,
                model=self.model_id,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            # Strip markdown fences if model added them anyway
            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.strip()

            parsed = json.loads(clean)
            score = float(parsed.get("score", 0.0))

            return JudgeResult(
                judge_slug=self.slug,
                score=score,
                passed=score >= self.pass_threshold,
                reasoning=parsed.get("reasoning", ""),
                flags=parsed.get("flags", []),
                cost_usd=0.0,   # cost tracked at agent level; judge cost minor
                raw_output=raw_text,
            )
        except Exception as exc:
            logger.error(
                "judge_evaluate_failed",
                judge=self.slug,
                error=str(exc),
            )
            return JudgeResult(
                judge_slug=self.slug,
                score=0.0,
                passed=False,
                reasoning=f"Judge evaluation failed: {exc}",
                flags=["evaluation_error"],
            )

# """
# Base judge framework.
# Every judge in Beacon follows this interface:
#   - name, slug, is_safety_critical
#   - rubric_prompt (rendered with example + response)
#   - output_schema (validated JSON the LLM must return)
#   - evaluate(example, agent_response) → JudgeResult
# """
# from __future__ import annotations

# import json
# from dataclasses import dataclass, field
# from typing import Any

# import structlog

# from beacon.integrations.anthropic_client import get_client as get_anthropic_client

# logger = structlog.get_logger(__name__)


# @dataclass
# class JudgeResult:
#     judge_slug: str
#     score: float          # 0.0 – 1.0
#     passed: bool
#     reasoning: str
#     flags: list[str] = field(default_factory=list)
#     input_tokens: int = 0
#     output_tokens: int = 0
#     cost_usd: float = 0.0
#     raw_output: str = ""


# JUDGE_SYSTEM_PROMPT = """\
# You are an expert evaluator assessing AI agent responses in a higher-education context.
# Your role is to score the agent's response against a provided rubric.

# CRITICAL RULES:
# - Respond ONLY with a valid JSON object matching the exact schema provided.
# - No markdown fences, no preamble, no explanation outside the JSON.
# - Be calibrated: reserve scores of 0.9+ for genuinely excellent responses.
# - Be consistent: identical inputs should yield identical scores.
# """


# class BaseJudge:
#     slug: str = ""
#     name: str = ""
#     description: str = ""
#     is_safety_critical: bool = False
#     model_id: str = "claude-sonnet-4-5"
#     pass_threshold: float = 0.7
#     temperature: float = 0.0
#     max_tokens: int = 512

#     # Subclasses override these
#     rubric_template: str = ""
#     output_schema: dict[str, Any] = {}

#     def _render_rubric(
#         self,
#         query: str,
#         agent_response: str,
#         expected_behaviors: list[str],
#         prohibited_behaviors: list[str],
#         persona: str | None = None,
#         reference_answer: str | None = None,
#     ) -> str:
#         expected = "\n".join(f"  - {b}" for b in expected_behaviors) or "  (none specified)"
#         prohibited = "\n".join(f"  - {b}" for b in prohibited_behaviors) or "  (none specified)"
#         persona_line = f"\nStudent persona: {persona}" if persona else ""
#         reference_line = f"\n\nREFERENCE ANSWER:\n{reference_answer}" if reference_answer else ""

#         return self.rubric_template.format(
#             query=query,
#             agent_response=agent_response,
#             expected_behaviors=expected,
#             prohibited_behaviors=prohibited,
#             persona_line=persona_line,
#             reference_line=reference_line,
#             schema=json.dumps(self.output_schema, indent=2),
#         )

#     async def evaluate(
#         self,
#         query: str,
#         agent_response: str,
#         expected_behaviors: list[str] | None = None,
#         prohibited_behaviors: list[str] | None = None,
#         persona: str | None = None,
#         reference_answer: str | None = None,
#     ) -> JudgeResult:
#         prompt = self._render_rubric(
#             query=query,
#             agent_response=agent_response,
#             expected_behaviors=expected_behaviors or [],
#             prohibited_behaviors=prohibited_behaviors or [],
#             persona=persona,
#             reference_answer=reference_answer,
#         )
#         client = get_anthropic_client()
#         try:
#             result = await client.complete_structured(
#                 messages=[{"role": "user", "content": prompt}],
#                 system=JUDGE_SYSTEM_PROMPT,
#                 model=self.model_id,
#                 max_tokens=self.max_tokens,
#                 temperature=self.temperature,
#             )
#             parsed = result["parsed"]
#             score = float(parsed.get("score", 0.0))
#             return JudgeResult(
#                 judge_slug=self.slug,
#                 score=score,
#                 passed=score >= self.pass_threshold,
#                 reasoning=parsed.get("reasoning", ""),
#                 flags=parsed.get("flags", []),
#                 input_tokens=result["input_tokens"],
#                 output_tokens=result["output_tokens"],
#                 cost_usd=result["cost_usd"],
#                 raw_output=result["text"],
#             )
#         except Exception as exc:
#             logger.error(
#                 "judge_evaluate_failed",
#                 judge=self.slug,
#                 error=str(exc),
#             )
#             return JudgeResult(
#                 judge_slug=self.slug,
#                 score=0.0,
#                 passed=False,
#                 reasoning=f"Judge evaluation failed: {exc}",
#                 flags=["evaluation_error"],
#             )
