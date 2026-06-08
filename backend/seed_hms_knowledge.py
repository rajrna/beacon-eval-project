"""
Seed HMS knowledge base with real facts.
Run after creating the Harvard MD program and creating the knowledge table.

Usage:
  python seed_hms_knowledge.py --program-id <uuid>
"""
from datetime import date
import asyncio
import sys
import uuid


HMS_KNOWLEDGE = [
    # Admissions
    {"category": "admissions", "key": "avg_mcat_matriculants", "value": "522.2", "display_label": "Average MCAT (matriculants)", "last_verified": "2024-09-01", "source_url": "https://hms.harvard.edu/admissions"},
    {"category": "admissions", "key": "avg_gpa_matriculants", "value": "3.9", "display_label": "Average GPA (matriculants)", "last_verified": "2024-09-01"},
    {"category": "admissions", "key": "class_size", "value": "Approximately 165 students per year", "display_label": "Class Size"},
    {"category": "admissions", "key": "acceptance_rate", "value": "Approximately 3-4%", "display_label": "Acceptance Rate"},
    {"category": "admissions", "key": "application_system", "value": "AMCAS (American Medical College Application Service)", "display_label": "Application System"},
    {"category": "admissions", "key": "interview_format", "value": "Multiple Mini Interview (MMI) and traditional panel interviews", "display_label": "Interview Format"},
    {"category": "admissions", "key": "holistic_review", "value": "HMS uses a holistic review process — GPA and MCAT are considered alongside research experience, clinical exposure, community service, and personal qualities", "display_label": "Review Process"},

    # Requirements
    {"category": "requirements", "key": "required_courses", "value": "Biology (1 year), General Chemistry (1 year), Organic Chemistry (1 year), Physics (1 year), Mathematics/Statistics (1 semester), Biochemistry (1 semester)", "display_label": "Required Prerequisite Courses"},
    {"category": "requirements", "key": "mcat_requirement", "value": "Required — no minimum score published; average matriculant score is 522.2", "display_label": "MCAT Requirement"},
    {"category": "requirements", "key": "research_experience", "value": "Strongly recommended — most matriculants have significant research experience", "display_label": "Research Experience"},
    {"category": "requirements", "key": "clinical_experience", "value": "Required — direct patient contact experience is expected", "display_label": "Clinical Experience"},
    {"category": "requirements", "key": "letters_of_recommendation", "value": "Minimum 3 letters required — at least one from a science faculty member", "display_label": "Letters of Recommendation"},
    {"category": "requirements", "key": "degree_requirement", "value": "Bachelor's degree required before matriculation", "display_label": "Degree Requirement"},

    # Deadlines
    {"category": "deadlines", "key": "amcas_deadline", "value": "October 15 (primary application) — submit early as HMS reviews on a rolling basis", "display_label": "AMCAS Primary Deadline"},
    {"category": "deadlines", "key": "secondary_deadline", "value": "Typically 2-3 weeks after receiving secondary application invitation", "display_label": "Secondary Application Deadline"},
    {"category": "deadlines", "key": "interview_season", "value": "October through February", "display_label": "Interview Season"},
    {"category": "deadlines", "key": "decision_date", "value": "March 15 (Acceptance Day per AAMC guidelines)", "display_label": "Earliest Acceptance Notification"},

    # Tuition
    {"category": "tuition", "key": "annual_tuition", "value": "Approximately $67,500 per year (2024-2025) — verify current figures at hms.harvard.edu/financial-aid", "display_label": "Annual Tuition", "last_verified": "2024-09-01", "source_url": "https://hms.harvard.edu/financial-aid"},
    {"category": "tuition", "key": "total_cost_of_attendance", "value": "Approximately $102,000-$110,000 per year including tuition, fees, housing, and living expenses", "display_label": "Total Cost of Attendance"},
    {"category": "tuition", "key": "program_length", "value": "4 years (MD degree)", "display_label": "Program Length"},
    {"category": "tuition", "key": "total_program_cost", "value": "Approximately $400,000-$440,000 total over 4 years before financial aid", "display_label": "Total Program Cost (estimate)"},

    # Financial Aid
    {"category": "financial_aid", "key": "need_based_aid", "value": "HMS meets 100% of demonstrated financial need for all admitted students", "display_label": "Need-Based Aid Policy"},
    {"category": "financial_aid", "key": "average_grant", "value": "Approximately $45,000-$50,000 per year in grants for eligible students", "display_label": "Average Annual Grant"},
    {"category": "financial_aid", "key": "loan_assistance", "value": "HMS Loan Repayment Assistance Program (LRAP) available for graduates in qualifying careers", "display_label": "Loan Repayment Assistance"},
    {"category": "financial_aid", "key": "no_loan_policy", "value": "HMS has a no-loan policy for families with incomes below $100,000 — aid provided entirely as grants", "display_label": "No-Loan Policy (low income)"},
    {"category": "financial_aid", "key": "financial_aid_contact", "value": "HMS Financial Aid Office: finaid@hms.harvard.edu | (617) 432-1575", "display_label": "Financial Aid Contact"},

    # Policies
    {"category": "policies", "key": "leave_of_absence", "value": "Medical and personal leaves of absence available — contact the Dean of Students office", "display_label": "Leave of Absence"},
    {"category": "policies", "key": "step1_policy", "value": "USMLE Step 1 must be passed before clinical rotations — retakes permitted per USMLE guidelines", "display_label": "USMLE Step 1 Policy"},
    {"category": "policies", "key": "academic_support", "value": "Office of Student Affairs provides academic coaching, tutoring, and remediation support", "display_label": "Academic Support"},
    {"category": "policies", "key": "mental_health", "value": "HMS Student Mental Health: (617) 495-2042 — confidential counseling available", "display_label": "Mental Health Services"},
    {"category": "policies", "key": "disability_services", "value": "Accommodations available through HMS Disability Services — contact early in the process", "display_label": "Disability Services"},

    # Clinical
    {"category": "clinical", "key": "clinical_start", "value": "Core clinical clerkships begin in Year 3 at affiliated teaching hospitals", "display_label": "Clinical Training Start"},
    {"category": "clinical", "key": "affiliated_hospitals", "value": "Massachusetts General Hospital, Brigham and Women's Hospital, Boston Children's Hospital, Beth Israel Deaconess Medical Center, and others", "display_label": "Primary Affiliated Hospitals"},
    {"category": "clinical", "key": "curriculum_name", "value": "Pathways curriculum — integrated science and clinical training from Year 1", "display_label": "Curriculum"},

    # Career
    {"category": "career", "key": "match_rate", "value": "Virtually 100% match rate into residency programs", "display_label": "Residency Match Rate"},
    {"category": "career", "key": "top_specialties", "value": "Internal Medicine, Surgery, Psychiatry, Pediatrics, Radiology, Anesthesiology — HMS graduates match into all specialties", "display_label": "Common Specialties"},
    {"category": "career", "key": "career_advising", "value": "HMS Academic Societies provide mentorship and career advising throughout the program", "display_label": "Career Advising"},
]


async def seed(program_id: str) -> None:
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
            print(f"ERROR: Program {program_id} not found.")
            return
        print(f"Seeding knowledge for: {row[0]}\n")

        inserted = 0
        updated = 0

        for entry in HMS_KNOWLEDGE:
            existing = await session.execute(text(
                "SELECT id FROM program_knowledge WHERE program_id = :pid AND key = :key"
            ), {"pid": program_id, "key": entry["key"]})
            existing_row = existing.fetchone()

            if existing_row:
                await session.execute(text("""
                    UPDATE program_knowledge
                    SET value = :value,
                        display_label = :display_label,
                        last_verified = :last_verified,
                        source_url = :source_url,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": str(existing_row[0]),
                    "value": entry["value"],
                    "display_label": entry.get("display_label"),
                    "last_verified": date.fromisoformat(entry["last_verified"]) if entry.get("last_verified") else None,
                    "source_url": entry.get("source_url"),
                })
                updated += 1
            else:
                await session.execute(text("""
                    INSERT INTO program_knowledge (
                        id, program_id, category, key, value,
                        display_label, last_verified, source_url,
                        is_active, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :program_id, :category, :key, :value,
                        :display_label, :last_verified, :source_url,
                        true, NOW(), NOW()
                    )
                """), {
                    "program_id": program_id,
                    "category": entry["category"],
                    "key": entry["key"],
                    "value": entry["value"],
                    "display_label": entry.get("display_label"),
                    "last_verified": date.fromisoformat(entry["last_verified"]) if entry.get("last_verified") else None,
                    "source_url": entry.get("source_url"),
                })
                inserted += 1

        await session.commit()
        print(f"✓ {inserted} entries inserted, {updated} updated")

    await engine.dispose()
    print(f"\n✅ HMS knowledge base seeded ({len(HMS_KNOWLEDGE)} facts across 7 categories).")
    print("Preview the prompt block at:")
    print(f"  GET /v1/programs/{program_id}/knowledge/prompt-block")


if __name__ == "__main__":
    program_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--program-id":
        program_id = sys.argv[2]
    else:
        import os
        program_id = os.environ.get("HARVARD_MD_PROGRAM_ID")

    if not program_id:
        print("Usage: python seed_hms_knowledge.py --program-id <uuid>")
        sys.exit(1)

    asyncio.run(seed(program_id))
