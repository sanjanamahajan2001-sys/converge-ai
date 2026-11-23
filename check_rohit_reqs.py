import asyncio
from app.db.session import db_manager
from app.db.models.user import User
from app.db.models.business import BusinessProfile, BusinessRequirement
from sqlalchemy import select

async def main():
    db_manager.initialize()
    async with db_manager.session_factory() as session:
        u = (await session.execute(select(User).where(User.username == 'rohit'))).scalar_one_or_none()
        if u:
            bp = (await session.execute(select(BusinessProfile).where(BusinessProfile.user_id == u.id))).scalar_one_or_none()
            reqs = (await session.execute(select(BusinessRequirement).where(BusinessRequirement.business_profile_id == bp.id))).scalars().all() if bp else []
            print(f"Rohit found! BP: {bp.company_name if bp else None}, Reqs: {[r.custom_requirement_title for r in reqs]}")
        else:
            print("Rohit not found in DB")
    await db_manager.close()

asyncio.run(main())
