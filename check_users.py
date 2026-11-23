import asyncio
import sys
sys.path.insert(0, /home/sanjana/converge-ai/backend)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.config import get_settings
from app.db.session import DatabaseManager
from app.db.models.user import User

async def main():
    settings = get_settings()
    mgr = DatabaseManager(settings)
    mgr.initialize()
    async with mgr.session_factory() as s:
        res = await s.execute(select(User).options(selectinload(User.profile), selectinload(User.hobbies), selectinload(User.topics)).limit(5))
        for u in res.scalars():
            loc = u.profile.location if u.profile else None
            hobbies = [h.hobby_name for h in u.hobbies]
            topics = [t.topic_keyword for t in u.topics]
            print(f{u.full_name}
