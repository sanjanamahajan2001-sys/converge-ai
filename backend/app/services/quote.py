"""Domain service for Customer Asks, Multi-Vendor Matching, and Email Quote Dispatch (Quote Subphase 3)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import math
from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload

from app.core.config import settings
from app.db.models.quote import (
    EmailDeliveryStatus,
    QuoteEmailDispatch,
    QuoteRequest,
    QuoteRequestStatus,
    QuoteUrgency,
    QuoteVendorMatch,
    VendorMatchStatus,
)
from app.db.models.user import User
from app.schemas.quote import (
    AdminQuoteDetailResponse,
    AdminQuoteDispatchItem,
    AdminQuoteListResponse,
    AdminQuoteMetrics,
    CustomerSummary,
    QuoteEmailDispatchDetail,
    QuoteRequestCreate,
    QuoteRequestDetail,
    QuoteVendorPanelCounts,
    QuoteVendorPanelItem,
    QuoteVendorPanelResponse,
    SendQuoteEmailRequest,
    SendQuoteEmailResponse,
)
from app.services.email import EmailMessage, get_email_service, render_commercial_quote_email

logger = logging.getLogger(__name__)


class QuoteService:
    """Service orchestrating customer asks, multi-vendor matching, and email quote delivery."""

    @staticmethod
    async def create_quote_request(
        db: AsyncSession,
        current_user: User,
        data: QuoteRequestCreate,
    ) -> QuoteRequestDetail:
        """Create a new procurement ask and broadcast it to qualified suppliers."""
        ask = QuoteRequest(
            customer_id=current_user.id,
            conversation_id=data.conversation_id,
            customer_agent_persona=data.customer_agent_persona or "Procurement AI Agent",
            title=data.title.strip(),
            product_name=data.product_name.strip(),
            product_code=data.product_code.strip() if data.product_code else None,
            grade_code=data.grade_code.strip() if data.grade_code else None,
            service_code=data.service_code.strip() if data.service_code else None,
            quantity=data.quantity,
            quantity_unit=data.quantity_unit or "MT",
            delivery_location=data.delivery_location.strip() if data.delivery_location else None,
            timeline_days=data.timeline_days,
            target_price_indication=data.target_price_indication,
            currency=data.currency or "INR",
            is_budget_public=data.is_budget_public,
            urgency=data.urgency,
            technical_specifications=data.technical_specifications or {},
            inquiry_notes=data.inquiry_notes.strip() if data.inquiry_notes else None,
            status=QuoteRequestStatus.OPEN,
        )
        db.add(ask)
        await db.flush()

        # Match qualified vendors
        matched_vendors: List[User] = []
        if data.target_vendor_ids:
            v_stmt = select(User).where(
                User.id.in_(data.target_vendor_ids),
                User.id != current_user.id,
                User.is_active == True,  # noqa: E712
            )
            matched_vendors = (await db.execute(v_stmt)).scalars().all()
        else:
            v_stmt = select(User).where(
                User.id != current_user.id,
                User.is_active == True,  # noqa: E712
            ).limit(5)
            matched_vendors = (await db.execute(v_stmt)).scalars().all()

        for idx, vendor in enumerate(matched_vendors):
            score = Decimal("95.00") - Decimal(str(idx * 2))
            reasons = [
                f"Supplies industrial materials matching category '{data.product_name}'",
                "Active supplier verified in conference delegate network",
            ]
            if data.delivery_location:
                reasons.append(f"Supports regional delivery to {data.delivery_location}")

            match = QuoteVendorMatch(
                quote_request_id=ask.id,
                vendor_id=vendor.id,
                match_score=score,
                match_reasons=reasons,
                status=VendorMatchStatus.PENDING_REVIEW,
            )
            db.add(match)

        if matched_vendors:
            ask.status = QuoteRequestStatus.MATCHED

        await db.commit()

        # Load ask with customer details
        load_stmt = (
            select(QuoteRequest)
            .options(
                joinedload(QuoteRequest.customer),
                selectinload(QuoteRequest.matches).selectinload(QuoteVendorMatch.dispatches),
            )
            .where(QuoteRequest.id == ask.id)
        )
        res = await db.execute(load_stmt)
        full_ask = res.scalar_one()

        cust = full_ask.customer
        return QuoteRequestDetail(
            id=full_ask.id,
            match_id=None,
            title=full_ask.title,
            product_name=full_ask.product_name,
            product_code=full_ask.product_code,
            grade_code=full_ask.grade_code,
            service_code=full_ask.service_code,
            quantity=full_ask.quantity,
            quantity_unit=full_ask.quantity_unit,
            delivery_location=full_ask.delivery_location,
            timeline_days=full_ask.timeline_days,
            target_price_indication=full_ask.target_price_indication,
            currency=full_ask.currency,
            is_budget_public=full_ask.is_budget_public,
            urgency=full_ask.urgency,
            status=full_ask.status,
            technical_specifications=full_ask.technical_specifications,
            inquiry_notes=full_ask.inquiry_notes,
            created_at=full_ask.created_at,
            customer=CustomerSummary(
                id=cust.id,
                full_name=cust.full_name,
                company_name=cust.company_name,
                job_title=cust.job_title,
                email=cust.email,
            ),
            customer_agent_persona=full_ask.customer_agent_persona,
            dispatches=[],
        )

    @staticmethod
    async def list_vendor_quotes_panel(
        db: AsyncSession,
        current_user: User,
        status_filter: str = "all",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QuoteVendorPanelResponse:
        """Query incoming procurement asks for the authenticated vendor."""
        # 1. Compute status counts
        count_stmt = select(QuoteVendorMatch.status).where(QuoteVendorMatch.vendor_id == current_user.id)
        count_res = await db.execute(count_stmt)
        all_status_rows = count_res.scalars().all()

        counts = QuoteVendorPanelCounts()
        counts.all = len(all_status_rows)
        for st in all_status_rows:
            if st == VendorMatchStatus.PENDING_REVIEW:
                counts.new_inquiries += 1
            elif st == VendorMatchStatus.QUOTED_VIA_EMAIL:
                counts.quoted += 1
            elif st == VendorMatchStatus.DECLINED:
                counts.declined += 1

        # 2. Build base query
        query = (
            select(QuoteVendorMatch)
            .join(QuoteRequest, QuoteVendorMatch.quote_request_id == QuoteRequest.id)
            .join(User, QuoteRequest.customer_id == User.id)
            .options(
                joinedload(QuoteVendorMatch.quote_request).joinedload(QuoteRequest.customer),
                selectinload(QuoteVendorMatch.dispatches),
            )
            .where(QuoteVendorMatch.vendor_id == current_user.id)
        )

        clean_status = status_filter.lower().strip()
        if clean_status == "new":
            query = query.where(QuoteVendorMatch.status == VendorMatchStatus.PENDING_REVIEW)
        elif clean_status == "quoted":
            query = query.where(QuoteVendorMatch.status == VendorMatchStatus.QUOTED_VIA_EMAIL)
        elif clean_status == "declined":
            query = query.where(QuoteVendorMatch.status == VendorMatchStatus.DECLINED)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    QuoteRequest.title.ilike(term),
                    QuoteRequest.product_name.ilike(term),
                    QuoteRequest.delivery_location.ilike(term),
                    User.full_name.ilike(term),
                    User.company_name.ilike(term),
                )
            )

        # Count total
        count_total_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_total_stmt)
        total = total_res.scalar_one()

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (max(page, 1) - 1) * page_size

        paginated_query = query.order_by(desc(QuoteVendorMatch.created_at)).offset(offset).limit(page_size)
        res = await db.execute(paginated_query)
        matches = res.scalars().all()

        items: List[QuoteVendorPanelItem] = []
        for m in matches:
            req = m.quote_request
            cust = req.customer
            dispatches = list(m.dispatches)
            dispatches.sort(key=lambda d: d.sent_at, reverse=True)
            latest_dispatch = dispatches[0] if dispatches else None

            items.append(
                QuoteVendorPanelItem(
                    match_id=m.id,
                    quote_request_id=req.id,
                    title=req.title,
                    product_name=req.product_name,
                    product_code=req.product_code,
                    quantity=req.quantity,
                    quantity_unit=req.quantity_unit,
                    delivery_location=req.delivery_location,
                    timeline_days=req.timeline_days,
                    urgency=req.urgency,
                    status=m.status,
                    match_score=m.match_score,
                    match_reasons=m.match_reasons,
                    viewed_at=m.viewed_at,
                    created_at=m.created_at,
                    customer=CustomerSummary(
                        id=cust.id,
                        full_name=cust.full_name,
                        company_name=cust.company_name,
                        job_title=cust.job_title,
                        email=cust.email,
                    ),
                    customer_agent_persona=req.customer_agent_persona,
                    dispatches_count=len(dispatches),
                    latest_quote_reference=latest_dispatch.quote_reference_number if latest_dispatch else None,
                    latest_quoted_value=latest_dispatch.total_value if latest_dispatch else None,
                    latest_quoted_currency=latest_dispatch.currency if latest_dispatch else None,
                    latest_dispatched_at=latest_dispatch.sent_at if latest_dispatch else None,
                )
            )

        return QuoteVendorPanelResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            counts=counts,
        )

    @staticmethod
    async def list_buyer_asks_panel(
        db: AsyncSession,
        current_user: User,
        status_filter: str = "all",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QuoteVendorPanelResponse:
        """Query procurement asks broadcasted by the authenticated customer delegate."""
        query = (
            select(QuoteRequest)
            .options(
                joinedload(QuoteRequest.customer),
                selectinload(QuoteRequest.matches).selectinload(QuoteVendorMatch.dispatches),
            )
            .where(QuoteRequest.customer_id == current_user.id)
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    QuoteRequest.title.ilike(term),
                    QuoteRequest.product_name.ilike(term),
                    QuoteRequest.delivery_location.ilike(term),
                )
            )

        # Count total
        count_total_stmt = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_total_stmt)
        total = total_res.scalar_one()

        # Count categories
        all_reqs_stmt = (
            select(QuoteRequest)
            .options(selectinload(QuoteRequest.matches).selectinload(QuoteVendorMatch.dispatches))
            .where(QuoteRequest.customer_id == current_user.id)
        )
        all_res = await db.execute(all_reqs_stmt)
        all_reqs = all_res.scalars().all()

        counts = {
            "all": len(all_reqs),
            "new_inquiries": sum(1 for r in all_reqs if not any(m.dispatches for m in r.matches)),
            "quoted": sum(1 for r in all_reqs if any(m.dispatches for m in r.matches)),
            "declined": sum(1 for r in all_reqs if r.status == QuoteRequestStatus.CANCELLED),
        }

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (max(page, 1) - 1) * page_size

        paginated_query = query.order_by(desc(QuoteRequest.created_at)).offset(offset).limit(page_size)
        res = await db.execute(paginated_query)
        reqs = res.scalars().all()

        items: List[QuoteVendorPanelItem] = []
        for req in reqs:
            cust = req.customer
            all_dispatches = [d for m in req.matches for d in m.dispatches]
            all_dispatches.sort(key=lambda d: d.sent_at, reverse=True)
            latest_dispatch = all_dispatches[0] if all_dispatches else None

            match_st = (
                VendorMatchStatus.QUOTED_VIA_EMAIL
                if all_dispatches
                else VendorMatchStatus.PENDING_REVIEW
            )

            items.append(
                QuoteVendorPanelItem(
                    match_id=None,
                    quote_request_id=req.id,
                    title=req.title,
                    product_name=req.product_name,
                    product_code=req.product_code,
                    quantity=req.quantity,
                    quantity_unit=req.quantity_unit,
                    delivery_location=req.delivery_location,
                    timeline_days=req.timeline_days,
                    urgency=req.urgency,
                    status=match_st,
                    match_score=Decimal(str(len(req.matches))),
                    match_reasons=[f"{len(req.matches)} vendors matched across conference."],
                    created_at=req.created_at,
                    customer=CustomerSummary(
                        id=cust.id,
                        full_name=cust.full_name,
                        company_name=cust.company_name,
                        job_title=cust.job_title,
                        email=cust.email,
                    ),
                    customer_agent_persona=req.customer_agent_persona,
                    dispatches_count=len(all_dispatches),
                    latest_quote_reference=latest_dispatch.quote_reference_number if latest_dispatch else None,
                    latest_quoted_value=latest_dispatch.total_value if latest_dispatch else None,
                    latest_quoted_currency=latest_dispatch.currency if latest_dispatch else None,
                    latest_dispatched_at=latest_dispatch.sent_at if latest_dispatch else None,
                )
            )

        return QuoteVendorPanelResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            counts=counts,
        )

    @staticmethod
    async def get_quote_request_detail(
        db: AsyncSession,
        current_user: User,
        quote_request_id: uuid.UUID,
    ) -> QuoteRequestDetail:
        """Inspect the full technical specifications of an ask with IDOR boundaries."""
        stmt = (
            select(QuoteRequest)
            .options(
                joinedload(QuoteRequest.customer),
                selectinload(QuoteRequest.matches).selectinload(QuoteVendorMatch.dispatches),
            )
            .where(QuoteRequest.id == quote_request_id)
        )
        res = await db.execute(stmt)
        ask = res.scalar_one_or_none()

        if not ask:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote request not found",
            )

        is_customer = ask.customer_id == current_user.id
        matched_entry: Optional[QuoteVendorMatch] = None
        for m in ask.matches:
            if m.vendor_id == current_user.id:
                matched_entry = m
                break

        if not is_customer and not matched_entry and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote request not found",
            )

        # Mark as viewed by vendor on first inspection
        if matched_entry and matched_entry.viewed_at is None:
            matched_entry.viewed_at = datetime.now(timezone.utc)
            await db.commit()

        # Build dispatches list
        dispatches_detail: List[QuoteEmailDispatchDetail] = []
        if matched_entry:
            for d in sorted(matched_entry.dispatches, key=lambda x: x.sent_at, reverse=True):
                dispatches_detail.append(
                    QuoteEmailDispatchDetail(
                        id=d.id,
                        quote_reference_number=d.quote_reference_number,
                        unit_price=d.unit_price,
                        total_value=d.total_value,
                        currency=d.currency,
                        incoterm=d.incoterm,
                        lead_time_days=d.lead_time_days,
                        validity_days=d.validity_days,
                        payment_terms=d.payment_terms,
                        commercial_notes=d.commercial_notes,
                        sender_email=d.sender_email,
                        recipient_email=d.recipient_email,
                        delivery_status=d.delivery_status,
                        sent_at=d.sent_at,
                    )
                )
        elif is_customer or current_user.is_admin:
            all_dispatches: List[QuoteEmailDispatch] = []
            for m in ask.matches:
                all_dispatches.extend(m.dispatches)
            all_dispatches.sort(key=lambda x: x.sent_at, reverse=True)

            for d in all_dispatches:
                dispatches_detail.append(
                    QuoteEmailDispatchDetail(
                        id=d.id,
                        quote_reference_number=d.quote_reference_number,
                        unit_price=d.unit_price,
                        total_value=d.total_value,
                        currency=d.currency,
                        incoterm=d.incoterm,
                        lead_time_days=d.lead_time_days,
                        validity_days=d.validity_days,
                        payment_terms=d.payment_terms,
                        commercial_notes=d.commercial_notes,
                        sender_email=d.sender_email,
                        recipient_email=d.recipient_email,
                        delivery_status=d.delivery_status,
                        sent_at=d.sent_at,
                    )
                )

        cust = ask.customer
        target_budget = (
            ask.target_price_indication
            if (ask.is_budget_public or is_customer or current_user.is_admin)
            else None
        )

        return QuoteRequestDetail(
            id=ask.id,
            match_id=matched_entry.id if matched_entry else None,
            title=ask.title,
            product_name=ask.product_name,
            product_code=ask.product_code,
            grade_code=ask.grade_code,
            service_code=ask.service_code,
            quantity=ask.quantity,
            quantity_unit=ask.quantity_unit,
            delivery_location=ask.delivery_location,
            timeline_days=ask.timeline_days,
            target_price_indication=target_budget,
            currency=ask.currency,
            is_budget_public=ask.is_budget_public,
            urgency=ask.urgency,
            status=ask.status,
            technical_specifications=ask.technical_specifications,
            inquiry_notes=ask.inquiry_notes,
            created_at=ask.created_at,
            customer=CustomerSummary(
                id=cust.id,
                full_name=cust.full_name,
                company_name=cust.company_name,
                job_title=cust.job_title,
                email=cust.email,
            ),
            customer_agent_persona=ask.customer_agent_persona,
            vendor_match_status=matched_entry.status if matched_entry else None,
            match_score=matched_entry.match_score if matched_entry else None,
            match_reasons=matched_entry.match_reasons if matched_entry else None,
            dispatches=dispatches_detail,
        )

    @staticmethod
    async def send_quote_via_email(
        db: AsyncSession,
        current_user: User,
        match_id: uuid.UUID,
        data: SendQuoteEmailRequest,
    ) -> SendQuoteEmailResponse:
        """Process supplier terms, assemble branded quotation, and dispatch via email."""
        stmt = (
            select(QuoteVendorMatch)
            .options(
                joinedload(QuoteVendorMatch.quote_request).joinedload(QuoteRequest.customer)
            )
            .where(
                QuoteVendorMatch.id == match_id,
                QuoteVendorMatch.vendor_id == current_user.id,
            )
        )
        res = await db.execute(stmt)
        match = res.scalar_one_or_none()

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor match not found or access denied",
            )

        ask = match.quote_request
        if ask.status == QuoteRequestStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot quote on a cancelled inquiry",
            )

        customer = ask.customer
        if not customer.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer has no registered email address on file",
            )

        # 1. CRLF Header Injection Defense (Prevent SMTP Header Splitting)
        for field_name, val in [("Incoterm", data.incoterm), ("Currency", data.currency)]:
            if val and ("\r" in val or "\n" in val):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Security violation: Newline characters not permitted in {field_name}",
                )

        # 2. Anti-spam Rate Limiting: Max 5 quotes per match
        cnt_stmt = select(func.count(QuoteEmailDispatch.id)).where(
            QuoteEmailDispatch.quote_vendor_match_id == match.id
        )
        cnt_res = await db.execute(cnt_stmt)
        total_dispatches = cnt_res.scalar() or 0
        if total_dispatches >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: Maximum 5 quotation revisions allowed per match.",
            )

        # 3. Anti-spam Rapid Dispatch Throttling: 5-second cooldown
        latest_stmt = (
            select(QuoteEmailDispatch.sent_at)
            .where(QuoteEmailDispatch.quote_vendor_match_id == match.id)
            .order_by(QuoteEmailDispatch.sent_at.desc())
            .limit(1)
        )
        latest_res = await db.execute(latest_stmt)
        last_sent_at = latest_res.scalar_one_or_none()
        if last_sent_at and (datetime.now(timezone.utc) - last_sent_at).total_seconds() < 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Throttled: Please wait 5 seconds before dispatching an updated quotation.",
            )

        qty = ask.quantity or Decimal("1.0")
        total_val = data.total_value or (qty * data.unit_price)

        year = datetime.now(timezone.utc).year
        ref_seq = match.id.hex[:6].upper()
        quote_ref = f"QUO-{year}-{ref_seq}"

        expiry_date = datetime.now(timezone.utc) + timedelta(days=data.validity_days)
        expiry_str = expiry_date.strftime("%b %d, %Y")

        sender_addr = settings.EMAIL_SENDER_ADDRESS or "sanjana.mahajan@sofueled.com"
        html_body, text_body = render_commercial_quote_email(
            quote_reference=quote_ref,
            product_name=ask.product_name,
            product_code=ask.product_code,
            quantity=qty,
            unit=ask.quantity_unit or "MT",
            unit_price=data.unit_price,
            total_value=total_val,
            currency=data.currency or "INR",
            incoterm=data.incoterm or "EXW",
            lead_time_days=data.lead_time_days,
            delivery_location=ask.delivery_location or "Destination Port",
            payment_terms=data.payment_terms,
            validity_days=data.validity_days,
            expiry_date_str=expiry_str,
            customer_name=customer.full_name,
            customer_company=customer.company_name or "Client Enterprise",
            customer_agent_name=ask.customer_agent_persona,
            vendor_delegate_name=current_user.full_name,
            vendor_company=current_user.company_name or "Vendor Corporation",
            sender_email=sender_addr,
            commercial_notes=data.commercial_notes,
        )

        email_subject = (
            f"Commercial Quotation: {ask.product_name} ({qty} {ask.quantity_unit or 'MT'}) [{quote_ref}]"
        )

        email_svc = get_email_service()
        msg = EmailMessage(
            to=[customer.email],
            subject=email_subject,
            html_body=html_body,
            text_body=text_body,
            sender_address=sender_addr,
            sender_name=f"{current_user.company_name or 'Converge AI'} via Converge AI",
            reply_to=current_user.email,
            cc=[current_user.email] if current_user.email else None,
            metadata={"quote_reference": quote_ref, "match_id": str(match.id)},
        )

        dispatch_result = await email_svc.send_email(msg)
        delivery_st = (
            EmailDeliveryStatus.SENT if dispatch_result.success else EmailDeliveryStatus.FAILED
        )

        dispatch = QuoteEmailDispatch(
            quote_vendor_match_id=match.id,
            quote_request_id=ask.id,
            vendor_id=current_user.id,
            sender_email=sender_addr,
            recipient_email=customer.email,
            quote_reference_number=quote_ref,
            unit_price=data.unit_price,
            total_value=total_val,
            currency=data.currency or "INR",
            incoterm=data.incoterm or "EXW",
            lead_time_days=data.lead_time_days,
            validity_days=data.validity_days,
            payment_terms=data.payment_terms,
            commercial_notes=data.commercial_notes,
            email_subject=email_subject,
            email_body_html=html_body,
            delivery_status=delivery_st,
            external_message_id=dispatch_result.message_id,
            error_message=dispatch_result.error,
        )
        db.add(dispatch)

        match.status = VendorMatchStatus.QUOTED_VIA_EMAIL
        await db.commit()

        logger.info(
            "Dispatched quote %s via email to %s (Status: %s)",
            quote_ref,
            customer.email,
            delivery_st.value,
        )

        return SendQuoteEmailResponse(
            dispatch_id=dispatch.id,
            quote_reference_number=quote_ref,
            recipient_email=customer.email,
            sender_email=sender_addr,
            total_value=total_val,
            currency=data.currency or "INR",
            delivery_status=delivery_st,
            sent_at=dispatch.sent_at,
            message=f"Commercial quotation {quote_ref} successfully dispatched to {customer.email}",
        )

    @staticmethod
    async def decline_quote_request(
        db: AsyncSession,
        current_user: User,
        match_id: uuid.UUID,
    ) -> dict:
        """Allow a matched supplier to decline an incoming ask."""
        stmt = select(QuoteVendorMatch).where(
            QuoteVendorMatch.id == match_id,
            QuoteVendorMatch.vendor_id == current_user.id,
        )
        res = await db.execute(stmt)
        match = res.scalar_one_or_none()

        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor match not found or access denied",
            )

        match.status = VendorMatchStatus.DECLINED
        await db.commit()
        logger.info("Vendor [%s] declined quote match [%s]", current_user.id, match_id)
        return {"status": "declined", "match_id": str(match_id)}

    @staticmethod
    async def send_direct_quote_from_conversation(
        db: AsyncSession,
        current_user: User,
        conversation_id: uuid.UUID,
        data: SendQuoteEmailRequest,
    ) -> SendQuoteEmailResponse:
        """Allow a vendor participant in a bilateral conversation to dispatch an official quote directly."""
        from sqlalchemy import func
        from app.db.models.conversation import Conversation, Message, MessageSenderType
        from app.services.quote_agent import QuoteAgentService

        # 1. Verify conversation
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv = (await db.execute(conv_stmt)).scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced conversation not found",
            )
        if current_user.id not in (conv.initiator_id, conv.target_id) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation",
            )

        # 2. Identify customer
        customer_id = conv.initiator_id if conv.target_id == current_user.id else conv.target_id
        cust_stmt = select(User).where(User.id == customer_id)
        customer = (await db.execute(cust_stmt)).scalar_one_or_none()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer participant not found",
            )

        # 3. Find or create QuoteRequest for this conversation
        ask_stmt = (
            select(QuoteRequest)
            .where(QuoteRequest.conversation_id == conversation_id)
            .order_by(QuoteRequest.created_at.desc())
        )
        ask = (await db.execute(ask_stmt)).scalars().first()
        if not ask:
            prefill = await QuoteAgentService.generate_ask_prefill(db, current_user, conversation_id)
            ask = await QuoteService.create_quote_request(db, customer, prefill)

        # 4. Find or create QuoteVendorMatch for current_user
        match_stmt = select(QuoteVendorMatch).where(
            QuoteVendorMatch.quote_request_id == ask.id,
            QuoteVendorMatch.vendor_id == current_user.id,
        )
        match = (await db.execute(match_stmt)).scalar_one_or_none()
        if not match:
            match = QuoteVendorMatch(
                quote_request_id=ask.id,
                vendor_id=current_user.id,
                match_score=Decimal("0.95"),
                match_reasons=["Direct commercial quotation initiated in 1-on-1 bilateral conversation."],
                status=VendorMatchStatus.PENDING_REVIEW,
            )
            db.add(match)
            await db.commit()
            await db.refresh(match)

        # 5. Dispatch quote email
        res = await QuoteService.send_quote_via_email(db, current_user, match.id, data)

        # 6. Post formatted confirmation message into chat
        try:
            qty_fmt = f"{int(ask.quantity):,}" if ask.quantity and ask.quantity == int(ask.quantity) else str(ask.quantity or "")
            unit_val = ask.quantity_unit or "MT"
            msg_content = (
                f"📄 **Official Commercial Quotation Dispatched via Email**\n\n"
                f"• **Reference ID:** `{res.quote_reference_number}`\n"
                f"• **Commodity:** {ask.product_name} ({qty_fmt} {unit_val})\n"
                f"• **Unit Consideration:** {data.currency} {data.unit_price:,.2f} / {unit_val}\n"
                f"• **Total Consideration:** {data.currency} {data.total_value:,.2f}\n"
                f"• **Governing Incoterm:** {data.incoterm} | **Timeline:** {data.lead_time_days} days\n"
                f"• **Payment Terms:** {data.payment_terms}\n\n"
                f"Delivered directly to {customer.full_name} ({customer.email})."
            )

            turn_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
            turn_count = (await db.execute(turn_stmt)).scalar() or 0

            msg = Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                sender_type=MessageSenderType.PARTICIPANT,
                turn_index=turn_count,
                content=msg_content,
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)

            # 7. Broadcast over WebSocket
            from app.api.routes.conversations import broadcast_conversation_event
            await broadcast_conversation_event(conversation_id, {
                "event": "message:new",
                "data": {
                    "id": str(msg.id),
                    "conversation_id": str(conversation_id),
                    "sender_id": str(current_user.id),
                    "content": msg.content,
                    "sender_type": "PARTICIPANT",
                    "turn_index": turn_count,
                    "created_at": msg.created_at.isoformat(),
                }
            })
        except Exception as b_ex:
            logger.warning("Failed to persist or broadcast in-chat quote message: %s", b_ex)

        return res

    @staticmethod
    async def list_admin_quotes(
        db: AsyncSession,
        search: Optional[str] = None,
        status: Optional[EmailDeliveryStatus] = None,
        user_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminQuoteListResponse:
        """Retrieve paginated platform quote dispatches for administrator oversight."""
        VendorUser = aliased(User)
        CustomerUser = aliased(User)

        query = (
            select(
                QuoteEmailDispatch,
                QuoteRequest,
                VendorUser,
                CustomerUser,
            )
            .join(QuoteRequest, QuoteEmailDispatch.quote_request_id == QuoteRequest.id)
            .join(VendorUser, QuoteEmailDispatch.vendor_id == VendorUser.id)
            .join(CustomerUser, QuoteRequest.customer_id == CustomerUser.id)
        )

        if status:
            query = query.where(QuoteEmailDispatch.delivery_status == status)

        if user_id:
            query = query.where(
                or_(
                    QuoteEmailDispatch.vendor_id == user_id,
                    QuoteRequest.customer_id == user_id,
                )
            )

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(QuoteEmailDispatch.quote_reference_number).like(term),
                    func.lower(QuoteRequest.product_name).like(term),
                    func.lower(QuoteRequest.title).like(term),
                    func.lower(QuoteEmailDispatch.recipient_email).like(term),
                    func.lower(QuoteEmailDispatch.sender_email).like(term),
                    func.lower(VendorUser.full_name).like(term),
                    func.lower(VendorUser.company_name).like(term),
                    func.lower(CustomerUser.full_name).like(term),
                    func.lower(CustomerUser.company_name).like(term),
                )
            )

        # Count total matching rows
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Platform metrics
        metrics_stmt = select(
            func.count(QuoteEmailDispatch.id).label("total_dispatched"),
            func.coalesce(func.sum(QuoteEmailDispatch.total_value), Decimal("0.00")).label("total_value"),
            func.count(func.distinct(QuoteEmailDispatch.vendor_id)).label("unique_vendors"),
            func.count(func.distinct(QuoteRequest.customer_id)).label("unique_customers"),
            func.count(func.nullif(QuoteEmailDispatch.delivery_status != EmailDeliveryStatus.SENT, True)).label("sent_count"),
            func.count(func.nullif(QuoteEmailDispatch.delivery_status != EmailDeliveryStatus.FAILED, True)).label("failed_count"),
        ).select_from(
            QuoteEmailDispatch.__table__.join(
                QuoteRequest.__table__,
                QuoteEmailDispatch.quote_request_id == QuoteRequest.id,
            )
        )
        if user_id:
            metrics_stmt = metrics_stmt.where(
                or_(
                    QuoteEmailDispatch.vendor_id == user_id,
                    QuoteRequest.customer_id == user_id,
                )
            )

        m_res = (await db.execute(metrics_stmt)).first()
        total_disp = m_res.total_dispatched if m_res else 0
        total_val = m_res.total_value if m_res else Decimal("0.00")
        u_vendors = m_res.unique_vendors if m_res else 0
        u_customers = m_res.unique_customers if m_res else 0
        sent_c = m_res.sent_count if m_res else 0
        failed_c = m_res.failed_count if m_res else 0
        rate_pct = (
            Decimal(str(round((sent_c / total_disp) * 100, 2)))
            if total_disp > 0
            else Decimal("100.00")
        )

        metrics = AdminQuoteMetrics(
            total_dispatched=total_disp,
            total_quoted_value=total_val,
            unique_vendors=u_vendors,
            unique_customers=u_customers,
            sent_count=sent_c,
            failed_count=failed_c,
            delivery_rate_percent=rate_pct,
        )

        offset = (page - 1) * page_size
        query = query.order_by(desc(QuoteEmailDispatch.sent_at)).offset(offset).limit(page_size)
        rows = (await db.execute(query)).all()

        items: List[AdminQuoteDispatchItem] = []
        for disp, ask, v_user, c_user in rows:
            items.append(
                AdminQuoteDispatchItem(
                    id=disp.id,
                    quote_reference_number=disp.quote_reference_number,
                    quote_request_id=disp.quote_request_id,
                    quote_vendor_match_id=disp.quote_vendor_match_id,
                    product_name=ask.product_name,
                    product_code=ask.product_code,
                    quantity=ask.quantity,
                    quantity_unit=ask.quantity_unit,
                    unit_price=disp.unit_price,
                    total_value=disp.total_value,
                    currency=disp.currency,
                    incoterm=disp.incoterm,
                    lead_time_days=disp.lead_time_days,
                    validity_days=disp.validity_days,
                    payment_terms=disp.payment_terms,
                    commercial_notes=disp.commercial_notes,
                    vendor_id=v_user.id,
                    vendor_name=v_user.full_name,
                    vendor_company=v_user.company_name,
                    sender_email=disp.sender_email,
                    customer_id=c_user.id,
                    customer_name=c_user.full_name,
                    customer_company=c_user.company_name,
                    recipient_email=disp.recipient_email,
                    email_subject=disp.email_subject,
                    delivery_status=disp.delivery_status,
                    external_message_id=disp.external_message_id,
                    error_message=disp.error_message,
                    sent_at=disp.sent_at,
                )
            )

        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        return AdminQuoteListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            metrics=metrics,
        )

    @staticmethod
    async def get_admin_quote_detail(
        db: AsyncSession,
        quote_id: uuid.UUID,
    ) -> AdminQuoteDetailResponse:
        """Retrieve full forensic inspection sheet for a quotation transmission."""
        VendorUser = aliased(User)
        CustomerUser = aliased(User)

        stmt = (
            select(
                QuoteEmailDispatch,
                QuoteRequest,
                VendorUser,
                CustomerUser,
            )
            .join(QuoteRequest, QuoteEmailDispatch.quote_request_id == QuoteRequest.id)
            .join(VendorUser, QuoteEmailDispatch.vendor_id == VendorUser.id)
            .join(CustomerUser, QuoteRequest.customer_id == CustomerUser.id)
            .where(QuoteEmailDispatch.id == quote_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation dispatch record not found.",
            )

        disp, ask, v_user, c_user = row
        return AdminQuoteDetailResponse(
            id=disp.id,
            quote_reference_number=disp.quote_reference_number,
            quote_request_id=disp.quote_request_id,
            quote_vendor_match_id=disp.quote_vendor_match_id,
            product_name=ask.product_name,
            product_code=ask.product_code,
            quantity=ask.quantity,
            quantity_unit=ask.quantity_unit,
            unit_price=disp.unit_price,
            total_value=disp.total_value,
            currency=disp.currency,
            incoterm=disp.incoterm,
            lead_time_days=disp.lead_time_days,
            validity_days=disp.validity_days,
            payment_terms=disp.payment_terms,
            commercial_notes=disp.commercial_notes,
            vendor_id=v_user.id,
            vendor_name=v_user.full_name,
            vendor_company=v_user.company_name,
            sender_email=disp.sender_email,
            customer_id=c_user.id,
            customer_name=c_user.full_name,
            customer_company=c_user.company_name,
            recipient_email=disp.recipient_email,
            email_subject=disp.email_subject,
            delivery_status=disp.delivery_status,
            external_message_id=disp.external_message_id,
            error_message=disp.error_message,
            sent_at=disp.sent_at,
            email_body_html=disp.email_body_html,
        )
