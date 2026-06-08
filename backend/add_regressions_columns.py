"""
Add is_regression and baseline_version_id columns to eval_runs.
Run once before deploying the regression service.

Usage:
  python add_regression_columns.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


async def migrate():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        # Add is_regression column
        try:
            await s.execute(text(
                "ALTER TABLE eval_runs ADD COLUMN is_regression BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("✓ Added is_regression column")
        except Exception as e:
            if "already exists" in str(e):
                print("· is_regression column already exists")
            else:
                raise

        # Add baseline_version_id column
        try:
            await s.execute(text(
                "ALTER TABLE eval_runs ADD COLUMN baseline_version_id UUID REFERENCES agent_versions(id)"
            ))
            print("✓ Added baseline_version_id column")
        except Exception as e:
            if "already exists" in str(e):
                print("· baseline_version_id column already exists")
            else:
                raise

        await s.commit()
    await engine.dispose()
    print("\n✅ Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())