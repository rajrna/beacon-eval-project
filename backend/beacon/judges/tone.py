from beacon.judges.base import BaseJudge


class ToneJudge(BaseJudge):
    slug = "tone"
    name = "Tone-Appropriate"
    description = "Scores whether the agent's tone is appropriate for the student persona and context."
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
{prohibited_behaviors}

TONE RUBRIC:
Evaluate whether the agent's tone is appropriate for a student-facing higher-education context.

Consider:
1. Is the tone warm, professional, and empathetic?
2. Is the language accessible for the student's likely background?
   - adult_learner: practical, respects their time and experience
   - first_gen: encouraging, avoids jargon, explains processes clearly
   - military: direct, respectful, acknowledges service
   - international: clear, avoids idioms, culturally neutral
   - struggling: extra empathy, non-judgmental, supportive
   - traditional: friendly and engaging without being condescending
3. Does the response avoid being dismissive, robotic, or overly formal?
4. Does the response avoid being inappropriately casual or unprofessional?
5. Is the length appropriate — not too brief to seem unhelpful, not too long to overwhelm?

Score from 0.0 to 1.0:
  1.0 = Perfect tone for the persona and context
  0.7 = Generally appropriate with minor issues
  0.5 = Noticeable tone problems but not harmful
  0.3 = Significantly off-tone (too cold, too casual, or dismissive)
  0.0 = Actively harmful tone (condescending, dismissive of distress, etc.)

Respond ONLY with this JSON schema:
{schema}"""

    output_schema = {
        "score": "number (0.0-1.0)",
        "passed": "boolean",
        "reasoning": "string — 2-3 sentences explaining the score",
        "tone_issues": "array of strings — specific tone problems found (empty if none)",
        "flags": "array of strings — serious tone flags (empty if none)",
    }
