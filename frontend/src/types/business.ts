export interface ProductGradeDTO {
  grade_code: string;
  product_code: string;
  grade_name: string;
  governing_standard?: string | null;
  aliases: string[];
}

export interface CanonicalProductDTO {
  product_code: string;
  category_code: string;
  canonical_name: string;
  substitute_product_codes: string[];
  grades: ProductGradeDTO[];
}

export interface ProductTaxonomyDTO {
  category_code: string;
  sector_code: string;
  canonical_name: string;
  standard_units: string[];
  canonical_products: CanonicalProductDTO[];
}

export interface ServiceTaxonomyDTO {
  service_code: string;
  category_code: string;
  canonical_name: string;
  description?: string | null;
}

export interface BusinessOffering {
  id: string;
  business_profile_id: string;
  custom_product_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  specifications_text?: string | null;
  declared_monthly_capacity?: number | string | null;
  declared_committed_volume?: number | string | null;
  capacity_unit?: string | null;
  minimum_order_quantity?: number | string | null;
  lead_time_days?: number | null;
  geographic_coverage: string[];
  offers_test_certificates: boolean;
  vendor_certifications: string[];
  open_to_distribution: boolean;
  target_distribution_regions: string[];
  distributor_tier_preferred?: string | null;
  is_public_indicative: boolean;
  indicative_price_min?: number | string | null;
  indicative_price_max?: number | string | null;
  price_currency: string;
  pricing_basis?: string | null;
  offers_delivered_pricing: boolean;
  quote_validity_days: number;
  is_active: boolean;
  price_last_confirmed_at?: string | null;
  capacity_last_confirmed_at?: string | null;
  is_capacity_stale: boolean;
  is_price_stale: boolean;
  reconfirmation_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusinessOfferingInput {
  custom_product_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  specifications_text?: string | null;
  declared_monthly_capacity?: number | null;
  declared_committed_volume?: number | null;
  capacity_unit?: string | null;
  minimum_order_quantity?: number | null;
  lead_time_days?: number | null;
  geographic_coverage?: string[];
  offers_test_certificates?: boolean;
  vendor_certifications?: string[];
  open_to_distribution?: boolean;
  target_distribution_regions?: string[];
  distributor_tier_preferred?: string | null;
  is_public_indicative?: boolean;
  indicative_price_min?: number | null;
  indicative_price_max?: number | null;
  price_currency?: string;
  pricing_basis?: string | null;
  offers_delivered_pricing?: boolean;
  quote_validity_days?: number;
}

export interface BusinessRequirement {
  id: string;
  business_profile_id: string;
  custom_requirement_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  required_quantity?: number | string | null;
  quantity_unit?: string | null;
  delivery_city?: string | null;
  delivery_country?: string | null;
  target_timeline_days?: number | null;
  target_budget_indication?: number | string | null;
  is_budget_public: boolean;
  urgency: 'IMMEDIATE' | 'PLANNED' | 'EXPLORATORY';
  excluded_supplier_ids: string[];
  allow_substitutes: boolean;
  required_certifications: string[];
  is_feedstock_procurement: boolean;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusinessRequirementInput {
  custom_requirement_title?: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  required_quantity?: number | null;
  quantity_unit?: string | null;
  delivery_city?: string | null;
  delivery_country?: string | null;
  target_timeline_days?: number | null;
  target_budget_indication?: number | null;
  is_budget_public?: boolean;
  urgency?: 'IMMEDIATE' | 'PLANNED' | 'EXPLORATORY';
  excluded_supplier_ids?: string[];
  allow_substitutes?: boolean;
  required_certifications?: string[];
  is_feedstock_procurement?: boolean;
  notes?: string | null;
}

export interface BusinessProfile {
  id: string;
  user_id: string;
  is_buyer: boolean;
  is_supplier: boolean;
  is_vendor: boolean;
  is_distributor: boolean;
  is_partner: boolean;
  allow_business_matching: boolean;
  company_name?: string | null;
  industry?: string | null;
  business_website?: string | null;
  hq_city?: string | null;
  hq_country?: string | null;
  company_bio?: string | null;
  distributor_territories: string[];
  warehousing_capacity_sqft?: number | string | null;
  retail_dealer_count?: number | null;
  partnership_types: string[];
  partnership_interests: string[];
  offerings: BusinessOffering[];
  requirements: BusinessRequirement[];
  created_at: string;
  updated_at: string;
}

export interface BusinessProfileUpdate {
  is_buyer: boolean;
  is_supplier: boolean;
  is_vendor: boolean;
  is_distributor: boolean;
  is_partner: boolean;
  allow_business_matching: boolean;
  company_name?: string | null;
  industry?: string | null;
  business_website?: string | null;
  hq_city?: string | null;
  hq_country?: string | null;
  company_bio?: string | null;
  distributor_territories?: string[];
  warehousing_capacity_sqft?: number | null;
  retail_dealer_count?: number | null;
  partnership_types?: string[];
  partnership_interests?: string[];
}

export interface ScoreBreakdown {
  product_relevance: number;
  capacity_feasibility: number;
  commitment_confidence: number;
  delivery_feasibility: number;
  verification_confidence: number;
}

export interface ParsedBusinessRequirement {
  raw_query: string;
  item_name?: string | null;
  matched_product_code?: string | null;
  matched_grade_code?: string | null;
  matched_service_code?: string | null;
  quantity?: number | null;
  quantity_unit?: string | null;
  destination_city?: string | null;
  target_timeline_days?: number | null;
  inquiry_type: string;
  confidence: number;
}

export interface BusinessMatchCandidate {
  offering_id?: string | null;
  requirement_id?: string | null;
  candidate_type?: 'OFFERING' | 'REQUIREMENT';
  business_profile_id: string;
  supplier_user_id: string;
  supplier_company_name?: string | null;
  supplier_industry?: string | null;
  supplier_hq_city?: string | null;
  supplier_role: string;
  offering_title: string;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  composite_score: number;
  score_breakdown: ScoreBreakdown;
  declared_monthly_capacity?: number | null;
  capacity_unit?: string | null;
  uncommitted_monthly_capacity?: number | null;
  lead_time_days?: number | null;
  geographic_coverage: string[];
  offers_test_certificates: boolean;
  confidence_badges: string[];
  indicative_price_display?: string | null;
  pricing_basis?: string | null;
  price_currency: string;
  destination_city?: string | null;
  target_timeline_days?: number | null;
  required_quantity?: number | null;
}

export interface BusinessMatchSearchRequest {
  requirement_id?: string | null;
  query?: string | null;
  item_name?: string | null;
  product_code?: string | null;
  grade_code?: string | null;
  service_code?: string | null;
  quantity?: number | null;
  quantity_unit?: string | null;
  delivery_city?: string | null;
  target_timeline_days?: number | null;
  allow_substitutes?: boolean;
  search_type?: 'SUPPLIERS' | 'BUYERS';
  limit?: number;
  offset?: number;
}

export interface BusinessMatchSearchResponse {
  total_candidates: number;
  query_summary?: ParsedBusinessRequirement | null;
  candidates: BusinessMatchCandidate[];
}
