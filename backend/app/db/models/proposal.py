"""Domain models for Commercial Proposals, Revisions, Approvals, and Contact Disclosures (Phase 7 - Subphase 2).

Enforces:
1. Zero Contact Leakage Invariant: Contact credentials remain strictly guarded until dual-sided approval.
2. Forensic Attribution: Proposer, Revision Author, and Approval Actor permanently recorded.
3. Concurrency Protection: Pessimistic row-locking compatible schema.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.user import User


class ProposalStatus(str, enum.Enum):
    """Proposal lifecycle states."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    MUTUALLY_APPROVED = "MUTUALLY_APPROVED"
    REJECTED = "REJECTED"
    REVISED = "REVISED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class CommercialRole(str, enum.Enum):
    """Commercial role in a bilateral transaction."""

    BUYER = "BUYER"
    SUPPLIER = "SUPPLIER"
    VENDOR = "VENDOR"
    DISTRIBUTOR = "DISTRIBUTOR"
    PARTNER = "PARTNER"


class ProposalType(str, enum.Enum):
    """Structured commercial proposal categories."""

    SUPPLY_CONTRACT = "SUPPLY_CONTRACT"
    PROCUREMENT_ORDER = "PROCUREMENT_ORDER"
    DISTRIBUTION_AGREEMENT = "DISTRIBUTION_AGREEMENT"
    SERVICE_MOU = "SERVICE_MOU"
    STRATEGIC_PARTNERSHIP = "STRATEGIC_PARTNERSHIP"


class ApprovalAction(str, enum.Enum):
    """Recorded action on a proposal revision."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class Proposal(Base):
    """Authoritative domain entity governing bilateral commercial proposals."""

    __tablename__ = "proposals"
    __table_args__ = (
        CheckConstraint("proposer_id != recipient_id", name="ck_proposals_distinct_parties"),
        CheckConstraint("current_revision_number >= 1", name="ck_proposals_min_revision"),
        Index(
            "uq_active_proposal_pair",
            "proposer_id",
            "recipient_id",
            unique=True,
            postgresql_where=text("status IN ('DRAFT', 'PENDING_REVIEW', 'REVISED')"),
        ),
        Index("ix_proposals_proposer", "proposer_id"),
        Index("ix_proposals_recipient", "recipient_id"),
        Index("ix_proposals_conversation", "conversation_id"),
        Index("ix_proposals_status", "status"),
        Index("ix_proposals_created_at", "created_at"),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposer_role: Mapped[CommercialRole] = mapped_column(
        Enum(CommercialRole, name="proposal_commercial_role", schema="business"),
        nullable=False,
    )
    recipient_role: Mapped[CommercialRole] = mapped_column(
        Enum(CommercialRole, name="proposal_commercial_role", schema="business"),
        nullable=False,
    )
    proposal_type: Mapped[ProposalType] = mapped_column(
        Enum(ProposalType, name="proposal_type", schema="business"),
        default=ProposalType.SUPPLY_CONTRACT,
        nullable=False,
    )
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="proposal_status", schema="business"),
        default=ProposalStatus.PENDING_REVIEW,
        server_default="PENDING_REVIEW",
        nullable=False,
    )
    current_revision_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    concluded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    revisions: Mapped[List["ProposalRevision"]] = relationship(
        "ProposalRevision",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalRevision.revision_number",
        lazy="selectin",
    )
    approvals: Mapped[List["ProposalApproval"]] = relationship(
        "ProposalApproval",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalApproval.created_at",
        lazy="selectin",
    )
    contact_disclosures: Mapped[List["ProposalContactDisclosure"]] = relationship(
        "ProposalContactDisclosure",
        back_populates="proposal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    proposer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[proposer_id],
        lazy="selectin",
    )
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id],
        lazy="selectin",
    )
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Proposal id={self.id} type={self.proposal_type.value} "
            f"status={self.status.value} rev={self.current_revision_number}>"
        )


class ProposalRevision(Base):
    """Versioned commercial contract terms and parameter specifications."""

    __tablename__ = "proposal_revisions"
    __table_args__ = (
        UniqueConstraint("proposal_id", "revision_number", name="uq_proposal_revision_number"),
        CheckConstraint("revision_number >= 1", name="ck_rev_min_revision_number"),
        CheckConstraint("quantity > 0", name="ck_rev_quantity_positive"),
        CheckConstraint(
            "delivery_timeline_days >= 1 AND delivery_timeline_days <= 730",
            name="ck_rev_delivery_timeline_range",
        ),
        Index("ix_proposal_revisions_proposal", "proposal_id"),
        Index("ix_proposal_revisions_author", "author_id"),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    proposal_type: Mapped[ProposalType] = mapped_column(
        Enum(ProposalType, name="proposal_type", schema="business"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    grade_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    service_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", server_default="INR", nullable=False)
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_location: Mapped[str] = mapped_column(String(150), nullable=False)
    incoterm: Mapped[Optional[str]] = mapped_column(String(20), default="EXW", server_default="EXW", nullable=True)
    delivery_timeline_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30", nullable=False)
    governing_standards: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    special_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revision_summary: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="revisions")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="selectin")
    approvals: Mapped[List["ProposalApproval"]] = relationship(
        "ProposalApproval",
        back_populates="revision",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProposalRevision id={self.id} proposal_id={self.proposal_id} rev={self.revision_number} title={self.title!r}>"


class ProposalApproval(Base):
    """Non-repudiable approval or rejection decision logged for a specific proposal revision."""

    __tablename__ = "proposal_approvals"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "revision_id",
            "user_id",
            "action",
            name="uq_proposal_approval_decision",
        ),
        Index("ix_proposal_approvals_proposal", "proposal_id"),
        Index("ix_proposal_approvals_revision", "revision_id"),
        Index("ix_proposal_approvals_user", "user_id"),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.proposal_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[ApprovalAction] = mapped_column(
        Enum(ApprovalAction, name="proposal_approval_action", schema="business"),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="approvals")
    revision: Mapped["ProposalRevision"] = relationship("ProposalRevision", back_populates="approvals")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<ProposalApproval id={self.id} rev={self.revision_id} user={self.user_id} action={self.action.value}>"


class ProposalContactDisclosure(Base):
    """Immutable ledger of verified contact disclosures authorized upon dual-sided proposal approval."""

    __tablename__ = "proposal_contact_disclosures"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "user_id",
            "disclosed_to_user_id",
            name="uq_proposal_contact_disclosure_pair",
        ),
        Index("ix_contact_disclosures_proposal", "proposal_id"),
        Index("ix_contact_disclosures_user", "user_id"),
        Index("ix_contact_disclosures_recipient", "disclosed_to_user_id"),
        {"schema": "business"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business.proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    disclosed_to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("core.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    disclosed_credentials: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    disclosed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="contact_disclosures")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    disclosed_to_user: Mapped["User"] = relationship("User", foreign_keys=[disclosed_to_user_id], lazy="selectin")

    def __repr__(self) -> str:
        # Strictly omit sensitive contact info from __repr__
        return f"<ProposalContactDisclosure id={self.id} proposal_id={self.proposal_id} from={self.user_id} to={self.disclosed_to_user_id}>"
