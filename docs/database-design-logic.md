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
  * `schedule_creation_trigger`: When to create schedules (AUTOMATIC, CUSTOM_DATE, RELATIVE_TO_TARGET_YEAR)
  * `custom_trigger_date`: For CUSTOM_DATE trigger (e.g., 2000-03-15 for March 15)
  * `months_before_target_year`: For RELATIVE_TO_TARGET_YEAR trigger
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
- Schedule Creation Trigger: AUTOMATIC
- Effective From: "2023-2024" (starts applying from this academic year)

This means: *"Every CS Bachelor student must submit a CITI certificate by August 15th of their 3rd year, with notifications starting 90 days before deadline and a 7-day grace period. Schedules are created automatically, effective from academic year 2023-2024 onwards."*

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

### 4. FLEXIBLE AUTOMATED SCHEDULE CREATION
- Multiple trigger mechanisms support different timing needs:
  * **AUTOMATIC**: Traditional approach - cron job runs at start of academic year based on recurrence_type
  * **CUSTOM_DATE**: Schedules created on specific calendar dates (e.g., March 15th every year)
  * **RELATIVE_TO_TARGET_YEAR**: Schedules created X months before students enter target year
- Scans all active requirements with appropriate trigger configurations
- Calculates deadline based on: `(academic_year + target_year + deadline_date)`

## Automation Logic Examples

### Example 1: Automatic Trigger
**On August 1st, 2025, cron job finds:**
- Requirement: CS-BACHELOR needs CITI in year 3, deadline date(2000, 8, 15)
- Trigger: AUTOMATIC
- New academic year: 2025-2026 (students starting now)
- Calculation: 2025 + 3 years = 2028, so deadline = August 15, 2028
- Creates schedule: ProgramRequirementSchedule linking to 2025-2026 academic year
- Sets last_notified_at to null (notifications haven't started yet)

### Example 2: Custom Date Trigger
**On March 15th (every year), cron job finds:**
- Requirement: CS-BACHELOR needs ETHICS cert, custom_trigger_date = date(2000, 3, 15)
- Trigger: CUSTOM_DATE
- Creates schedules for current academic year cohorts
- Useful for mid-year requirement additions or special timing needs

### Example 3: Relative to Target Year Trigger
**6 months before target year starts:**
- Requirement: CS-BACHELOR needs SAFETY cert, months_before_target_year = 6
- Trigger: RELATIVE_TO_TARGET_YEAR
- If students enter year 2 in August 2026, schedules created in February 2026
- Gives students advance notice and preparation time

## Benefits of This Design

✅ Requirements are defined once and reused  
✅ Each student cohort gets appropriate deadlines  
✅ Historical data is preserved (old schedules remain)  
✅ Automation reduces manual work for faculty  
✅ Easy to track compliance across different cohorts  
✅ Flexible enough to handle requirement changes over time  
✅ Supports different deadline patterns (annual, semester-based, one-time)  
✅ Multiple schedule creation triggers for different timing needs  
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
  * `custom_trigger_date = date(2000, 3, 10)` represents March 10th (any year)
  * Database constraints ensure year 2000 is always used
- **Trigger Flexibility**: `schedule_creation_trigger` enum supports different timing patterns
- **Lifecycle Management**: `effective_from_year` and `effective_until_year` handle requirement changes over time
- **Automation Control**: `auto_create_schedules` allows manual override of automation

### Technical Implementation
- The `recurrence_type` field allows for different automation patterns
- The `last_recurrence_at` field tracks when schedules were last generated
- Using `is_active = False` instead of deletion preserves historical data
- The design supports multiple requirements per program and multiple programs per certificate type
- Academic years provide the temporal framework for calculating specific deadlines
- Database constraints ensure data consistency for trigger-specific fields

### Code Usage Examples
```python
from datetime import date

# Create requirement with automatic trigger
requirement = ProgramRequirement(
    name="3rd Year CITI Certification",
    deadline_date=date(2000, 8, 15),  # August 15th
    grace_period_days=7,
    notification_days_before_deadline=90,
    schedule_creation_trigger=ScheduleCreationTrigger.AUTOMATIC,
    recurrence_type=ProgReqRecurrenceType.ANNUAL
)

# Create requirement with custom date trigger  
requirement = ProgramRequirement(
    name="Ethics Training Certificate",
    deadline_date=date(2000, 12, 1),   # December 1st deadline
    schedule_creation_trigger=ScheduleCreationTrigger.CUSTOM_DATE,
    custom_trigger_date=date(2000, 3, 15),  # Create schedules March 15th
    notification_days_before_deadline=60
)

# Create requirement with relative timing
requirement = ProgramRequirement(
    name="Lab Safety Certification",
    deadline_date=date(2000, 9, 30),   # September 30th deadline
    schedule_creation_trigger=ScheduleCreationTrigger.RELATIVE_TO_TARGET_YEAR,
    months_before_target_year=6,  # Create schedules 6 months before target year
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