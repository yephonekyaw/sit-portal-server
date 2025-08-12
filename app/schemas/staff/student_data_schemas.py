from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class ParsedStudentRecord(BaseModel):
    id: str
    firstName: str
    lastName: str
    email: EmailStr
    studentId: str = Field(..., pattern="^[0-9]{11}$")
    programCode: str = Field(..., pattern="^(CS|DSI|IT)$")
    academicYear: str = Field(..., pattern="^[0-9]{4}$")
    sourceFile: Optional[str] = None


class ImportStudentsRequest(BaseModel):
    """Request schema for importing student records"""

    students: List[ParsedStudentRecord] = Field(
        ..., min_length=1, description="List of student records to import"
    )


class ImportStudentsResponse(BaseModel):
    """Response schema for student import results"""

    total_received: int = Field(..., description="Total number of records received")
    processed: int = Field(..., description="Number of records processed")
    created: int = Field(..., description="Number of new student records created")
    skipped: int = Field(
        ..., description="Number of records skipped (duplicates or errors)"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages if any"
    )
