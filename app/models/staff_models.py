from typing import Optional
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
