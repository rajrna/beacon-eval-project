"""
Seed HMS student life knowledge entries.
Run after the main HMS knowledge seeder.

Usage:
  python seed_hms_student_life.py --program-id <uuid>
"""
import asyncio
import sys
from datetime import date


HMS_STUDENT_LIFE = [
    # Housing
    {"category": "general", "key": "housing_options", "value": "HMS does not guarantee housing but maintains a list of approved off-campus housing options near the Longwood Medical Area. Most students live in the Fenway, Mission Hill, Jamaica Plain, or Brookline neighborhoods. Average rent ranges from $1,500-$2,500/month for a single bedroom.", "display_label": "Housing Options"},
    {"category": "general", "key": "vanderbilt_hall", "value": "Vanderbilt Hall is the on-campus residence located steps from HMS. It offers furnished single rooms and is highly competitive. Priority is given to first-year students. Amenities include a gym, study rooms, and communal kitchens.", "display_label": "Vanderbilt Hall (On-Campus Residence)"},
    {"category": "general", "key": "housing_cost", "value": "On-campus housing at Vanderbilt Hall costs approximately $1,200-$1,500/month. Off-campus options near Longwood range from $1,500-$2,800/month depending on size and location.", "display_label": "Housing Costs"},

    # Wellness
    {"category": "general", "key": "student_wellness", "value": "HMS Student Wellness offers free confidential counseling, psychiatry, and wellness coaching. Students can self-refer or be referred by a physician. Same-day crisis appointments are available.", "display_label": "Student Wellness Services"},
    {"category": "general", "key": "mental_health_services", "value": "HMS Student Mental Health: (617) 495-2042. Services include individual therapy, group therapy, psychiatry, and crisis support. All services are confidential and free for enrolled students.", "display_label": "Mental Health Services Contact"},
    {"category": "general", "key": "wellness_programs", "value": "HMS offers mindfulness meditation classes, yoga, resilience workshops, and peer support programs through the Wellness Office. The HAVEN peer counseling program connects students with trained peers for informal support.", "display_label": "Wellness Programs"},
    {"category": "general", "key": "fitness_facilities", "value": "Students have access to the Malkin Athletic Center (MAC) at Harvard, offering a gym, pool, tennis courts, and group fitness classes. The MAC is a short shuttle ride from the medical campus.", "display_label": "Fitness & Recreation"},

    # Academic societies
    {"category": "general", "key": "academic_societies", "value": "All HMS students are assigned to one of five Academic Societies: Castle, Cannon, Holmes, Peabody, or London. Each society has dedicated faculty advisors, mentors, and hosts social and academic events. Societies provide community and longitudinal mentorship throughout all four years.", "display_label": "Academic Societies"},
    {"category": "general", "key": "society_advisors", "value": "Each Academic Society has a dedicated faculty advisor who meets regularly with students, provides career guidance, writes letters of recommendation, and advocates for students throughout their HMS career.", "display_label": "Faculty Advisors through Societies"},

    # Student organizations
    {"category": "general", "key": "student_organizations", "value": "HMS has over 100 student organizations covering medical specialties, cultural groups, community service, research, and advocacy. Notable groups include the Student National Medical Association (SNMA), Latino Medical Student Association (LMSA), and specialty interest groups for every major field.", "display_label": "Student Organizations"},
    {"category": "general", "key": "community_service", "value": "HMS students run student-staffed free clinics serving underserved Boston communities including the Student Run Free Clinic at Boston Health Care for the Homeless Program. Over 80% of HMS students participate in community service during their training.", "display_label": "Community Service Opportunities"},
    {"category": "general", "key": "student_government", "value": "The HMS Student Council represents student interests to administration, allocates student activity funds, and organizes campus-wide events. All students are encouraged to participate.", "display_label": "Student Government"},

    # Diversity and inclusion
    {"category": "general", "key": "diversity_inclusion", "value": "HMS is committed to building a diverse physician workforce. The Office for Diversity Inclusion and Community Partnership (DICP) provides resources, mentorship, and support for underrepresented students including URM students, first-generation students, LGBTQ+ students, and students with disabilities.", "display_label": "Diversity & Inclusion Office"},
    {"category": "general", "key": "lgbtq_resources", "value": "HMS has an active LGBTQ+ Medical Student Group and dedicated resources through the DICP office. Harvard University's Office of BGLTQ Student Life also serves medical students. HMS is consistently ranked among the most LGBTQ-friendly medical schools.", "display_label": "LGBTQ+ Resources"},
    {"category": "general", "key": "first_gen_support", "value": "First-generation and low-income students are supported through the First Generation Harvard Student group, dedicated financial advising, and peer mentorship programs. HMS actively recruits and retains first-generation physicians.", "display_label": "First-Generation Student Support"},

    # Social life
    {"category": "general", "key": "boston_location", "value": "HMS is located in Boston's Longwood Medical Area, steps from Fenway Park, the Museum of Fine Arts, and dozens of restaurants and cafes. Boston offers world-class culture, sports, outdoor activities, and easy access to Cape Cod, the White Mountains, and New York City.", "display_label": "Boston Location & Lifestyle"},
    {"category": "general", "key": "student_events", "value": "HMS hosts an active social calendar including the annual HMS Talent Show, Spring Formal, HMS Olympics (inter-society competition), cultural celebrations, and weekly society events. First-year orientation includes social bonding activities to build class community.", "display_label": "Student Events & Social Life"},
    {"category": "general", "key": "student_lounge", "value": "The Gordon Hall student lounge provides a central gathering space with comfortable seating, lockers, and informal meeting areas. Each Academic Society also has a dedicated lounge space.", "display_label": "Student Lounges & Spaces"},

    # Food and campus
    {"category": "general", "key": "dining_options", "value": "The Longwood Galleria food court is steps from HMS with multiple dining options. The HMS campus has several cafes including the Gordon Hall Cafe. The Fenway neighborhood offers dozens of restaurants within walking distance.", "display_label": "Dining Options"},
    {"category": "general", "key": "campus_location", "value": "HMS is located at 25 Shattuck Street, Boston, MA 02115 in the Longwood Medical Area — a 200-acre biomedical research hub shared with Dana-Farber, Brigham and Women's, Boston Children's Hospital, and Beth Israel Deaconess Medical Center.", "display_label": "Campus Location"},
    {"category": "general", "key": "transportation", "value": "HMS is accessible via the MBTA Green Line (Longwood or Fenway stops) and multiple bus routes. Harvard provides a free shuttle connecting the medical campus to Harvard Yard. Most students do not need a car.", "display_label": "Transportation"},

    # Support services
    {"category": "general", "key": "disability_services", "value": "Students with disabilities are supported through the HMS Disability Services office. Accommodations are available for academic work and USMLE exams. Students should contact the office early to arrange appropriate support.", "display_label": "Disability Services"},
    {"category": "general", "key": "international_student_support", "value": "The Harvard International Office (HIO) supports international students with visa requirements, employment authorization, and cultural adjustment. HMS also has a dedicated international student advisor.", "display_label": "International Student Support"},
    {"category": "general", "key": "ombudsperson", "value": "The HMS Ombudsperson provides confidential, informal, impartial, and independent conflict resolution for students. Students can discuss any concern — academic, professional, or interpersonal — without formal reporting obligations.", "display_label": "Ombudsperson (Confidential Conflict Resolution)"},

    # Curriculum and schedule
    {"category": "general", "key": "curriculum_overview", "value": "The Pathways curriculum integrates basic science and clinical training from the start. Year 1-2 focus on foundational sciences and early clinical exposure. Year 3-4 are primarily clinical rotations across HMS-affiliated hospitals.", "display_label": "Curriculum Overview"},
    {"category": "general", "key": "grading_system", "value": "HMS uses a pass/fail grading system for preclinical years. Clinical rotations use an Honors/High Pass/Pass/Fail system. This is designed to foster collaboration over competition among students.", "display_label": "Grading System"},
    {"category": "general", "key": "research_opportunities", "value": "HMS students have unparalleled access to research through affiliated hospitals, Harvard T.H. Chan School of Public Health, and the Broad Institute. A dedicated research year (5th year) is available. Over 70% of HMS students engage in research during their training.", "display_label": "Research Opportunities"},
    {"category": "general", "key": "leave_of_absence_process", "value": "Students may take a leave of absence for medical, personal, research, or professional reasons. The Dean of Students office manages leaves. Financial aid may be affected depending on timing — consult the financial aid office before taking a leave.", "display_label": "Leave of Absence Process"},
]


async def seed(program_id: str) -> None:
    from beacon.core.settings import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text

    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        result = await session.execute(
            text(f"SELECT name FROM programs WHERE id = '{program_id}'")
        )
        row = result.fetchone()
        if not row:
            print(f"ERROR: Program {program_id} not found.")
            return
        print(f"Seeding student life knowledge for: {row[0]}\n")

        inserted = 0
        updated = 0

        for entry in HMS_STUDENT_LIFE:
            existing = await session.execute(text(
                "SELECT id FROM program_knowledge WHERE program_id = :pid AND key = :key"
            ), {"pid": program_id, "key": entry["key"]})
            existing_row = existing.fetchone()

            if existing_row:
                await session.execute(text("""
                    UPDATE program_knowledge
                    SET value = :value,
                        display_label = :display_label,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": str(existing_row[0]),
                    "value": entry["value"],
                    "display_label": entry.get("display_label"),
                })
                updated += 1
            else:
                await session.execute(text("""
                    INSERT INTO program_knowledge (
                        id, program_id, category, key, value,
                        display_label, is_active, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :program_id, :category, :key, :value,
                        :display_label, true, NOW(), NOW()
                    )
                """), {
                    "program_id": program_id,
                    "category": entry["category"],
                    "key": entry["key"],
                    "value": entry["value"],
                    "display_label": entry.get("display_label"),
                })
                inserted += 1

        await session.commit()
        print(f"✓ {inserted} entries inserted, {updated} updated")
        print(f"\nTotal student life entries: {len(HMS_STUDENT_LIFE)}")
        print("Categories: housing, wellness, societies, orgs, diversity, social, campus, support, curriculum")

    await engine.dispose()
    print(f"\n✅ HMS student life knowledge seeded.")
    print("Run backfill_embeddings.py to generate embeddings for the new entries.")


if __name__ == "__main__":
    program_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--program-id":
        program_id = sys.argv[2]
    else:
        import os
        program_id = os.environ.get("HARVARD_MD_PROGRAM_ID")

    if not program_id:
        print("Usage: python seed_hms_student_life.py --program-id <uuid>")
        sys.exit(1)

    asyncio.run(seed(program_id))