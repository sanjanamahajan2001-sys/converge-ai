/**
 * TypeScript data contracts and types for Proposal Generation & Dual-Sided Approval.
 *
 * Enforces zero contact leakage invariant:
 * Direct contact credentials (email, phone, etc.) are only defined and non-null
 * when proposal status is 'MUTUALLY_APPROVED'.
 */

export type ProposalStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'MUTUALLY_APPROVED'
  | 'REJECTED'
  | 'REVISED'
  | 'WITHDRAWN'
  | 'EXPIRED';

export type CommercialRole =
  | 'BUYER'
  | 'SUPPLIER'
  | 'VENDOR'
  | 'DISTRIBUTOR'
  | 'PARTNER';

export type ProposalType =
  | 'SUPPLY_CONTRACT'
  | 'PROCUREMENT_ORDER'
  | 'DISTRIBUTION_AGREEMENT'
  | 'SERVICE_MOU'
  | 'STRATEGIC_PARTNERSHIP';

export type ApprovalAction =
  | 'APPROVED'
  | 'REJECTED'
  | 'WITHDRAWN';

export interface ProposalPartySummary {
  user_id: string;
  full_name: string;
  company_name?: string | null;
  designation?: string | null;
  role: CommercialRole;
}

export interface DisclosedContactCredentials {
  user_id: string;
  full_name: string;
  company_name?: string | null;
  designation?: string | null;
  email: string;
  phone_number: string;
  hq_city?: string | null;
  corporate_website?: string | null;
  tax_id_or_registration?: string | null;
  verification_receipt_hash?: string | null;
  disclosed_at: string;
}

export interface ProposalRevisionBase {
  title: string;
  proposal_type: ProposalType;
  product_name: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity: number;
  unit: string;
  unit_price?: number | null;
  currency: string;
  total_value?: number | null;
  payment_terms: string;
  delivery_location: string;
  incoterm?: string | null;
  delivery_timeline_days: number;
  governing_standards?: string[];
  special_conditions?: string | null;
  notes?: string | null;
  revision_summary?: string | null;
}

export type ProposalRevisionCreate = ProposalRevisionBase;

export interface ProposalRevision extends ProposalRevisionBase {
  id: string;
  proposal_id: string;
  revision_number: number;
  author_id: string;
  author_name?: string | null;
  author_company?: string | null;
  created_at: string;
}

export interface ProposalApprovalRecord {
  id: string;
  proposal_id: string;
  revision_id: string;
  revision_number: number;
  user_id: string;
  user_name?: string | null;
  action: ApprovalAction;
  notes?: string | null;
  ip_address?: string | null;
  created_at: string;
}

export interface ProposalCreateRequest {
  conversation_id?: string | null;
  recipient_id: string;
  proposer_role: CommercialRole;
  recipient_role: CommercialRole;
  validity_days: number;
  revision: ProposalRevisionCreate;
}

export interface CounterProposalRequest {
  revision_summary: string;
  revision: ProposalRevisionCreate;
}

export interface ProposalApprovalRequest {
  notes?: string | null;
}

export interface ProposalRejectionRequest {
  reason: string;
}

export interface ProposalDraftPrefillRequest {
  conversation_id: string;
  recipient_id: string;
}

export interface ProposalDraftPrefillResponse {
  conversation_id: string;
  recipient_id: string;
  proposer_role: CommercialRole;
  recipient_role: CommercialRole;
  suggested_revision: ProposalRevisionCreate;
  grounding_source: string;
  confidence_score: number;
}

export interface ProposalListItem {
  id: string;
  conversation_id?: string | null;
  proposer_id: string;
  proposer_name: string;
  proposer_company?: string | null;
  proposer_role: CommercialRole;
  recipient_id: string;
  recipient_name: string;
  recipient_company?: string | null;
  recipient_role: CommercialRole;
  proposal_type: ProposalType;
  status: ProposalStatus;
  current_revision_number: number;
  current_title: string;
  product_name: string;
  quantity: number;
  unit: string;
  total_value?: number | null;
  currency: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
  concluded_at?: string | null;
  user_is_proposer: boolean;
  requires_user_action: boolean;
  contacts_disclosed: boolean;
}

export interface ProposalDetail {
  id: string;
  conversation_id?: string | null;
  proposer: ProposalPartySummary;
  recipient: ProposalPartySummary;
  proposal_type: ProposalType;
  status: ProposalStatus;
  current_revision_number: number;
  active_revision: ProposalRevision;
  revisions: ProposalRevision[];
  approvals: ProposalApprovalRecord[];
  expires_at: string;
  created_at: string;
  updated_at: string;
  concluded_at?: string | null;
  user_is_proposer: boolean;
  requires_user_action: boolean;
  contacts_disclosed: boolean;
  disclosed_credentials?: DisclosedContactCredentials | null;
  rejection_reason?: string | null;
}

// --- Admin Portal DTOs ---

export interface AdminProposalFilter {
  status?: ProposalStatus | null;
  proposal_type?: ProposalType | null;
  search?: string | null;
  page: number;
  page_size: number;
}

export interface AdminProposalListItem {
  id: string;
  conversation_id?: string | null;
  proposer_id: string;
  proposer_name: string;
  proposer_company?: string | null;
  proposer_role: CommercialRole;
  recipient_id: string;
  recipient_name: string;
  recipient_company?: string | null;
  recipient_role: CommercialRole;
  proposal_type: ProposalType;
  status: ProposalStatus;
  current_revision_number: number;
  total_revisions_count: number;
  current_title: string;
  product_name: string;
  total_value?: number | null;
  currency: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
  concluded_at?: string | null;
  approvals_count: number;
}

export interface AdminProposalListResponse {
  items: AdminProposalListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  status_counts: Record<string, number>;
}

// --- Revision Diff DTOs ---

export interface ProposalDiffFieldChange {
  field: string;
  field_label: string;
  old_value: any;
  new_value: any;
  change_type: 'MODIFIED' | 'ADDED' | 'REMOVED' | 'UNCHANGED';
  numeric_delta?: number | null;
  formatted_change?: string | null;
}

export interface ProposalRevisionDiffResponse {
  proposal_id: string;
  from_revision_number: number;
  to_revision_number: number;
  from_author_name?: string | null;
  to_author_name?: string | null;
  from_created_at?: string | null;
  to_created_at?: string | null;
  changes: ProposalDiffFieldChange[];
  has_price_change: boolean;
  has_quantity_change: boolean;
  has_timeline_change: boolean;
  has_delivery_change: boolean;
}
