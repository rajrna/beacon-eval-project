from beacon.judges.base import BaseJudge


class CompletenessJudge(BaseJudge):
    slug = "completeness"
    name = "Completeness"
    description = "Scores whether the agent's response fully addresses the student's needs."
    is_safety_critical = False
    pass_threshold = 0.7

    rubric_template = """\
STUDENT QUERY:
{query}{persona_line}

AGENT RESPONSE:
{agent_response}

EXPECTED BEHAVIORS:
{expected_behaviors}

PROHIBITED BEHAVIORS:
{prohibited_behaviors}{reference_line}

COMPLETENESS RUBRIC:
Evaluate whether the response fully addresses everything the student asked and needs.

Consider:
1. Does the response directly answer the student's question?
2. Are all parts of a multi-part question addressed?
3. Does the response anticipate likely follow-up questions and address them proactively?
4. Are next steps or action items clear when relevant?
5. Does the response leave the student with actionable information?
6. Are there any important omissions that would leave the student confused or unable to proceed?

Score from 0.0 to 1.0:
  1.0 = Fully complete — addresses everything, proactively helpful
  0.7 = Mostly complete with minor omissions
  0.5 = Partially complete — answers the literal question but misses important context
  0.3 = Significantly incomplete — student would need to ask multiple follow-up questions
  0.0 = Does not answer the question at all or provides only irrelevant content

Respond ONLY with this JSON schema:
{schema}"""

    output_schema = {
        "score": "number (0.0-1.0)",
        "passed": "boolean",
        "reasoning": "string — 2-3 sentences explaining the score",
        "missing_elements": "array of strings — important information that was omitted (empty if none)",
        "flags": "array of strings — serious completeness issues (empty if none)",
    }
