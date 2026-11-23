"""Seed sample conference and session data for testing the Agenda & Bookmarks UI (P3-WS4).

Usage:
    python backend/scripts/seed_sample_agenda.py
    python backend/scripts/seed_sample_agenda.py --clear
"""

import argparse
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, text

# Add backend root to sys.path and configure ENV_FILE path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
if "ENV_FILE" not in os.environ:
    env_candidate = backend_dir / ".env"
    if env_candidate.exists():
        os.environ["ENV_FILE"] = str(env_candidate)

# Hardcoded deterministic sample UUIDs for clean tracking and idempotency
SAMPLE_CONF_ID = "c0000000-0000-0000-0000-000000000001"
SAMPLE_SESSION_1 = "a0000000-0000-0000-0000-000000000001"
SAMPLE_SESSION_2 = "a0000000-0000-0000-0000-000000000002"
SAMPLE_SESSION_3 = "a0000000-0000-0000-0000-000000000003"
SAMPLE_SESSION_4 = "a0000000-0000-0000-0000-000000000004"

def get_engine():
    from app.core.config import get_settings
    settings = get_settings()
    db_url = settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL
    # Ensure psycopg2 driver for synchronous execution
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "+psycopg2")
    return create_engine(db_url)

def clear_sample_data(engine):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM agenda.bookmarked_sessions WHERE session_id IN (:s1, :s2, :s3, :s4)"),
            {"s1": SAMPLE_SESSION_1, "s2": SAMPLE_SESSION_2, "s3": SAMPLE_SESSION_3, "s4": SAMPLE_SESSION_4}
        )
        conn.execute(
            text("DELETE FROM agenda.sessions WHERE conference_id = :cid"),
            {"cid": SAMPLE_CONF_ID}
        )
        conn.execute(
            text("DELETE FROM agenda.conferences WHERE id = :cid"),
            {"cid": SAMPLE_CONF_ID}
        )
    print("Cleared sample agenda and sessions successfully.")

def seed_sample_data(engine):
    tz = ZoneInfo("America/Los_Angeles")

    # Dates in venue timezone:
    # Day 1: 2026-11-10
    # Day 2: 2026-11-11
    s1_start = datetime(2026, 11, 10, 9, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    s1_end = datetime(2026, 11, 10, 10, 30, tzinfo=tz).astimezone(ZoneInfo("UTC"))

    s2_start = datetime(2026, 11, 10, 11, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    s2_end = datetime(2026, 11, 10, 12, 30, tzinfo=tz).astimezone(ZoneInfo("UTC"))

    s3_start = datetime(2026, 11, 11, 10, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    s3_end = datetime(2026, 11, 11, 11, 30, tzinfo=tz).astimezone(ZoneInfo("UTC"))

    s4_start = datetime(2026, 11, 11, 14, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
    s4_end = datetime(2026, 11, 11, 15, 30, tzinfo=tz).astimezone(ZoneInfo("UTC"))

    with engine.begin() as conn:
        # Check if already seeded
        res = conn.execute(
            text("SELECT id FROM agenda.conferences WHERE id = :cid"),
            {"cid": SAMPLE_CONF_ID}
        ).fetchone()

        if res:
            print("Sample conference already exists. Cleaning up existing sample records first...")
            clear_sample_data(engine)

        # 1. Insert Conference
        conn.execute(
            text("""
                INSERT INTO agenda.conferences (
                    id, title, description, venue_name, timezone, start_date, end_date, is_active, created_at, updated_at
                ) VALUES (
                    :id, :title, :description, :venue_name, :timezone, :start_date, :end_date, :is_active, NOW(), NOW()
                )
            """),
            {
                "id": SAMPLE_CONF_ID,
                "title": "Converge AI Global Summit 2026",
                "description": "The premier gathering for autonomous agent architectures, zero-trust coordination, and multi-agent systems.",
                "venue_name": "Moscone Convention Center, San Francisco",
                "timezone": "America/Los_Angeles",
                "start_date": "2026-11-10",
                "end_date": "2026-11-12",
                "is_active": True,
            }
        )

        # 2. Insert Sessions
        sessions = [
            {
                "id": SAMPLE_SESSION_1,
                "conference_id": SAMPLE_CONF_ID,
                "title": "Autonomous Multi-Agent Networks: Architecture & Negotiation",
                "abstract": "An in-depth keynote exploring real-time peer consensus, decentralized coordination algorithms, and telemetry in large-scale agent networks.",
                "speaker_names": "Dr. Alice Martin, Bob Vance",
                "track_name": "Architecture",
                "hall_room": "Grand Ballroom A",
                "start_time": s1_start,
                "end_time": s1_end,
                "is_cancelled": False,
            },
            {
                "id": SAMPLE_SESSION_2,
                "conference_id": SAMPLE_CONF_ID,
                "title": "Zero-Trust Protocol Design for Edge Agent Clusters",
                "abstract": "Securing cross-organizational agent communication over public networks with cryptographic hardware enclaves and mutual TLS.",
                "speaker_names": "Carol Danvers",
                "track_name": "Security",
                "hall_room": "Hall B",
                "start_time": s2_start,
                "end_time": s2_end,
                "is_cancelled": False,
            },
            {
                "id": SAMPLE_SESSION_3,
                "conference_id": SAMPLE_CONF_ID,
                "title": "Decentralized Consensus in Practice: Enterprise Case Studies",
                "abstract": "Production lessons learned from deploying 10,000+ collaborating agents across hybrid cloud infrastructures.",
                "speaker_names": "David Kim, Sarah Jenkins",
                "track_name": "Architecture",
                "hall_room": "Grand Ballroom A",
                "start_time": s3_start,
                "end_time": s3_end,
                "is_cancelled": False,
            },
            {
                "id": SAMPLE_SESSION_4,
                "conference_id": SAMPLE_CONF_ID,
                "title": "Hardware Enclaves & Ephemeral Key Delegation",
                "abstract": "Deep dive into secure key delegation protocols for autonomous agents acting on behalf of delegates. (Cancelled due to speaker travel delay).",
                "speaker_names": "Dr. Elena Rostova",
                "track_name": "Security",
                "hall_room": "Hall C",
                "start_time": s4_start,
                "end_time": s4_end,
                "is_cancelled": True, # Cancelled to demonstrate the cancellation indicator
            },
        ]

        for s in sessions:
            conn.execute(
                text("""
                    INSERT INTO agenda.sessions (
                        id, conference_id, title, abstract, speaker_names, track_name,
                        hall_room, start_time, end_time, is_cancelled, created_at, updated_at
                    ) VALUES (
                        :id, :conference_id, :title, :abstract, :speaker_names, :track_name,
                        :hall_room, :start_time, :end_time, :is_cancelled, NOW(), NOW()
                    )
                """),
                s
            )

    print("Successfully seeded 'Converge AI Global Summit 2026' with 4 sessions across 2 days!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed or clear sample agenda data.")
    parser.add_argument("--clear", action="store_true", help="Clear sample agenda data")
    args = parser.parse_args()

    engine = get_engine()
    if args.clear:
        clear_sample_data(engine)
    else:
        seed_sample_data(engine)
