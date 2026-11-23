"""Clear lounge message history and reset room to turn 0."""

import asyncio
from app.db.session import db_manager
from app.db.models.chatroom import ChatroomMessage, ChatroomPresence, ConferenceChatroom
from sqlalchemy import delete, select

async def clear_lounge():
    db_manager.initialize()
    async with db_manager.session_factory() as session:
        # Delete all chatroom messages
        msg_del = await session.execute(delete(ChatroomMessage))
        print(f"Cleared {msg_del.rowcount} messages.")

        # Delete all presence records so new visits get fresh join
        pres_del = await session.execute(delete(ChatroomPresence))
        print(f"Cleared {pres_del.rowcount} presence records.")

        # Re-initialize clean welcome message for every active chatroom
        chatrooms = (await session.execute(select(ConferenceChatroom))).scalars().all()
        for cr in chatrooms:
            welcome_msg = ChatroomMessage(
                chatroom_id=cr.id,
                sender_id=None,
                sender_type="HOST",
                sender_name="Virtual Lounge Host",
                content=(
                    f"🎉 Welcome to the {cr.name}! "
                    f"This is an open town square for all conference delegates to chat, share session takeaways, "
                    f"connect on mutual initiatives, and stay posted on break announcements, live weather, and venue updates."
                ),
                message_kind="WELCOME",
                turn_index=0,
            )
            session.add(welcome_msg)
            print(f"Initialized fresh turn #0 for {cr.name} ({cr.slug})")

        await session.commit()
        print("✅ Lounge reset complete! Ready for fresh testing.")

if __name__ == "__main__":
    asyncio.run(clear_lounge())
