"""Initial database baseline: create application schemas and permissions (GAP-02)

Revision ID: 001_initial_schemas
Revises: 
Create Date: 2026-10-23 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schemas"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Approved application schemas
SCHEMAS = ["core", "agenda", "a2a", "matching"]
RUNTIME_ROLE = "converge_ai_app"
OWNER_ROLE = "converge_ai_owner"


def upgrade() -> None:
    """Create the 4 approved schemas and configure least-privilege runtime grants."""
    for schema in SCHEMAS:
        # Create schema owned by converge_ai_owner
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {OWNER_ROLE};")
        
        # Grant USAGE on schema to runtime application role
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO {RUNTIME_ROLE};")
        
        # Configure default privileges for future tables created by converge_ai_owner
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA {schema} "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {RUNTIME_ROLE};"
        )
        
        # Configure default privileges for future sequences created by converge_ai_owner
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA {schema} "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {RUNTIME_ROLE};"
        )


def downgrade() -> None:
    """Safely drop application schemas using RESTRICT to prevent accidental data loss."""
    # Reverse order for clean teardown
    for schema in reversed(SCHEMAS):
        # Drop default privileges
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA {schema} "
            f"REVOKE USAGE, SELECT ON SEQUENCES FROM {RUNTIME_ROLE};"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {OWNER_ROLE} IN SCHEMA {schema} "
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {RUNTIME_ROLE};"
        )
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM {RUNTIME_ROLE};")
        
        # Drop schema using RESTRICT (fails safely if tables were created)
        op.execute(f"DROP SCHEMA IF EXISTS {schema} RESTRICT;")
