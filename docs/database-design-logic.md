# Database Design Logic: Programs, Certificates, Requirements & Schedules

This document explains the relationship between four key tables that handle certificate submission requirements for university students. The design accounts for long-term requirements with yearly deadline variations.

## Overview of the Relationship

```
Programs → ProgramRequirements → ProgramRequirementSchedules → CertificateSubmissions
    ↓              ↓                      ↓
CertificateTypes   AcademicYears        Students
```

## Detailed Explanation with Examples

### 1. PROGRAMS TABLE
- Contains all degree programs offered by the faculty
- Examples: 
  * `CS-BACHELOR` (Computer Science Bachelor's)
  * `CS-MASTER` (Computer Science Master's) 
  * `IT-BACHELOR` (Information Technology Bachelor's)
  * `IT-MASTER`, `CS-PHD`, `IT-PHD`
- These programs are relatively stable and rarely change

### 2. CERTIFICATE_TYPES TABLE  
- Defines all types of certificates the system handles
- Examples:
  * `CITI` (Collaborative Institutional Training Initiative)
  * `ETHICS` (Research Ethics Certificate)
  * `SAFETY` (Lab Safety Certificate)
- Independent of programs - certificates exist regardless of which program requires them

### 3. PROGRAM_REQUIREMENTS TABLE (The Connection Layer)
- Links programs to certificate types with specific timing rules
- Contains the "business rules" for when students need to submit certificates
- Key fields explained:
  * `program_id`: Which program this requirement applies to
  * `cert_type_id`: Which certificate type is required
  * `name`: Descriptive name for the requirement (e.g., "3rd Year CITI Certificate")
  * `target_year`: Which year of study this is due (1, 2, 3, 4, etc.)
  * `deadline_date`: When in that year it's due (uses year 2000 as dummy, e.g., 2000-08-15 for Aug 15)
  * `grace_period_days`: Number of days after deadline before submission is marked overdue (default: 7)
  * `notification_days_before_deadline`: Days before deadline to start sending reminder notifications (default: 90)
  * `is_mandatory`: Whether this requirement is mandatory for graduation (affects enforcement)
  * `special_instruction`: Optional custom instructions for students about this specific requirement
  * `is_active`: Whether this requirement is still in effect
  * `recurrence_type`: How often schedules are created (ANNUAL, ONCE)
  * `last_recurrence_at`: Timestamp of when schedules were last generated for this requirement
  * `months_before_deadline`: Months before deadline to create schedules for cron jobs
  * `effective_from_year/effective_until_year`: When this requirement is valid (academic year format)

**EXAMPLE REQUIREMENT:**
- Program: CS-BACHELOR
- Certificate: CITI  
- Name: "3rd Year Research Ethics Certification"
- Target Year: 3 (third year of study)
- Deadline: date(2000, 8, 15) (August 15th)
- Grace Period: 7 days
- Notification Days Before: 90 days
- Is Mandatory: true
- Special Instruction: "Complete all modules including the refresher course"
- Recurrence: ANNUAL
- Months Before Deadline: 6 (create schedules 6 months before deadline)
- Effective From: "2023-2024" (starts applying from this academic year)

This means: *"Every CS Bachelor student must submit a CITI certificate by August 15th of their 3rd year, with notifications starting 90 days before deadline and a 7-day grace period. Schedules are created 6 months before the deadline via cron jobs, effective from academic year 2023-2024 onwards."*

### 4. PROGRAM_REQUIREMENT_SCHEDULES TABLE (The Timeline Implementation)
- Creates specific deadlines for each academic year cohort
- Converts the general requirement rules into concrete dates
- Key fields:
  * `program_requirement_id`: Links to the general requirement rule
  * `academic_year_id`: Which student cohort this applies to  
  * `submission_deadline`: The actual datetime deadline for this cohort
  * `last_notified_at`: Timestamp of when reminder notifications were last sent (null if never sent)

**EXAMPLE SCHEDULES FOR THE CITI REQUIREMENT ABOVE:**

For students who started in 2023 (Academic Year 2023-2024):
- Their 3rd year is 2025-2026
- Schedule deadline: August 15, 2026 at 11:59 PM

For students who started in 2024 (Academic Year 2024-2025):
- Their 3rd year is 2026-2027  
- Schedule deadline: August 15, 2027 at 11:59 PM

For students who started in 2025 (Academic Year 2025-2026):
- Their 3rd year is 2027-2028
- Schedule deadline: August 15, 2028 at 11:59 PM

## Why This Design?

### 1. REQUIREMENT STABILITY
- The CITI requirement for CS students might last 5+ years unchanged
- We don't want to recreate the requirement rule every year
- We just create new schedules with updated deadlines

### 2. COHORT-SPECIFIC DEADLINES
- 2023 CS students and 2024 CS students have the same requirement
- But they need different deadline dates (2026 vs 2027)
- Schedules handle this automatically

### 3. EASY REQUIREMENT UPDATES
- If faculty decides to change CITI deadline from August to September
- We update the ProgramRequirement once
- Future schedule generations use the new deadline
- Existing schedules remain unchanged (grandfathering)

### 4. CRON-BASED AUTOMATED SCHEDULE CREATION
- Cron jobs use `months_before_deadline` to determine when to create new requirement schedules
- Scans all active requirements and creates schedules at the appropriate time
- Calculates deadline based on: `(academic_year + target_year + deadline_date)`
- Uses `months_before_deadline` to determine optimal schedule creation timing

## Automation Logic Examples

### Example 1: Cron Job Schedule Creation
**Cron job running daily finds:**
- Requirement: CS-BACHELOR needs CITI in year 3, deadline date(2000, 8, 15)
- months_before_deadline: 6
- New academic year: 2025-2026 (students starting now)
- Calculation: 2025 + 3 years = 2028, so deadline = August 15, 2028
- Creates schedule 6 months before deadline (February 15, 2028)
- Creates schedule: ProgramRequirementSchedule linking to 2025-2026 academic year
- Sets last_notified_at to null (notifications haven't started yet)

### Example 2: Different Timing Requirements
**For requirements with different timing needs:**
- Requirement: CS-BACHELOR needs ETHICS cert, months_before_deadline = 3
- Creates schedules 3 months before the actual deadline
- Useful for requirements that need less advance notice
- Allows flexible timing based on requirement complexity

## Benefits of This Design

✅ Requirements are defined once and reused  
✅ Each student cohort gets appropriate deadlines  
✅ Historical data is preserved (old schedules remain)  
✅ Automation reduces manual work for faculty  
✅ Easy to track compliance across different cohorts  
✅ Flexible enough to handle requirement changes over time  
✅ Supports different deadline patterns (annual, semester-based, one-time)  
✅ Flexible cron-based schedule creation timing  
✅ Effective date ranges for requirement lifecycle management  
✅ Unified date format reduces field complexity  
✅ Database-enforced date validation with year 2000 convention  

## Real World Workflow

1. **Faculty creates requirement:** "CS students need CITI cert in year 3 by Aug 15"
2. **System automatically creates schedules** for each new student cohort  
3. **Students see their specific deadline** in the portal
4. **Staff can track submissions** across all cohorts and requirements
5. **When requirements change,** only future cohorts are affected

## Database Schema Relationships

```sql
-- Core relationship chain
Programs (1) → (Many) ProgramRequirements (1) → (Many) ProgramRequirementSchedules

-- Supporting relationships
CertificateTypes (1) → (Many) ProgramRequirements
AcademicYears (1) → (Many) ProgramRequirementSchedules  
Students (1) → (Many) CertificateSubmissions
ProgramRequirementSchedules (1) → (Many) CertificateSubmissions
```

## Implementation Notes

### Field Design Decisions
- **Date Fields**: Using PostgreSQL Date type with year 2000 as dummy year for month/day storage
  * `deadline_date = date(2000, 8, 15)` represents August 15th (any year)
  * Database constraints ensure year 2000 is always used
- **Cron Timing**: `months_before_deadline` determines when cron jobs create new schedules
- **Lifecycle Management**: `effective_from_year` and `effective_until_year` handle requirement changes over time

### Technical Implementation
- The `recurrence_type` field allows for different automation patterns
- The `last_recurrence_at` field tracks when schedules were last generated for specific student cohorts
  * Stores August 1st of the student cohort year (not specific deadline dates)
  * Only compares years to handle deadline date changes gracefully
  * Example: For cohort 2024, stores 2024-08-01 00:00:00 UTC regardless of actual deadline month/day
- Using `is_active = False` instead of deletion preserves historical data
- The design supports multiple requirements per program and multiple programs per certificate type
- Academic years provide the temporal framework for calculating specific deadlines
- Database constraints ensure data consistency for cron timing fields

### Code Usage Examples
```python
from datetime import date

# Create requirement with cron-based schedule creation
requirement = ProgramRequirement(
    name="3rd Year CITI Certification",
    deadline_date=date(2000, 8, 15),  # August 15th
    grace_period_days=7,
    notification_days_before_deadline=90,
    months_before_deadline=6,  # Create schedules 6 months before deadline
    recurrence_type=ProgReqRecurrenceType.ANNUAL
)

# Create requirement with different timing
requirement = ProgramRequirement(
    name="Ethics Training Certificate",
    deadline_date=date(2000, 12, 1),   # December 1st deadline
    months_before_deadline=3,  # Create schedules 3 months before deadline
    notification_days_before_deadline=60
)

# Create requirement with longer lead time
requirement = ProgramRequirement(
    name="Lab Safety Certification",
    deadline_date=date(2000, 9, 30),   # September 30th deadline
    months_before_deadline=12,  # Create schedules 1 year before deadline
    effective_from_year="2024-2025"
)

# Extract month/day when needed
deadline_month = requirement.deadline_date.month  # 8
deadline_day = requirement.deadline_date.day      # 15
```

## Questions to Consider for Future Development

### 1. Student Program Transfers
**Challenge:** What happens to students who transfer between programs?

**Current Design Impact:**
- Students are linked to a single `program_id` 
- Existing certificate submissions are tied to the original program's requirements
- Transfer would require updating student's `program_id` but maintaining submission history

**Potential Solutions to Consider:**
- Add `transfer_history` table to track program changes
- Allow submissions to remain valid across related programs
- Create "program equivalency" rules for certificate transfers
- Add `program_at_submission_time` field to maintain context

### 2. Late Submissions and Extensions
**Challenge:** How do you handle late submissions or extensions?

**Current Design Impact:**
- `submission_deadline` in ProgramRequirementSchedule is fixed
- `submission_timing` enum tracks ON_TIME/LATE/OVERDUE
- No built-in extension mechanism

**Potential Solutions to Consider:**
- Add `extension_deadline` field to ProgramRequirementSchedule
- Create `submission_extensions` table for individual student extensions
- Utilize existing `grace_period_days` field in ProgramRequirement for automatic extensions
- Track extension reasons and approval workflow
- Consider different extension policies per requirement type

**Extension Workflow Options:**
```sql
-- Option A: Individual extensions table
CREATE TABLE submission_extensions (
    student_id UUID,
    requirement_schedule_id UUID, 
    extended_deadline TIMESTAMP,
    reason TEXT,
    approved_by UUID,
    approved_at TIMESTAMP
);

-- Option B: Add fields to existing schedule
ALTER TABLE program_requirement_schedules 
ADD COLUMN grace_period_days INTEGER DEFAULT 0,
ADD COLUMN extension_deadline TIMESTAMP;
```

**Implementation Considerations:**
- Automated late submission detection
- Staff notification workflows for overdue submissions
- Extension request and approval processes
- Impact on dashboard statistics and reporting