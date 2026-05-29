# Beacon Datasets

Golden example datasets for evaluating student-facing AI agents.
Each file is JSONL — one JSON object per line, validated against `_schema/example.schema.json`.

## Files

| File | Program | Category | Examples |
|---|---|---|---|
| `westbrook_mba_tuition.jsonl` | Westbrook Online MBA | tuition | 5 |
| `westbrook_mba_admissions.jsonl` | Westbrook Online MBA | admissions | 5 |
| `westbrook_mba_retention.jsonl` | Westbrook Online MBA | retention | 5 |
| `westbrook_mba_adversarial.jsonl` | Westbrook Online MBA | adversarial | 5 |

## Schema

Each example has these fields:

```json
{
  "id": "optional-stable-id",
  "query": "The student query text",
  "expected_behaviors": ["List of behaviors the agent MUST demonstrate"],
  "prohibited_behaviors": ["List of behaviors the agent must NOT exhibit"],
  "reference_answer": null,
  "persona": "adult_learner | first_gen | military | international | struggling | traditional | null",
  "difficulty": "easy | medium | hard | adversarial",
  "safety_tags": ["mental_health", "crisis_referral", "ferpa", "academic_integrity", ...],
  "notes": "Optional notes for SME reviewers"
}
```

## Adding examples

1. Add to the appropriate JSONL file (one JSON object per line, no trailing comma)
2. Run validation: `make validate-datasets`
3. If adding safety-tagged examples, assign an SME as required reviewer on the PR
4. Safety-tagged examples require SME sign-off before merging

## CI validation

The `nightly-dataset-validation` workflow validates all JSONL files against the schema nightly
and on every PR that touches `datasets/`.
