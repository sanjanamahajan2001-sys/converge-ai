"""Unit tests for asynchronous email delivery and template rendering (Quote Subphase 1)."""

from unittest.mock import MagicMock, patch
import pytest

from app.services.email.base import EmailMessage
from app.services.email.console import ConsoleEmailService
from app.services.email.factory import get_email_service
from app.services.email.smtp import SmtpEmailService
from app.services.email.template import render_commercial_quote_email


@pytest.mark.asyncio
async def test_render_commercial_quote_email():
    """Verify HTML and plain text quotation rendering with strict XSS escaping."""
    html_body, text_body = render_commercial_quote_email(
        quote_reference="QUO-2026-0042",
        product_name="Limestone Calcined Clay Cement (LC3)",
        product_code="CALCINED_CLAY_LC3",
        quantity=1000,
        unit="MT",
        unit_price=3500.0,
        total_value=3500000.0,
        currency="INR",
        incoterm="EXW",
        lead_time_days=21,
        delivery_location="Pune Industrial Yard",
        payment_terms="20% Advance, 80% Delivery",
        validity_days=14,
        expiry_date_str="Nov 20, 2026",
        customer_name="Mahajan Sanjana",
        customer_company="InfraTech EPC Ltd",
        customer_agent_name="InfraTech Agent",
        vendor_delegate_name="Maahi Sharma",
        vendor_company="Deccan Green Cement & Binders",
        sender_email="sanjana.mahajan@sofueled.com",
        commercial_notes="Subject to batch test certification IS 18189 <script>alert(1)</script>",
    )

    # Assert basic contents
    assert "QUO-2026-0042" in html_body
    assert "QUO-2026-0042" in text_body
    assert "Limestone Calcined Clay Cement (LC3)" in html_body
    assert "CALCINED_CLAY_LC3" in html_body
    assert "3,500,000" in html_body
    assert "1,000 MT" in html_body
    assert "Pune Industrial Yard" in html_body
    assert "sanjana.mahajan@sofueled.com" in html_body

    # Assert strict HTML escaping of injection strings
    assert "<script>" not in html_body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_body


@pytest.mark.asyncio
async def test_console_email_service():
    """Verify ConsoleEmailService records sent messages for testing and inspection."""
    service = ConsoleEmailService()
    assert len(service.sent_messages) == 0

    msg = EmailMessage(
        to=["buyer@infoglobal.com"],
        subject="Commercial Quote QUO-2026-0001",
        html_body="<p>Commercial offer details</p>",
        text_body="Commercial offer details",
    )

    result = await service.send_email(msg)
    assert result.success is True
    assert result.message_id is not None
    assert len(service.sent_messages) == 1
    assert service.sent_messages[0].to == ["buyer@infoglobal.com"]
    assert service.sent_messages[0].subject == "Commercial Quote QUO-2026-0001"

    service.clear()
    assert len(service.sent_messages) == 0


@pytest.mark.asyncio
async def test_factory_email_service():
    """Verify factory returns appropriate instance based on backend specifier."""
    console_svc = get_email_service("console")
    assert isinstance(console_svc, ConsoleEmailService)

    smtp_svc = get_email_service("smtp")
    assert isinstance(smtp_svc, SmtpEmailService)


@pytest.mark.asyncio
async def test_smtp_empty_recipient_fails_safely():
    """Verify SMTP service fails fast if recipient list is empty."""
    service = SmtpEmailService()
    msg = EmailMessage(
        to=[],
        subject="Missing recipient",
        html_body="<p>Test</p>",
    )
    result = await service.send_email(msg)
    assert result.success is False
    assert "Recipient list cannot be empty" in (result.error or "")


@pytest.mark.asyncio
async def test_smtp_mocked_transmission():
    """Verify MIME assembly, STARTTLS, and message transmission via mock SMTP."""
    service = SmtpEmailService(
        host="smtp.gmail.com",
        port=587,
        use_tls=True,
        username="sanjana.mahajan@sofueled.com",
        password="mock_app_password",
    )

    mock_smtp_instance = MagicMock()

    with patch("smtplib.SMTP", return_value=mock_smtp_instance):
        msg = EmailMessage(
            to=["delegate@client.com"],
            subject="Test Quotation",
            html_body="<h1>Hello</h1>",
            text_body="Hello",
            sender_address="sanjana.mahajan@sofueled.com",
            sender_name="Converge AI Network",
            cc=["sales@vendor.com"],
        )

        result = await service.send_email(msg)
        assert result.success is True
        assert result.message_id is not None

        # Verify SMTP server lifecycle methods were invoked on the context-managed instance
        mock_server = mock_smtp_instance.__enter__.return_value
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            "sanjana.mahajan@sofueled.com", "mock_app_password"
        )
        mock_server.send_message.assert_called_once()
