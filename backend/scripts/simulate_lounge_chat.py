"""Simulate continuous ambient chat messages in the conference lounge."""

import argparse
import asyncio
import sys
from app.db.session import db_manager
from app.services.ambient_lounge_service import AmbientLoungeService
from app.services.temporal_context import TemporalContextService

async def simulate(count: int = 5, interval: float = 3.0):
    db_manager.initialize()
    async with db_manager.session_factory() as session:
        # Get active conference and lounge
        conf = await TemporalContextService.get_active_conference(session)
        conf_id = conf.id if conf else None
        lounge = await AmbientLoungeService.get_or_create_default_lounge(session, conference_id=conf_id)
        
        print(f"🎯 Simulating ambient lounge chat for: {lounge.name} (ID: {lounge.id})")
        print(f"⚡ Generating {count} messages with {interval}s interval between ticks...\n")

        for i in range(1, count + 1):
            generated, reason, msg = await AmbientLoungeService.generate_ambient_tick(
                session, lounge.id, force=True
            )
            if generated and msg:
                sender_label = f"[{msg.sender_type}] {msg.sender_name}"
                print(f"💬 Turn #{msg.turn_index} | {sender_label}:")
                print(f"   \"{msg.content}\"")
                print(f"   (Kind: {msg.message_kind})\n")
            else:
                print(f"⚠️ Tick {i}: Not generated ({reason})")

            if i < count:
                await asyncio.sleep(interval)

        print("✅ Ambient simulation finished successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate ambient lounge conversation")
    parser.add_argument("--count", type=int, default=5, help="Number of ambient messages to generate")
    parser.add_argument("--interval", type=float, default=3.0, help="Interval in seconds between messages")
    args = parser.parse_args()

    asyncio.run(simulate(count=args.count, interval=args.interval))
