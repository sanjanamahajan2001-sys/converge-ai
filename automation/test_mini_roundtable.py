import asyncio
import sys
sys.path.insert(0, '/home/sanjana/converge-ai/backend')

from app.core.config import get_settings
from app.db.session import DatabaseManager
from app.services.group_conversation import GroupConversationService
from app.schemas.group_conversation import GroupConversationCreate
from sqlalchemy import select
from app.db.models.user import User

async def main():
    settings = get_settings()
    manager = DatabaseManager(settings)
    manager.initialize()
    async with manager.session_factory() as session:
        res = await session.execute(select(User).limit(3))
        users = res.scalars().all()
        host = users[0]
        peers = [users[1], users[2]]
        print('Host:', host.username, 'Peers:', [p.username for p in peers])
        payload = GroupConversationCreate(
            title='Direct Mini Test Circle',
            topic_context='Testing AI generation in isolation',
            member_ids=[p.id for p in peers]
        )
        res = await GroupConversationService.create_circle(session, host.id, payload)
        print('Created OK. Current turn:', res.current_turn, 'msgs count:', len(res.messages))
        for m in res.messages:
            print(f'Turn {m.turn_index} [{m.sender_type}]: {m.content[:70]}...')

    await manager.close()

if __name__ == '__main__':
    asyncio.run(main())
