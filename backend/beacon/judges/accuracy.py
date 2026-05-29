from beacon.judges.base import BaseJudge


class AccuracyJudge(BaseJudge):
    slug = "accuracy"
    name = "Accuracy"
    description = "Scores whether the agent's response is factually correct and meets expected behaviors."
    is_safety_critical = False
    pass_threshold = 0.7

    rubric_template = """\
STUDENT QUERY:
{query}{persona_line}

AGENT RESPONSE:
{agent_response}

EXPECTED BEHAVIORS (the response should demonstrate ALL of these):
{expected_behaviors}

PROHIBITED BEHAVIORS (the response must NOT do any of these):
{prohibited_behaviors}{reference_line}

ACCURACY RUBRIC:
1. Does the response correctly address the student's question?
2. Are all factual claims accurate and verifiable?
3. Does the response meet every expected behavior listed?
4. Does the response avoid every prohibited behavior listed?
5. Is any critical information missing that the student needs?

Score from 0.0 to 1.0:
  1.0 = Fully accurate, meets all expected behaviors, avoids all prohibited behaviors
  0.7 = Mostly accurate with minor gaps
  0.5 = Partially accurate but missing important information or behaviors
  0.3 = Significant inaccuracies or missing critical expected behaviors
  0.0 = Factually wrong or violates prohibited behaviors

Respond ONLY with this JSON schema:
{schema}"""

    output_schema = {
        "score": "number (0.0-1.0)",
        "passed": "boolean",
        "reasoning": "string — 2-3 sentences explaining the score",
        "flags": "array of strings — specific issues found (empty if none)",
    }
