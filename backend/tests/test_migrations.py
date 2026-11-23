"""Tests for Alembic migrations, schema ownership, and least-privilege role boundaries."""

import os
import subprocess
import psycopg2
import pytest
from app.core.config import get_settings

settings = get_settings()
TEST_MIGRATION_URL = settings.TEST_MIGRATION_URL or settings.MIGRATION_DATABASE_URL
TEST_APP_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL
EXPECTED_SCHEMAS = ["core", "agenda", "a2a", "matching"]

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALEMBIC_BIN = os.path.join(BACKEND_DIR, ".venv", "bin", "alembic")


def get_connection(url: str):
    """Create raw psycopg2 connection."""
    clean_url = url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(clean_url)


def test_schema_existence_and_ownership():
    """Verify all 4 schemas exist in test DB and are owned by converge_ai_owner."""
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT nspname, r.rolname
            FROM pg_namespace n
            JOIN pg_roles r ON n.nspowner = r.oid
            WHERE n.nspname IN ('core', 'agenda', 'a2a', 'matching');
        """)
        results = dict(cur.fetchall())

    conn.close()

    for schema in EXPECTED_SCHEMAS:
        assert schema in results, f"Schema {schema} missing from test database"
        assert results[schema] == "converge_ai_owner", f"Schema {schema} not owned by converge_ai_owner"


def test_runtime_role_cannot_perform_ddl():
    """Verify runtime role converge_ai_app cannot create tables (GAP-02)."""
    conn = get_connection(TEST_APP_URL)
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("CREATE TABLE core.unauthorized_test (id serial);")
    conn.rollback()
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("CREATE TABLE agenda.unauthorized_test (id serial);")
    conn.close()


def test_runtime_role_cannot_drop_schema():
    """Verify runtime role converge_ai_app cannot drop application schemas (GAP-02)."""
    conn = get_connection(TEST_APP_URL)
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DROP SCHEMA core;")
    conn.rollback()
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DROP SCHEMA agenda;")
    conn.close()


def test_no_business_data_present():
    """Verify schemas contain no seeded business rows in baseline."""
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        # Verify core identity tables have 0 rows in baseline
        cur.execute("SELECT count(*) FROM core.users;")
        user_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.audit_logs;")
        audit_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.login_rate_limits;")
        rate_limit_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.user_sessions;")
        session_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.participant_profiles;")
        profile_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.participant_hobbies;")
        hobby_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM core.participant_topics;")
        topic_count = cur.fetchone()[0]

        # Verify agenda foundation tables exist and have 0 rows
        cur.execute("SELECT count(*) FROM agenda.conferences;")
        conference_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM agenda.sessions;")
        session_agenda_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM agenda.bookmarked_sessions;")
        bookmark_count = cur.fetchone()[0]

        # Verify a2a execution foundation tables exist and have 0 rows
        cur.execute("SELECT count(*) FROM a2a.tasks;")
        task_count = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM a2a.task_attempts;")
        attempt_count = cur.fetchone()[0]

        # Verify no tables in downstream domain schemas (matching)
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema = 'matching';
        """)
        downstream_tables = cur.fetchall()

    conn.close()
    assert user_count == 0, f"Expected 0 users in test DB, found {user_count}"
    assert audit_count == 0, f"Expected 0 audit logs in test DB, found {audit_count}"
    assert rate_limit_count == 0, f"Expected 0 rate limits in test DB, found {rate_limit_count}"
    assert session_count == 0, f"Expected 0 user sessions in test DB, found {session_count}"
    assert profile_count == 0, f"Expected 0 participant profiles in test DB, found {profile_count}"
    assert hobby_count == 0, f"Expected 0 participant hobbies in test DB, found {hobby_count}"
    assert topic_count == 0, f"Expected 0 participant topics in test DB, found {topic_count}"
    assert conference_count == 0, f"Expected 0 conferences in test DB, found {conference_count}"
    assert session_agenda_count == 0, f"Expected 0 agenda sessions in test DB, found {session_agenda_count}"
    assert bookmark_count == 0, f"Expected 0 bookmarked sessions in test DB, found {bookmark_count}"
    assert task_count == 0, f"Expected 0 tasks in test DB, found {task_count}"
    assert attempt_count == 0, f"Expected 0 task attempts in test DB, found {attempt_count}"
    assert len(downstream_tables) == 0, f"Expected 0 tables in matching schema, found: {downstream_tables}"


def test_migration_downgrade_and_reupgrade():
    """Verify Alembic downgrade to base drops schemas cleanly and re-upgrade succeeds."""
    assert "test" in TEST_MIGRATION_URL.lower(), (
        f"SAFETY GUARD: Destructive migration test aborted! Refusing to run on non-test database: {TEST_MIGRATION_URL}"
    )
    cmd_down = [
        ALEMBIC_BIN, "downgrade", "base"
    ]
    env = {**os.environ, "MIGRATION_DATABASE_URL": TEST_MIGRATION_URL}
    res_down = subprocess.run(cmd_down, env=env, capture_output=True, text=True, cwd=BACKEND_DIR)
    assert res_down.returncode == 0, f"Downgrade failed: {res_down.stderr}"

    # Verify schemas were dropped
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT nspname FROM pg_namespace
            WHERE nspname IN ('core', 'agenda', 'a2a', 'matching');
        """)
        schemas_after_down = cur.fetchall()
    conn.close()
    assert len(schemas_after_down) == 0, f"Expected schemas to be dropped, found: {schemas_after_down}"

    # 2. Re-upgrade to head
    cmd_up = [
        ALEMBIC_BIN, "upgrade", "head"
    ]
    res_up = subprocess.run(cmd_up, env=env, capture_output=True, text=True, cwd=BACKEND_DIR)
    assert res_up.returncode == 0, f"Re-upgrade failed: {res_up.stderr}"

    # Verify schemas recreated cleanly
    conn = get_connection(TEST_MIGRATION_URL)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT nspname FROM pg_namespace
            WHERE nspname IN ('core', 'agenda', 'a2a', 'matching');
        """)
        schemas_after_up = [r[0] for r in cur.fetchall()]
    conn.close()

    for s in EXPECTED_SCHEMAS:
        assert s in schemas_after_up
