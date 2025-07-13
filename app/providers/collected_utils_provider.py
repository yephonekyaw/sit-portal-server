from typing import List
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, Staff, Role, Permission, StaffPermission, Program


class CollectedUtilsProvider:
    @staticmethod
    async def get_staff_user_ids_by_program_and_role(
        program_code: str, role_name: str
    ) -> List[str]:
        """Get a list of staff user IDs based on program code and role name."""
        async with AsyncSessionLocal() as db:
            stmt = (
                select(User.id)
                .join(Staff, User.id == Staff.user_id)
                .join(StaffPermission, Staff.id == StaffPermission.staff_id)
                .join(Permission, StaffPermission.permission_id == Permission.id)
                .join(Role, Permission.role_id == Role.id)
                .join(Program, Permission.program_id == Program.id)
                .where(Program.program_code == program_code)
                .where(Role.name == role_name)
                .where(StaffPermission.is_active == True)
            )
            result = await db.execute(stmt)
            return [str(user_id) for user_id in result.scalars().all()]
