"""Email template rendering engine for commercial quotations and alerts.

Ensures strict HTML escaping on all dynamic parameters to prevent email injection.
"""

from decimal import Decimal
import html
from typing import Any, Optional, Tuple, Union


def _format_quantity(val: Union[float, int, str, Decimal]) -> str:
    """Format quantity without trailing zeros."""
    try:
        d = Decimal(str(val))
        # Remove trailing zeros after decimal point
        normalized = d.normalize()
        # If integer, return as comma-formatted int
        if normalized == normalized.to_integral():
            return f"{int(normalized):,}"
        return f"{normalized:,}"
    except Exception:
        return str(val)


def _format_money(val: Union[float, int, str, Decimal]) -> str:
    """Format money with comma grouping."""
    try:
        d = Decimal(str(val))
        if d == d.to_integral():
            return f"{int(d):,}"
        return f"{d:,.2f}"
    except Exception:
        return str(val)


def render_commercial_quote_email(
    *,
    quote_reference: str,
    product_name: str,
    product_code: Optional[str] = None,
    quantity: Union[float, int, str],
    unit: str,
    unit_price: Union[float, int, str],
    total_value: Union[float, int, str],
    currency: str = "INR",
    incoterm: str = "EXW",
    lead_time_days: int = 14,
    delivery_location: str = "Destination Port",
    payment_terms: str = "30 Days Net",
    validity_days: int = 15,
    expiry_date_str: str = "",
    customer_name: str = "Valued Buyer",
    customer_company: str = "Client Enterprise",
    customer_agent_name: Optional[str] = None,
    vendor_delegate_name: str = "Commercial Representative",
    vendor_company: str = "Vendor Corporation",
    sender_email: str = "sanjana.mahajan@sofueled.com",
    commercial_notes: Optional[str] = None,
) -> Tuple[str, str]:
    """Render dual HTML and plain-text versions of a commercial quotation email.

    Returns:
        Tuple[str, str]: (html_body, plain_text_body)
    """
    # Sanitize dynamic inputs
    safe_quote_ref = html.escape(str(quote_reference))
    safe_product_name = html.escape(str(product_name))
    safe_product_code = html.escape(str(product_code)) if product_code else ""
    safe_quantity = html.escape(_format_quantity(quantity))
    safe_unit = html.escape(str(unit))
    safe_unit_price = html.escape(_format_money(unit_price))
    safe_total_value = html.escape(_format_money(total_value))
    safe_currency = html.escape(str(currency))
    safe_incoterm = html.escape(str(incoterm))
    safe_location = html.escape(str(delivery_location))
    safe_payment = html.escape(str(payment_terms))
    safe_expiry = html.escape(str(expiry_date_str))
    safe_cust_name = html.escape(str(customer_name))
    safe_cust_company = html.escape(str(customer_company))
    safe_agent_name = html.escape(str(customer_agent_name or "Procurement AI Agent"))
    safe_vendor_delegate = html.escape(str(vendor_delegate_name))
    safe_vendor_company = html.escape(str(vendor_company))
    safe_sender_email = html.escape(str(sender_email))
    safe_notes = html.escape(str(commercial_notes or "No additional caveats specified."))

    sku_badge = (
        f'<span style="font-family: monospace; font-size: 11px; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; border: 1px solid #cbd5e1; color: #475569;">SKU: {safe_product_code}</span>'
        if safe_product_code
        else ""
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Commercial Quotation {safe_quote_ref}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      margin: 0;
      padding: 24px;
      color: #0f172a;
      -webkit-font-smoothing: antialiased;
    }}
    .wrapper {{
      max-width: 620px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      background: #0f172a;
      color: #f8fafc;
      padding: 24px 28px;
      border-bottom: 3px solid #c28833;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      background: #c28833;
      color: #ffffff;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .title {{
      font-size: 20px;
      font-weight: 700;
      margin: 14px 0 6px;
      color: #ffffff;
    }}
    .subtitle {{
      font-size: 13px;
      color: #94a3b8;
    }}
    .content {{
      padding: 28px;
    }}
    .greeting {{
      font-size: 14px;
      line-height: 1.5;
      margin-bottom: 16px;
      color: #334155;
    }}
    .spec-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }}
    .spec-table tr:nth-child(even) {{
      background-color: #f8fafc;
    }}
    .spec-table td {{
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
      font-size: 13px;
    }}
    .spec-label {{
      color: #64748b;
      width: 38%;
      font-weight: 500;
    }}
    .spec-value {{
      color: #0f172a;
      font-weight: 600;
    }}
    .total-box {{
      background: #fdfaf3;
      border: 1px solid #fae8c8;
      border-radius: 8px;
      padding: 18px;
      margin: 22px 0;
      text-align: left;
    }}
    .total-label {{
      font-size: 11px;
      text-transform: uppercase;
      color: #8d621e;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .total-amount {{
      font-size: 24px;
      font-weight: 800;
      color: #0f172a;
      margin-top: 4px;
      font-family: 'Courier New', Courier, monospace;
    }}
    .notes-box {{
      margin-top: 20px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px 16px;
    }}
    .notes-label {{
      font-size: 11px;
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }}
    .notes-text {{
      font-size: 13px;
      color: #334155;
      line-height: 1.5;
      white-space: pre-wrap;
    }}
    .footer {{
      padding: 20px 28px;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <span class="pill">Formal Quotation • {safe_quote_ref}</span>
      <div class="title">{safe_product_name}</div>
      <div class="subtitle">
        In response to ask from {safe_agent_name} ({safe_cust_company})
      </div>
    </div>

    <div class="content">
      <div class="greeting">
        Dear <strong>{safe_cust_name}</strong>,<br>
        <strong>{safe_vendor_company}</strong> (represented by {safe_vendor_delegate}) has prepared and submitted the following commercial quotation in response to your procurement inquiry:
      </div>

      <table class="spec-table">
        <tr>
          <td class="spec-label">Quoted Commodity</td>
          <td class="spec-value">{safe_product_name} {sku_badge}</td>
        </tr>
        <tr>
          <td class="spec-label">Offered Quantity</td>
          <td class="spec-value">{safe_quantity} {safe_unit}</td>
        </tr>
        <tr>
          <td class="spec-label">Unit Consideration</td>
          <td class="spec-value">{safe_currency} {safe_unit_price} / {safe_unit}</td>
        </tr>
        <tr>
          <td class="spec-label">Governing Incoterm</td>
          <td class="spec-value">{safe_incoterm}</td>
        </tr>
        <tr>
          <td class="spec-label">Delivery Timeline</td>
          <td class="spec-value">{lead_time_days} Calendar Days to {safe_location}</td>
        </tr>
        <tr>
          <td class="spec-label">Payment Terms</td>
          <td class="spec-value">{safe_payment}</td>
        </tr>
        <tr>
          <td class="spec-label">Quote Validity</td>
          <td class="spec-value">{validity_days} Days (Expires {safe_expiry})</td>
        </tr>
      </table>

      <div class="total-box">
        <div class="total-label">Total Commercial Consideration</div>
        <div class="total-amount">{safe_currency} {safe_total_value}</div>
      </div>

      <div class="notes-box">
        <div class="notes-label">Vendor Notes & Specifications:</div>
        <div class="notes-text">{safe_notes}</div>
      </div>
    </div>

    <div class="footer">
      This quotation was dispatched via <strong>Converge AI Conference Network</strong> on behalf of {safe_vendor_company}.<br>
      To respond or accept these terms, reply directly to this email or contact {safe_sender_email}.<br>
      Reference ID: <strong style="font-family: monospace;">{safe_quote_ref}</strong>
    </div>
  </div>
</body>
</html>
"""

    plain_text_content = f"""================================================================================
COMMERCIAL QUOTATION: {quote_reference}
Product: {product_name}
================================================================================

Dear {customer_name},

{vendor_company} ({vendor_delegate_name}) has submitted a formal commercial quotation in response to your procurement inquiry (initiated by {customer_agent_name or 'Procurement Agent'} for {customer_company}):

COMMERCIAL TERMS:
- Commodity: {product_name} {f'({product_code})' if product_code else ''}
- Quantity: {quantity} {unit}
- Unit Consideration: {currency} {unit_price} per {unit}
- Governing Incoterm: {incoterm}
- Delivery Location: {delivery_location}
- Delivery Timeline: {lead_time_days} Calendar Days
- Payment Settlement: {payment_terms}
- Quote Validity: {validity_days} Days (Expires {expiry_date_str})

TOTAL CONTRACT VALUE: {currency} {total_value}

VENDOR NOTES:
{commercial_notes or 'No additional notes provided.'}

--------------------------------------------------------------------------------
Dispatched via Converge AI Conference Network on behalf of {vendor_company}.
Sender Contact: {sender_email} | Ref: {quote_reference}
================================================================================
"""

    return html_content, plain_text_content
