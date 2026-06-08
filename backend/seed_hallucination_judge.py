"""
Add the Hallucination Detection judge to the database.
Run once after deploying the new judge file.

Usage:
  python seed_hallucination_judge.py
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone


async def seed():
    from beacon.core.settings import get_settings
    from beacon.judges.hallucination_detection import HallucinationDetectionJudge
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text

    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Get rubric and schema from the judge class itself
    judge_cls = HallucinationDetectionJudge()

    async with factory() as session:
        # Check if judge already exists
        existing = await session.execute(
            text("SELECT id FROM judges WHERE slug = 'hallucination_detection'")
        )
        row = existing.fetchone()

        if row:
            judge_id = str(row[0])
            print(f"· Judge already exists: hallucination_detection ({judge_id[:8]}…)")
        else:
            judge_id = str(uuid.uuid4())
            await session.execute(text("""
                INSERT INTO judges (id, slug, name, description, is_safety_critical, created_at, updated_at)
                VALUES (:id, :slug, :name, :description, :is_safety_critical, :now, :now)
            """), {
                "id": judge_id,
                "slug": "hallucination_detection",
                "name": "Hallucination Detection",
                "description": "Detects fabricated or unverifiable factual claims — especially specific statistics, dollar amounts, deadlines, and named programs. Critical for enrollment and financial aid agents.",
                "is_safety_critical": True,
                "now": datetime.now(timezone.utc),
            })
            print(f"✓ Created judge: hallucination_detection ({judge_id[:8]}…)")

        # Check if judge version already exists
        existing_v = await session.execute(
            text("SELECT id FROM judge_versions WHERE judge_id = :judge_id AND version_number = 1"),
            {"judge_id": judge_id},
        )
        v_row = existing_v.fetchone()

        if v_row:
            print(f"· Judge version 1 already exists ({str(v_row[0])[:8]}…)")
        else:
            version_id = str(uuid.uuid4())
            await session.execute(text("""
                INSERT INTO judge_versions (
                    id, judge_id, version_number, model_id, rubric_prompt,
                    output_schema, pass_threshold, temperature,
                    is_locked, is_approved, created_at, created_by_id
                )
                VALUES (
                    :id, :judge_id, 1, :model_id, :rubric_prompt,
                    :output_schema, :pass_threshold, :temperature,
                    false, false, :now, :created_by_id
                )
            """), {
                "id": version_id,
                "judge_id": judge_id,
                "model_id": settings.bedrock_model_id,
                "rubric_prompt": judge_cls.rubric_template,
                "output_schema": json.dumps(judge_cls.output_schema),
                "pass_threshold": judge_cls.pass_threshold,
                "temperature": judge_cls.temperature,
                "now": datetime.now(timezone.utc),
                "created_by_id": "00000000-0000-0000-0000-000000000001",
            })
            print(f"✓ Created judge version 1 ({version_id[:8]}…)")

        await session.commit()

    await engine.dispose()
    print("\n✅ Hallucination Detection judge ready.")
    print("Go to /judges in the frontend to see it.")
    print("Include 'hallucination_detection' when triggering eval runs.")


if __name__ == "__main__":
    asyncio.run(seed())