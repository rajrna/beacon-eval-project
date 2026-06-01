"""
Load Harvard CS datasets into the database.
Run AFTER creating Harvard University and CS program through the frontend.

Usage:
  python load_harvard_datasets.py --program-id <your-program-uuid>

Or set HARVARD_PROGRAM_ID environment variable.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

DATASETS_DIR = Path(__file__).parent.parent / "datasets"
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

DATASET_CONFIGS = [
    ("CS Admissions Q&A", "admissions", "harvard_cs_admissions.jsonl"),
    ("CS Financial Aid", "finaid", "harvard_cs_finaid.jsonl"),
    ("CS Retention & Support", "retention", "harvard_cs_retention.jsonl"),
    ("CS Adversarial Examples", "safety", "harvard_cs_adversarial.jsonl"),
]


async def load(program_id: str) -> None:
    from beacon.core.settings import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text

    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        # Verify program exists
        result = await session.execute(
            text(f"SELECT name FROM programs WHERE id = '{program_id}'")
        )
        row = result.fetchone()
        if not row:
            print(f"ERROR: Program {program_id} not found. Create it in the frontend first.")
            return
        print(f"Loading datasets for program: {row[0]}")

        for ds_name, category, filename in DATASET_CONFIGS:
            # Check if dataset already exists
            existing = await session.execute(text(
                f"SELECT id FROM datasets WHERE program_id = '{program_id}' AND name = '{ds_name}'"
            ))
            existing_row = existing.fetchone()

            if existing_row:
                dataset_id = str(existing_row[0])
                print(f"  · Dataset exists: {ds_name} ({dataset_id[:8]}…)")
            else:
                # Create dataset
                dataset_id = str(uuid.uuid4())
                await session.execute(text("""
                    INSERT INTO datasets (id, program_id, name, category, sme_owner_id, version, created_at, updated_at)
                    VALUES (:id, :program_id, :name, :category, :sme_owner_id, 1, NOW(), NOW())
                """), {
                    "id": dataset_id,
                    "program_id": program_id,
                    "name": ds_name,
                    "category": category,
                    "sme_owner_id": DEV_USER_ID,
                })
                print(f"  ✓ Created dataset: {ds_name}")

            # Check example count
            count_result = await session.execute(text(
                f"SELECT COUNT(*) FROM examples WHERE dataset_id = '{dataset_id}'"
            ))
            count = count_result.scalar()
            if count > 0:
                print(f"    · Already has {count} examples, skipping")
                continue

            # Load examples from JSONL
            jsonl_path = DATASETS_DIR / filename
            if not jsonl_path.exists():
                print(f"    ✗ File not found: {jsonl_path}")
                continue

            inserted = 0
            for line in jsonl_path.read_text(encoding="utf-8").strip().splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                safety_tags = data.get("safety_tags", [])
                await session.execute(text("""
                    INSERT INTO examples (
                        id, dataset_id, query, expected_behaviors, prohibited_behaviors,
                        reference_answer, persona, difficulty, safety_tags,
                        is_safety_tagged, notes, external_id, created_by_id, created_at
                    ) VALUES (
                        :id, :dataset_id, :query, :expected_behaviors, :prohibited_behaviors,
                        :reference_answer, :persona, :difficulty, :safety_tags,
                        :is_safety_tagged, :notes, :external_id, :created_by_id, NOW()
                    )
                """), {
                    "id": str(uuid.uuid4()),
                    "dataset_id": dataset_id,
                    "query": data["query"],
                    "expected_behaviors": data.get("expected_behaviors", []),
                    "prohibited_behaviors": data.get("prohibited_behaviors", []),
                    "reference_answer": data.get("reference_answer"),
                    "persona": data.get("persona"),
                    "difficulty": data.get("difficulty", "medium"),
                    "safety_tags": safety_tags,
                    "is_safety_tagged": bool(safety_tags),
                    "notes": data.get("notes"),
                    "external_id": data.get("id"),
                    "created_by_id": DEV_USER_ID,
                })
                inserted += 1

            await session.commit()
            print(f"    ✓ {inserted} examples loaded from {filename}")

    await engine.dispose()
    print("\n✅ Harvard CS datasets loaded successfully.")
    print("Go to /datasets in the frontend to see them.")


if __name__ == "__main__":
    # Get program ID from args or env
    program_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--program-id":
        program_id = sys.argv[2]
    else:
        import os
        program_id = os.environ.get("HARVARD_PROGRAM_ID")

    if not program_id:
        print("Usage: python load_harvard_datasets.py --program-id <uuid>")
        print("   or: set HARVARD_PROGRAM_ID=<uuid> and run python load_harvard_datasets.py")
        print()
        print("Get your program ID from:")
        print("  http://localhost:8000/v1/programs?institution_id=<your-harvard-institution-id>")
        sys.exit(1)

    asyncio.run(load(program_id))
