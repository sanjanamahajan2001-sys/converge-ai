/**
 * TypeScript contracts and Data Transfer Objects for the Quotes & Multi-Vendor RFQ System (Quote Subphase 5).
 */

export type QuoteUrgency = 'CRITICAL' | 'HIGH' | 'PLANNED' | 'FLEXIBLE';

export type VendorMatchStatus =
  | 'PENDING_REVIEW'
  | 'VIEWED'
  | 'QUOTE_SENT'
  | 'DECLINED'
  | 'EXPIRED';

export type QuoteRequestStatus =
  | 'BROADCAST'
  | 'MATCHED'
  | 'FULFILLED'
  | 'CANCELLED'
  | 'EXPIRED';

export type EmailDeliveryStatus =
  | 'PENDING'
  | 'SENT'
  | 'FAILED'
  | 'BOUNCED';

export interface CustomerSummary {
  id: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
  email?: string | null;
}

export interface VendorSummary {
  id: string;
  full_name: string;
  company_name?: string | null;
  job_title?: string | null;
}

export interface QuoteVendorPanelItem {
  match_id: string;
  quote_request_id: string;
  title: string;
  product_name: string;
  product_code?: string | null;
  quantity?: number | string | null;
  quantity_unit?: string | null;
  delivery_location?: string | null;
  timeline_days?: number | null;
  urgency: QuoteUrgency;
  status: VendorMatchStatus;
  match_score: number | string;
  match_reasons: string[];
  viewed_at?: string | null;
  created_at: string;
  customer: CustomerSummary;
  customer_agent_persona?: string | null;

  // Quoting Activity Summary
  dispatches_count: number;
  latest_quote_reference?: string | null;
  latest_quoted_value?: number | string | null;
  latest_quoted_currency?: string | null;
  latest_dispatched_at?: string | null;
}

export interface QuoteVendorPanelCounts {
  all: number;
  new_inquiries: number;
  quoted: number;
  declined: number;
}

export interface QuoteVendorPanelResponse {
  items: QuoteVendorPanelItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  counts: QuoteVendorPanelCounts;
}

export interface QuoteEmailDispatchDetail {
  id: string;
  quote_reference_number: string;
  unit_price: number | string;
  total_value: number | string;
  currency: string;
  incoterm: string;
  lead_time_days: number;
  validity_days: number;
  payment_terms: string;
  commercial_notes?: string | null;
  sender_email: string;
  recipient_email: string;
  delivery_status: EmailDeliveryStatus;
  sent_at: string;
}

export interface QuoteRequestDetail {
  id: string;
  match_id?: string | null;
  title: string;
  product_name: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity?: number | string | null;
  quantity_unit?: string | null;
  delivery_location?: string | null;
  timeline_days?: number | null;
  target_price_indication?: number | string | null;
  currency: string;
  is_budget_public: boolean;
  urgency: QuoteUrgency;
  status: QuoteRequestStatus;
  technical_specifications: Record<string, any>;
  inquiry_notes?: string | null;
  created_at: string;
  customer: CustomerSummary;
  customer_agent_persona?: string | null;

  // Vendor-specific perspective
  vendor_match_status?: VendorMatchStatus | null;
  match_score?: number | string | null;
  match_reasons?: string[] | null;
  dispatches: QuoteEmailDispatchDetail[];
}

export interface SendQuoteEmailRequest {
  unit_price: number;
  total_value: number;
  currency?: string;
  incoterm: string;
  lead_time_days: number;
  validity_days: number;
  payment_terms: string;
  commercial_notes?: string;
}

export interface SendQuoteEmailResponse {
  quote_reference_number: string;
  match_id: string;
  dispatch_id: string;
  recipient_email: string;
  sender_email: string;
  total_value: number;
  currency: string;
  delivery_status: EmailDeliveryStatus;
  sent_at: string;
  delivery_message: string;
}

export interface QuoteRequestCreate {
  conversation_id?: string | null;
  customer_agent_persona?: string;
  title: string;
  product_name: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity?: number;
  quantity_unit?: string;
  delivery_location?: string;
  timeline_days?: number;
  target_price_indication?: number;
  currency?: string;
  is_budget_public?: boolean;
  urgency?: QuoteUrgency;
  technical_specifications?: Record<string, any>;
  inquiry_notes?: string;
  target_vendor_ids?: string[];
}

// --- Admin Quotes Governance Types ---

export interface AdminQuoteDispatchItem {
  id: string;
  quote_reference_number: string;
  quote_request_id: string;
  quote_vendor_match_id: string;
  product_name: string;
  product_code?: string | null;
  quantity?: number | string | null;
  quantity_unit?: string | null;
  unit_price: number | string;
  total_value: number | string;
  currency: string;
  incoterm: string;
  lead_time_days: number;
  validity_days: number;
  payment_terms: string;
  commercial_notes?: string | null;

  vendor_id: string;
  vendor_name: string;
  vendor_company?: string | null;
  sender_email: string;

  customer_id: string;
  customer_name: string;
  customer_company?: string | null;
  recipient_email: string;

  email_subject: string;
  delivery_status: EmailDeliveryStatus;
  external_message_id?: string | null;
  error_message?: string | null;
  sent_at: string;
}

export interface AdminQuoteMetrics {
  total_dispatched: number;
  total_quoted_value: number | string;
  unique_vendors: number;
  unique_customers: number;
  sent_count: number;
  failed_count: number;
  delivery_rate_percent: number | string;
}

export interface AdminQuoteListResponse {
  items: AdminQuoteDispatchItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  metrics: AdminQuoteMetrics;
}

export interface AdminQuoteDetailResponse extends AdminQuoteDispatchItem {
  email_body_html: string;
}

