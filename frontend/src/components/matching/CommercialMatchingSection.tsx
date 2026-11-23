import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { brochureApi } from '@/lib/api/brochures';
import {
  searchBusinessMatches,
  parseBusinessQuery,
  getMyActiveRequirements,
  getMyActiveOfferings,
} from '@/lib/api/business';
import {
  BusinessMatchCandidate,
  BusinessMatchSearchRequest,
  ParsedBusinessRequirement,
  BusinessRequirement,
  BusinessOffering,
} from '@/types/business';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { BusinessConnectionModal } from './BusinessConnectionModal';

export const CommercialMatchingSection: React.FC = () => {
  const navigate = useNavigate();
  const [searchIntent, setSearchIntent] = useState<'SUPPLIERS' | 'BUYERS'>('SUPPLIERS');
  const [selectedReqId, setSelectedReqId] = useState<string>('');
  const [selectedOffId, setSelectedOffId] = useState<string>('');
  const [rawQuery, setRawQuery] = useState<string>('');
  const [allowSubstitutes, setAllowSubstitutes] = useState<boolean>(false);
  const [parsedPreview, setParsedPreview] = useState<ParsedBusinessRequirement | null>(null);
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [activeCandidateBreakdown, setActiveCandidateBreakdown] = useState<string | null>(null);
  const [selectedCandidateForRfq, setSelectedCandidateForRfq] = useState<BusinessMatchCandidate | null>(null);

  // Load user's saved requirements (Buyer profile)
  const { data: myRequirements = [] } = useQuery<BusinessRequirement[]>({
    queryKey: ['myActiveRequirements'],
    queryFn: getMyActiveRequirements,
    retry: false,
  });

  // Load user's saved catalog offerings (Supplier/Vendor profile)
  const { data: myOfferings = [] } = useQuery<BusinessOffering[]>({
    queryKey: ['myActiveOfferings'],
    queryFn: getMyActiveOfferings,
    retry: false,
  });

  // Query published brochures directory for ecosystem discovery
  const { data: brochuresDirectory = [] } = useQuery({
    queryKey: ['brochuresDirectory'],
    queryFn: () => brochureApi.getDirectory(),
    staleTime: 60000,
  });

  // Mode B Commercial Search Query
  const {
    data: searchResults,
    isLoading: isSearching,
    isError: isSearchError,
    error: searchError,
    refetch: executeSearch,
  } = useQuery({
    queryKey: ['commercialMatches', searchIntent, selectedReqId, selectedOffId, rawQuery, allowSubstitutes],
    queryFn: () => {
      const payload: BusinessMatchSearchRequest = {
        allow_substitutes: allowSubstitutes,
        search_type: searchIntent,
        limit: 20,
      };
      if (searchIntent === 'SUPPLIERS') {
        if (selectedReqId) {
          payload.requirement_id = selectedReqId;
        } else if (rawQuery.trim()) {
          payload.query = rawQuery.trim();
        }
      } else {
        // BUYERS intent
        if (selectedOffId) {
          const off = myOfferings.find((o) => o.id === selectedOffId);
          if (off) {
            payload.query = off.custom_product_title;
            payload.product_code = off.product_code;
            payload.grade_code = off.grade_code;
            payload.service_code = off.service_code;
            payload.quantity_unit = off.capacity_unit;
          }
        } else if (rawQuery.trim()) {
          payload.query = rawQuery.trim();
        }
      }
      return searchBusinessMatches(payload);
    },
    enabled: Boolean(
      (searchIntent === 'SUPPLIERS' && (selectedReqId || rawQuery.trim())) ||
      (searchIntent === 'BUYERS' && (selectedOffId || rawQuery.trim()))
    ),
    retry: false,
    staleTime: 20000,
  });

  // Parse natural language query
  const handleParseQuery = async () => {
    if (!rawQuery.trim()) return;
    setIsParsing(true);
    try {
      const parsed = await parseBusinessQuery(rawQuery.trim());
      setParsedPreview(parsed);
    } catch (err) {
      console.error('Failed to parse query:', err);
    } finally {
      setIsParsing(false);
    }
  };

  // When saved requirement dropdown changes
  const handleSelectRequirement = (reqId: string) => {
    setSelectedReqId(reqId);
    if (reqId) {
      setRawQuery('');
      setParsedPreview(null);
    }
  };

  const handleStartConversation = (candidate: BusinessMatchCandidate) => {
    setSelectedCandidateForRfq(candidate);
  };

  return (
    <div className="space-y-6">
      {/* Intro Banner */}
      <div className="bg-canvas-surface border border-canvas-border rounded-xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">🏭</span>
            <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
              Commercial RFQ & Multi-Dimensional Sourcing
            </h2>
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              Mode B Active
            </span>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-3xl">
            Evaluate qualified suppliers, manufacturers, and industrial service providers across 5 dimensions: Product Taxonomy, Run-Rate Capacity, Uncommitted Volume, Delivery Feasibility & Data Freshness.
          </p>
        </div>
      </div>

      {/* Sourcing Query & Selection Box */}
      <div className="bg-canvas-surface border border-canvas-border rounded-xl p-4 sm:p-5 space-y-4">
        {/* Search Intent Toggle: Buyer looking for Suppliers vs Supplier/Vendor looking for Buyers */}
        <div className="flex items-center gap-2 p-1 bg-canvas-base border border-canvas-border rounded-lg w-fit text-xs">
          <button
            type="button"
            onClick={() => {
              setSearchIntent('SUPPLIERS');
              setSelectedOffId('');
              setRawQuery('');
              setParsedPreview(null);
            }}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              searchIntent === 'SUPPLIERS'
                ? 'bg-brass text-white shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            🔍 Find Suppliers & Vendors (Buyer Mode)
          </button>
          <button
            type="button"
            onClick={() => {
              setSearchIntent('BUYERS');
              setSelectedReqId('');
              setRawQuery('');
              setParsedPreview(null);
            }}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              searchIntent === 'BUYERS'
                ? 'bg-purple-600 text-white shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            🎯 Find Active Buyer Inquiries (Supplier/Vendor Mode)
          </button>
        </div>

        {/* Saved Requirements Selector (For Buyer Mode) */}
        {searchIntent === 'SUPPLIERS' && myRequirements.length > 0 && (
          <div>
            <label className="block text-xs font-semibold text-ink-primary mb-1">
              Select One of Your Saved Procurement Requirements:
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <select
                value={selectedReqId}
                onChange={(e) => handleSelectRequirement(e.target.value)}
                className="flex-1 px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              >
                <option value="">-- Choose a Saved Requirement --</option>
                {myRequirements.map((req) => {
                  const qty = req.required_quantity != null ? Number(req.required_quantity).toLocaleString() : null;
                  const unit = req.quantity_unit ? req.quantity_unit.replace(/_/g, ' ') : 'Units';
                  return (
                    <option key={req.id} value={req.id}>
                      {req.custom_requirement_title || req.product_code || req.service_code || 'Requirement'}{' '}
                      {qty ? `(${qty} ${unit})` : ''}{' '}
                      {req.delivery_city ? `→ ${req.delivery_city}` : ''}
                    </option>
                  );
                })}
              </select>
              {selectedReqId && (
                <button
                  type="button"
                  onClick={() => setSelectedReqId('')}
                  className="px-3 py-1.5 text-xs rounded-lg border border-canvas-border text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated"
                >
                  Clear Selection
                </button>
              )}
            </div>
          </div>
        )}

        {/* Saved Catalog Offerings Selector (For Supplier/Vendor Mode) */}
        {searchIntent === 'BUYERS' && myOfferings.length > 0 && (
          <div>
            <label className="block text-xs font-semibold text-ink-primary mb-1">
              Select One of Your Catalog Offerings to Find Matching Buyers:
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <select
                value={selectedOffId}
                onChange={(e) => {
                  setSelectedOffId(e.target.value);
                  if (e.target.value) {
                    setRawQuery('');
                    setParsedPreview(null);
                  }
                }}
                className="flex-1 px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-purple-600 focus:outline-none"
              >
                <option value="">-- Choose a Catalog Offering --</option>
                {myOfferings.map((off) => {
                  const cap = off.declared_monthly_capacity != null ? Number(off.declared_monthly_capacity).toLocaleString() : null;
                  const unit = off.capacity_unit ? off.capacity_unit.replace(/_/g, ' ') : 'Units';
                  return (
                    <option key={off.id} value={off.id}>
                      {off.custom_product_title || off.product_code || off.service_code || 'Offering'}{' '}
                      {cap ? `(${cap} ${unit}/mo)` : ''}
                    </option>
                  );
                })}
              </select>
              {selectedOffId && (
                <button
                  type="button"
                  onClick={() => setSelectedOffId('')}
                  className="px-3 py-1.5 text-xs rounded-lg border border-canvas-border text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated"
                >
                  Clear Selection
                </button>
              )}
            </div>
          </div>
        )}

        {/* Natural Language Input */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-semibold text-ink-primary">
              {searchIntent === 'BUYERS'
                ? (myOfferings.length > 0 ? 'Or Search Buyer Requirements by Keyword / Material:' : 'Search Buyer Requirements by Keyword / Material:')
                : (myRequirements.length > 0 ? 'Or Search by Natural Language Procurement Inquiry:' : 'Procurement Inquiry / Natural Language RFQ:')}
            </label>
            {rawQuery && (
              <button
                type="button"
                onClick={handleParseQuery}
                disabled={isParsing}
                className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
              >
                {isParsing ? 'Parsing...' : '✨ Preview NLP Parsing'}
              </button>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={rawQuery}
              disabled={searchIntent === 'SUPPLIERS' ? Boolean(selectedReqId) : Boolean(selectedOffId)}
              onChange={(e) => {
                setRawQuery(e.target.value);
                setParsedPreview(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  executeSearch();
                }
              }}
              placeholder={
                searchIntent === 'BUYERS'
                  ? (selectedOffId ? 'Using selected catalog offering above' : 'e.g. Limestone Calcined Clay Cement, bulk haulage, crane rental...')
                  : (selectedReqId ? 'Using selected saved requirement above' : 'e.g. Need 1000 MT LC3-50 low-carbon cement delivered to Pune within 45 days')
              }
              className="flex-1 px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary placeholder:text-ink-muted focus:border-brass focus:outline-none disabled:opacity-50"
            />
            <button
              type="button"
              disabled={searchIntent === 'SUPPLIERS' ? (!selectedReqId && !rawQuery.trim()) : (!selectedOffId && !rawQuery.trim())}
              onClick={() => executeSearch()}
              className={`px-4 py-2 text-xs font-semibold rounded-lg text-white transition-colors shadow-xs disabled:opacity-50 flex items-center justify-center gap-1.5 ${
                searchIntent === 'BUYERS' ? 'bg-purple-600 hover:bg-purple-700' : 'bg-brass hover:bg-brass/90'
              }`}
            >
              <span>{searchIntent === 'BUYERS' ? '🎯' : '🔍'}</span>
              <span>{searchIntent === 'BUYERS' ? 'Find Matching Buyers' : 'Find Qualified Suppliers'}</span>
            </button>
          </div>
        </div>

        {/* NLP Extraction Preview Pill Box */}
        {(parsedPreview || searchResults?.query_summary) && (
          <div className="bg-canvas-elevated border border-canvas-border rounded-lg p-3 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase font-mono tracking-wider text-ink-muted">
                NLP Query Extraction
              </span>
              <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                NLP Parsing Confidence: {Math.round(((parsedPreview || searchResults?.query_summary)?.confidence || 1.0) * 100)}%
              </span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              {((parsedPreview || searchResults?.query_summary)?.item_name || (parsedPreview || searchResults?.query_summary)?.matched_product_code) && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-canvas-base border border-canvas-border text-ink-primary font-medium">
                  🏷️ Item: <strong>{(parsedPreview || searchResults?.query_summary)?.item_name || (parsedPreview || searchResults?.query_summary)?.matched_product_code}</strong>
                </span>
              )}
              {(parsedPreview || searchResults?.query_summary)?.matched_grade_code && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-canvas-base border border-canvas-border text-ink-primary font-medium">
                  🔖 Grade: <strong>{(parsedPreview || searchResults?.query_summary)?.matched_grade_code}</strong>
                </span>
              )}
              {(parsedPreview || searchResults?.query_summary)?.quantity && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-canvas-base border border-canvas-border text-ink-primary font-medium">
                  ⚖️ Volume: <strong>{(parsedPreview || searchResults?.query_summary)?.quantity} {(parsedPreview || searchResults?.query_summary)?.quantity_unit || 'Units'}</strong>
                </span>
              )}
              {(parsedPreview || searchResults?.query_summary)?.destination_city && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-canvas-base border border-canvas-border text-ink-primary font-medium">
                  📍 Destination: <strong>{(parsedPreview || searchResults?.query_summary)?.destination_city}</strong>
                </span>
              )}
              {(parsedPreview || searchResults?.query_summary)?.target_timeline_days && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-canvas-base border border-canvas-border text-ink-primary font-medium">
                  ⏱️ Timeline: <strong>{(parsedPreview || searchResults?.query_summary)?.target_timeline_days} Days</strong>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Options Row */}
        <div className="flex items-center gap-2 pt-1 border-t border-canvas-border text-xs">
          <label className="flex items-center gap-2 cursor-pointer text-ink-secondary hover:text-ink-primary">
            <input
              type="checkbox"
              checked={allowSubstitutes}
              onChange={(e) => setAllowSubstitutes(e.target.checked)}
              className="rounded border-canvas-border text-brass focus:ring-brass"
            />
            <span>Include substitute materials / compatible industrial alternatives</span>
          </label>
        </div>
      </div>

      {/* Results Section */}
      {isSearching ? (
        <LoadingState message="Evaluating supplier run-rates, delivery feasibility, and uncommitted allocations..." />
      ) : isSearchError ? (
        <EmptyState
          emoji="⚠️"
          title="Matching Engine Error"
          description={searchError instanceof Error ? searchError.message : 'Could not execute commercial matching.'}
          action={
            <button
              type="button"
              onClick={() => executeSearch()}
              className="px-4 py-2 text-xs font-semibold rounded-md bg-canvas-elevated border border-canvas-border text-ink-primary hover:bg-canvas-sunken"
            >
              Retry Sourcing Search
            </button>
          }
        />
      ) : !searchResults || searchResults.candidates.length === 0 ? (
        <div className="max-w-2xl mx-auto py-8">
          <EmptyState
            emoji="🔍"
            title="No Matching Suppliers Found"
            description={
              selectedReqId || rawQuery
                ? 'No active suppliers or vendors meet the criteria for this inquiry. Try enabling substitute materials or adjusting delivery geography.'
                : 'Select one of your active procurement requirements or enter a query above to discover verified commercial suppliers.'
            }
          />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Candidates Summary Bar */}
          <div className="flex items-center justify-between text-xs text-ink-secondary border-b border-canvas-border pb-2">
            <span>
              Found <strong className="text-ink-primary">{searchResults.total_candidates}</strong> qualified commercial offering{searchResults.total_candidates !== 1 ? 's' : ''} evaluated across 5 dimensions
            </span>
            <span className="font-mono text-[11px] text-ink-muted">
              Mode B Multi-Dimensional Ranking
            </span>
          </div>

          {/* Candidate Offerings Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {searchResults.candidates.map((candidate) => {
              const score = Math.round(candidate.composite_score);
              const isBreakdownOpen = activeCandidateBreakdown === candidate.offering_id;

              return (
                <div
                  key={candidate.offering_id}
                  className="bg-canvas-surface border border-canvas-border rounded-xl p-5 space-y-4 shadow-xs hover:border-brass/50 transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Header: Role & Match Score */}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-primary">
                            {candidate.supplier_role === 'SUPPLIER'
                              ? '🏭 Supplier / Manufacturer'
                              : candidate.supplier_role === 'VENDOR'
                              ? '🛠️ Vendor / Service Provider'
                              : candidate.supplier_role === 'DISTRIBUTOR'
                              ? '📦 Distributor'
                              : '🤝 Commercial Partner'}
                          </span>
                          {candidate.supplier_hq_city && (
                            <span className="text-xs text-ink-muted">
                              📍 {candidate.supplier_hq_city}
                            </span>
                          )}
                        </div>
                        <h3 className="font-bold text-base text-ink-primary mt-1.5">
                          {candidate.supplier_company_name || 'Commercial Participant'}
                        </h3>
                        <p className="text-xs font-semibold text-brass mt-0.5">
                          {candidate.offering_title}
                        </p>
                      </div>

                      {/* Match Score Badge */}
                      <div className="flex flex-col items-end">
                        <div
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold font-mono tracking-tight shadow-xs ${
                            score >= 85
                              ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                              : score >= 70
                              ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                              : 'bg-canvas-elevated text-ink-secondary border border-canvas-border'
                          }`}
                        >
                          {score}% Match
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            setActiveCandidateBreakdown(
                              isBreakdownOpen ? null : (candidate.offering_id || candidate.requirement_id || candidate.business_profile_id)
                            )
                          }
                          className="text-[10px] text-ink-muted hover:text-ink-primary underline mt-1"
                        >
                          {isBreakdownOpen ? 'Hide Score Breakdown' : 'View 5-D Breakdown'}
                        </button>
                      </div>
                    </div>

                    {/* 5-Dimensional Score Breakdown Accordion */}
                    {isBreakdownOpen && (
                      <div className="mt-3 p-3 bg-canvas-elevated rounded-lg border border-canvas-border text-xs space-y-2">
                        <div className="text-[11px] font-semibold uppercase font-mono tracking-wider text-ink-muted">
                          5-Dimensional Decomposed Scoring:
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                          <div>
                            <div className="text-ink-muted">Product Match:</div>
                            <div className="font-mono font-bold text-ink-primary">
                              {Math.round(candidate.score_breakdown.product_relevance * 100)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-ink-muted">Capacity Run-Rate:</div>
                            <div className="font-mono font-bold text-ink-primary">
                              {Math.round(candidate.score_breakdown.capacity_feasibility * 100)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-ink-muted">Uncommitted Volume:</div>
                            <div className="font-mono font-bold text-ink-primary">
                              {Math.round(candidate.score_breakdown.commitment_confidence * 100)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-ink-muted">Delivery Feasibility:</div>
                            <div className="font-mono font-bold text-ink-primary">
                              {Math.round(candidate.score_breakdown.delivery_feasibility * 100)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-ink-muted">Data Freshness:</div>
                            <div className="font-mono font-bold text-ink-primary">
                              {Math.round(candidate.score_breakdown.verification_confidence * 100)}%
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Confidence Badges */}
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {candidate.confidence_badges.map((badge, idx) => {
                        const isWarning = badge.includes('Unverified') || badge.includes('Stale');
                        return (
                          <span
                            key={idx}
                            className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                              isWarning
                                ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800'
                                : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                            }`}
                          >
                            {badge}
                          </span>
                        );
                      })}
                      {candidate.offers_test_certificates && !candidate.confidence_badges.some((b) => b.includes('Certs')) && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                          📜 Mill / NABL Certs
                        </span>
                      )}
                    </div>

                    {/* Operational Details Grid */}
                    <div className="grid grid-cols-2 gap-3 mt-4 text-xs pt-3 border-t border-canvas-border">
                      <div>
                        <span className="text-ink-muted block text-[11px]">Declared Capacity:</span>
                        <span className="font-medium text-ink-primary">
                          {candidate.declared_monthly_capacity != null
                            ? `${candidate.declared_monthly_capacity.toLocaleString()} ${candidate.capacity_unit || 'Units'} / Mo`
                            : 'On Request'}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[11px]">Uncommitted Available:</span>
                        <span className="font-medium text-ink-primary">
                          {candidate.uncommitted_monthly_capacity != null
                            ? `${candidate.uncommitted_monthly_capacity.toLocaleString()} ${candidate.capacity_unit || 'Units'}`
                            : 'Unrecorded'}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[11px]">Lead Time:</span>
                        <span className="font-medium text-ink-primary">
                          {candidate.lead_time_days != null ? `${candidate.lead_time_days} Days` : 'Standard'}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[11px]">Indicative Pricing:</span>
                        <span className="font-medium text-ink-primary">
                          {candidate.indicative_price_display || 'Available on RFQ'}
                        </span>
                      </div>
                    </div>

                    {/* Geographic Coverage */}
                    {candidate.geographic_coverage && candidate.geographic_coverage.length > 0 && (
                      <div className="mt-3 text-xs">
                        <span className="text-ink-muted text-[11px]">Service / Delivery Coverage: </span>
                        <span className="text-ink-secondary">
                          {candidate.geographic_coverage.join(', ')}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions Bar */}
                  <div className="pt-4 border-t border-canvas-border flex flex-wrap items-center justify-between gap-3 mt-4">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-ink-muted">
                        🔒 Private Buyer Budget Preserved
                      </span>
                      {(() => {
                        const candidateBrochure = brochuresDirectory.find(
                          (b) =>
                            (candidate.supplier_company_name &&
                              b.company_name.toLowerCase() === candidate.supplier_company_name.toLowerCase()) ||
                            (candidate.business_profile_id && b.business_profile_id === candidate.business_profile_id)
                        );
                        if (!candidateBrochure) return null;
                        return (
                          <Link
                            to={`/brochures/${candidateBrochure.slug}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors"
                            title={`Open ${candidateBrochure.title} (Digital Flipbook)`}
                          >
                            <span>📖</span>
                            <span>View Digital Brochure ↗</span>
                          </Link>
                        );
                      })()}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleStartConversation(candidate)}
                      className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg text-white transition-colors shadow-xs flex items-center gap-1.5 ${
                        candidate.candidate_type === 'REQUIREMENT'
                          ? 'bg-purple-600 hover:bg-purple-700'
                          : 'bg-brass hover:bg-brass/90'
                      }`}
                    >
                      <span>💬</span>
                      <span>
                        {candidate.candidate_type === 'REQUIREMENT'
                          ? (candidate.supplier_role === 'DISTRIBUTOR' ? 'Propose Distribution Alliance' : 'Pitch Offering to Buyer')
                          : 'Initiate RFQ Discussion'}
                      </span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Commercial Connection & Brief Modal */}
      <BusinessConnectionModal
        isOpen={!!selectedCandidateForRfq}
        onClose={() => setSelectedCandidateForRfq(null)}
        candidate={selectedCandidateForRfq}
        requirement={myRequirements.find((r) => r.id === selectedReqId) || null}
        parsedQuery={parsedPreview || searchResults?.query_summary || null}
        onSuccess={(conversationId) => {
          setSelectedCandidateForRfq(null);
          navigate(`/conversations/${conversationId}`);
        }}
      />
    </div>
  );
};
