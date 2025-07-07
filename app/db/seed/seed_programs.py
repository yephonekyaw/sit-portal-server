import uuid
from sqlalchemy.orm import Session
from ..models import (
    Program,
)
from app.utils.logging import get_logger

logger = get_logger()


def seed_programs(db_session: Session):
    programs_data = [
        {
            "id": uuid.uuid4(),
            "program_code": "CS",
            "program_name": "Computer Science",
            "description": "A comprehensive program focusing on computer science fundamentals, software development, algorithms, data structures, and computational theory. Students will learn programming languages, software engineering principles, database systems, and emerging technologies.",
            "is_active": True,
        },
        {
            "id": uuid.uuid4(),
            "program_code": "DSI",
            "program_name": "Digital Service Innovation",
            "description": "An innovative program that combines technology, design thinking, and business strategy to create digital solutions for real-world problems. Students will learn about user experience design, digital transformation, service design, and innovation management.",
            "is_active": True,
        },
        {
            "id": uuid.uuid4(),
            "program_code": "IT",
            "program_name": "Information Technology",
            "description": "A practical program focused on the application of technology in business environments. Students will learn about network administration, cybersecurity, system integration, IT project management, and enterprise technology solutions.",
            "is_active": True,
        },
    ]

    # Check if programs already exist to avoid duplicates
    existing_codes = {
        p.program_code for p in db_session.query(Program.program_code).all()
    }

    programs_to_add = []
    for program_data in programs_data:
        if program_data["program_code"] not in existing_codes:
            program = Program(**program_data)
            programs_to_add.append(program)

    if programs_to_add:
        db_session.add_all(programs_to_add)
        logger.info(f"Successfully seeded {len(programs_to_add)} programs")
    else:
        logger.info("No new programs to seed")
