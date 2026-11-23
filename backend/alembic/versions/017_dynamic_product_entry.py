"""Add custom_requirement_title for dynamic product and service entry

Revision ID: 017_dynamic_product_entry
Revises: 016_business_matching_profiles
Create Date: 2026-10-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic (must be <= 32 chars).
revision: str = "017_dynamic_product_entry"
down_revision: Union[str, None] = "016_business_matching_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add custom_requirement_title column to business_requirements
    op.add_column(
        "business_requirements",
        sa.Column(
            "custom_requirement_title",
            sa.String(length=200),
            nullable=False,
            server_default="",
        ),
        schema="business",
    )

    # 2. Backfill existing requirements from canonical_products or service_taxonomies
    op.execute(
        """
        UPDATE business.business_requirements br
        SET custom_requirement_title = COALESCE(
            NULLIF((SELECT canonical_name FROM business.canonical_products cp WHERE cp.product_code = br.product_code), ''),
            NULLIF((SELECT canonical_name FROM business.service_taxonomies st WHERE st.service_code = br.service_code), ''),
            'Procurement Requirement'
        )
        WHERE custom_requirement_title = '';
        """
    )


def downgrade() -> None:
    op.drop_column("business_requirements", "custom_requirement_title", schema="business")
