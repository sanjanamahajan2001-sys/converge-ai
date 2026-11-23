import React, { useState, useEffect } from 'react';
import {
  CommercialRole,
  ProposalCreateRequest,
  ProposalDetail,
  ProposalRevision,
  ProposalRevisionCreate,
  ProposalType,
} from '@/types/proposal';
import { proposalApi } from '@/lib/api/proposal';
import { formatUnit, cleanProposalTitle } from '@/lib/proposalUtils';

interface ProposalDraftModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'initial_draft' | 'counter_proposal';
  proposalId?: string;
  conversationId?: string;
  recipientId?: string;
  recipientName?: string;
  baseRevision?: ProposalRevision;
  onSuccess: (proposal: ProposalDetail) => void;
}

export const ProposalDraftModal: React.FC<ProposalDraftModalProps> = ({
  isOpen,
  onClose,
  mode,
  proposalId,
  conversationId,
  recipientId,
  recipientName,
  baseRevision,
  onSuccess,
}) => {
  // Form State
  const [title, setTitle] = useState('');
  const [proposalType, setProposalType] = useState<ProposalType>('SUPPLY_CONTRACT');
  const [proposerRole, setProposerRole] = useState<CommercialRole>('BUYER');
  const [recipientRole, setRecipientRole] = useState<CommercialRole>('SUPPLIER');
  const [validityDays, setValidityDays] = useState(7);

  const [productName, setProductName] = useState('');
  const [productCode, setProductCode] = useState('');
  const [quantity, setQuantity] = useState<number>(100);
  const [unit, setUnit] = useState('MT');
  const [unitPrice, setUnitPrice] = useState<number | ''>(8500);
  const [currency, setCurrency] = useState('INR');
  const [paymentTerms, setPaymentTerms] = useState('30% Advance, 70% against BL/Delivery');
  const [deliveryLocation, setDeliveryLocation] = useState('JNPT Port, Navi Mumbai');
  const [incoterm, setIncoterm] = useState('CIF');
  const [deliveryTimelineDays, setDeliveryTimelineDays] = useState(14);
  const [governingStandards, setGoverningStandards] = useState('ISO 9001:2015');
  const [specialConditions, setSpecialConditions] = useState('');
  const [notes, setNotes] = useState('');
  const [revisionSummary, setRevisionSummary] = useState('');

  // AI & Submission Status State
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [aiConfidence, setAiConfidence] = useState<number | null>(null);
  const [aiGroundingSource, setAiGroundingSource] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      if (mode === 'counter_proposal' && baseRevision) {
        setTitle(cleanProposalTitle(baseRevision.title) || `Counter-Offer: ${baseRevision.product_name}`);
        setProposalType(baseRevision.proposal_type || 'SUPPLY_CONTRACT');
        setProductName(baseRevision.product_name || '');
        setProductCode(baseRevision.product_code || '');
        setQuantity(parseFloat(String(baseRevision.quantity)) || 100);
        setUnit(formatUnit(baseRevision.unit) || 'MT');
        setUnitPrice(baseRevision.unit_price != null ? parseFloat(String(baseRevision.unit_price)) : '');
        setCurrency(baseRevision.currency || 'INR');
        setPaymentTerms(baseRevision.payment_terms || '');
        setDeliveryLocation(baseRevision.delivery_location || '');
        setIncoterm(baseRevision.incoterm || 'CIF');
        setDeliveryTimelineDays(baseRevision.delivery_timeline_days || 14);
        setGoverningStandards((baseRevision.governing_standards || []).join(', '));
        setSpecialConditions(baseRevision.special_conditions || '');
        setNotes(baseRevision.notes || '');
        setRevisionSummary('');
      } else {
        setTitle(productName ? `Commercial Agreement for ${productName}` : 'Commercial Agreement');
      }
    }
  }, [isOpen, mode, baseRevision]);

  if (!isOpen) return null;

  const totalValue =
    typeof unitPrice === 'number' && quantity > 0 ? unitPrice * quantity : null;

  const handleAiPrefill = async () => {
    if (!conversationId || !recipientId) {
      setErrorMessage('Active conversation context and recipient are required for AI auto-fill.');
      return;
    }

    setIsAiLoading(true);
    setErrorMessage(null);
    try {
      const res = await proposalApi.getProposalDraftPrefill({
        conversation_id: conversationId,
        recipient_id: recipientId,
      });

      const rev = res.suggested_revision;
      if (rev.title) setTitle(cleanProposalTitle(rev.title));
      if (rev.proposal_type) setProposalType(rev.proposal_type);
      if (res.proposer_role) setProposerRole(res.proposer_role);
      if (res.recipient_role) setRecipientRole(res.recipient_role);
      if (rev.product_name) setProductName(rev.product_name);
      if (rev.product_code) setProductCode(rev.product_code);
      if (rev.quantity) setQuantity(parseFloat(String(rev.quantity)));
      if (rev.unit) setUnit(formatUnit(rev.unit));
      if (rev.unit_price !== undefined && rev.unit_price !== null) setUnitPrice(parseFloat(String(rev.unit_price)));
      if (rev.currency) setCurrency(rev.currency);
      if (rev.payment_terms) setPaymentTerms(rev.payment_terms);
      if (rev.delivery_location) setDeliveryLocation(rev.delivery_location);
      if (rev.incoterm) setIncoterm(rev.incoterm);
      if (rev.delivery_timeline_days) setDeliveryTimelineDays(rev.delivery_timeline_days);
      if (rev.governing_standards && rev.governing_standards.length > 0) {
        setGoverningStandards(rev.governing_standards.join(', '));
      }
      if (rev.special_conditions) setSpecialConditions(rev.special_conditions);
      if (rev.notes) setNotes(rev.notes);

      setAiConfidence(Math.round((res.confidence_score || 0.85) * 100));
      setAiGroundingSource(res.grounding_source || 'Dialogue & Catalog Analysis');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to auto-fill draft with AI.');
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) {
      setErrorMessage('Product or service name is required.');
      return;
    }
    if (quantity <= 0) {
      setErrorMessage('Quantity must be greater than zero.');
      return;
    }
    if (!paymentTerms.trim()) {
      setErrorMessage('Payment terms are required.');
      return;
    }
    if (!deliveryLocation.trim()) {
      setErrorMessage('Delivery location or fulfillment jurisdiction is required.');
      return;
    }
    if (mode === 'counter_proposal' && !revisionSummary.trim()) {
      setErrorMessage('Please provide a brief revision summary explaining your counter-offer.');
      return;
    }

    const standardsList = governingStandards
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const revisionPayload: ProposalRevisionCreate = {
      title: title.trim() || `Commercial Agreement: ${productName}`,
      proposal_type: proposalType,
      product_name: productName.trim(),
      product_code: productCode.trim() || undefined,
      quantity,
      unit: unit.trim() || 'Units',
      unit_price: unitPrice === '' ? null : Number(unitPrice),
      currency: currency.trim() || 'INR',
      total_value: totalValue,
      payment_terms: paymentTerms.trim(),
      delivery_location: deliveryLocation.trim(),
      incoterm: incoterm || null,
      delivery_timeline_days: Number(deliveryTimelineDays) || 7,
      governing_standards: standardsList,
      special_conditions: specialConditions.trim() || null,
      notes: notes.trim() || null,
      revision_summary: mode === 'counter_proposal' ? revisionSummary.trim() : null,
    };

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (mode === 'initial_draft') {
        if (!recipientId) {
          throw new Error('Recipient delegate ID is required to submit proposal.');
        }
        const createPayload: ProposalCreateRequest = {
          conversation_id: conversationId || null,
          recipient_id: recipientId,
          proposer_role: proposerRole,
          recipient_role: recipientRole,
          validity_days: Number(validityDays) || 7,
          revision: revisionPayload,
        };
        const res = await proposalApi.createProposal(createPayload);
        onSuccess(res);
        onClose();
      } else {
        if (!proposalId) {
          throw new Error('Proposal ID is required for counter-offers.');
        }
        const res = await proposalApi.counterProposal(proposalId, {
          revision_summary: revisionSummary.trim(),
          revision: revisionPayload,
        });
        onSuccess(res);
        onClose();
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit proposal.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-ink-primary/70 backdrop-blur-xs overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="flex flex-col w-full h-full sm:h-auto sm:max-h-[92vh] sm:max-w-3xl sm:rounded-2xl bg-canvas-surface border-0 sm:border border-canvas-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 bg-canvas-elevated border-b border-canvas-border shrink-0">
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="text-xl sm:text-2xl" aria-hidden="true">
              {mode === 'counter_proposal' ? '🔄' : '📝'}
            </span>
            <div>
              <h3 id="modal-title" className="font-serif text-base sm:text-lg font-bold text-ink-primary">
                {mode === 'counter_proposal'
                  ? `Submit Counter-Offer (Rev ${(baseRevision?.revision_number || 1) + 1})`
                  : 'Draft Commercial Proposal'}
              </h3>
              <p className="text-xs text-ink-muted">
                {recipientName ? `With ${recipientName}` : 'Bilateral consensus contract draft'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-ink-muted hover:text-ink-primary hover:bg-canvas-sunken transition-colors"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form id="proposal-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {/* AI Auto-fill Banner for initial draft */}
          {mode === 'initial_draft' && conversationId && recipientId && (
            <div className="p-3.5 rounded-xl bg-brass-light/20 dark:bg-brass-light/10 border border-brass/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <span className="text-lg">✨</span>
                <div>
                  <h4 className="text-xs sm:text-sm font-semibold text-ink-primary">
                    AI Contract Grounding Engine
                  </h4>
                  <p className="text-[11px] sm:text-xs text-ink-secondary">
                    Auto-synthesize contract terms from your dialogue history and catalog offerings.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleAiPrefill}
                disabled={isAiLoading}
                className="w-full sm:w-auto px-3 py-1.5 rounded-lg bg-brass text-white text-xs font-semibold hover:bg-brass/90 transition-colors shadow-2xs flex items-center justify-center gap-1.5 shrink-0"
              >
                {isAiLoading ? (
                  <>
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Analyzing Dialogue...</span>
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    <span>Auto-fill from Dialogue</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* AI Confidence Pill if triggered */}
          {aiConfidence !== null && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs">
              <span className="font-bold">✓ Grounded</span>
              <span>•</span>
              <span>Source: {aiGroundingSource}</span>
              <span>•</span>
              <span className="font-semibold">{aiConfidence}% Confidence</span>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-700 text-rose-700 dark:text-rose-300 text-xs">
              {errorMessage}
            </div>
          )}

          {/* Counter-Proposal Summary Box */}
          {mode === 'counter_proposal' && (
            <div className="p-3.5 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-300/60 dark:border-amber-700/50 space-y-1.5">
              <label htmlFor="rev-summary" className="block text-xs font-bold text-amber-900 dark:text-amber-200">
                Revision Summary / Key Changes <span className="text-crimson">*</span>
              </label>
              <input
                id="rev-summary"
                type="text"
                required
                value={revisionSummary}
                onChange={(e) => setRevisionSummary(e.target.value)}
                placeholder="e.g. Adjusted unit price to ₹ 8,200/MT and accelerated delivery to 10 days"
                className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              />
            </div>
          )}

          {/* Agreement Basics Section */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              1. Agreement Basics & Classification
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Contract Title <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Supply Agreement for OPC 53 Grade Cement"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Contract Category
                </label>
                <select
                  value={proposalType}
                  onChange={(e) => setProposalType(e.target.value as ProposalType)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                >
                  <option value="SUPPLY_CONTRACT">Supply Contract</option>
                  <option value="PROCUREMENT_ORDER">Procurement Order</option>
                  <option value="DISTRIBUTION_AGREEMENT">Distribution Agreement</option>
                  <option value="SERVICE_MOU">Service MOU</option>
                  <option value="STRATEGIC_PARTNERSHIP">Strategic Partnership</option>
                </select>
              </div>
            </div>

            {mode === 'initial_draft' && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary mb-1">
                    Your Commercial Role
                  </label>
                  <select
                    value={proposerRole}
                    onChange={(e) => setProposerRole(e.target.value as CommercialRole)}
                    className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                  >
                    <option value="BUYER">Buyer / Procurer</option>
                    <option value="SUPPLIER">Supplier / Manufacturer</option>
                    <option value="DISTRIBUTOR">Distributor</option>
                    <option value="PARTNER">Partner</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary mb-1">
                    Recipient Role
                  </label>
                  <select
                    value={recipientRole}
                    onChange={(e) => setRecipientRole(e.target.value as CommercialRole)}
                    className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                  >
                    <option value="SUPPLIER">Supplier / Manufacturer</option>
                    <option value="BUYER">Buyer / Procurer</option>
                    <option value="DISTRIBUTOR">Distributor</option>
                    <option value="PARTNER">Partner</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary mb-1">
                    Validity Period (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={validityDays}
                    onChange={(e) => setValidityDays(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Commercial Quantities & Financials Section */}
          <div className="space-y-3 pt-2 border-t border-canvas-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              2. Commercial Scope & Pricing
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Product / Commodity / Service <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="e.g. TMT Steel Rebars Fe 550D"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Product / SKU Code (Optional)
                </label>
                <input
                  type="text"
                  value={productCode}
                  onChange={(e) => setProductCode(e.target.value)}
                  placeholder="e.g. ASTM-A615-GR60"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Quantity <span className="text-crimson">*</span>
                </label>
                <input
                  type="number"
                  min="0.001"
                  step="any"
                  required
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Unit <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="MT, Units, Kg..."
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Unit Price
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="e.g. 52000"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="AED">AED (د.إ)</option>
                  <option value="SGD">SGD (S$)</option>
                </select>
              </div>
            </div>

            {/* Total Value Pill */}
            {totalValue !== null && (
              <div className="p-2.5 rounded-lg bg-canvas-elevated border border-canvas-border flex items-center justify-between text-xs">
                <span className="text-ink-secondary">Computed Total Agreement Value:</span>
                <span className="font-mono font-bold text-ink-primary text-sm sm:text-base">
                  {currency} {totalValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
              </div>
            )}
          </div>

          {/* Logistics & Delivery Section */}
          <div className="space-y-3 pt-2 border-t border-canvas-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              3. Fulfillment, Delivery & Payment
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Delivery Location / Port <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={deliveryLocation}
                  onChange={(e) => setDeliveryLocation(e.target.value)}
                  placeholder="e.g. JNPT Port, Navi Mumbai, India"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Incoterm
                </label>
                <select
                  value={incoterm}
                  onChange={(e) => setIncoterm(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                >
                  <option value="CIF">CIF (Cost, Insurance & Freight)</option>
                  <option value="FOB">FOB (Free on Board)</option>
                  <option value="EXW">EXW (Ex Works)</option>
                  <option value="DAP">DAP (Delivered at Place)</option>
                  <option value="CFR">CFR (Cost and Freight)</option>
                  <option value="DDP">DDP (Delivered Duty Paid)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Delivery Timeline (Days) <span className="text-crimson">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={deliveryTimelineDays}
                  onChange={(e) => setDeliveryTimelineDays(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-ink-secondary mb-1">
                  Payment Terms <span className="text-crimson">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  placeholder="e.g. 30% Advance, 70% against BL or LC at Sight"
                  className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
            </div>
          </div>

          {/* Standards & Notes Section */}
          <div className="space-y-3 pt-2 border-t border-canvas-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              4. Governing Standards & Special Conditions
            </h4>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Governing Standards (Comma-separated)
              </label>
              <input
                type="text"
                value={governingStandards}
                onChange={(e) => setGoverningStandards(e.target.value)}
                placeholder="e.g. ISO 9001:2015, ASTM A36, BIS IS 1786"
                className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Special Conditions (Optional)
              </label>
              <textarea
                rows={2}
                value={specialConditions}
                onChange={(e) => setSpecialConditions(e.target.value)}
                placeholder="e.g. Third-party SGS inspection at loading port mandatory"
                className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Internal Commercial Notes (Optional)
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional contract notes or caveats..."
                className="w-full px-3 py-2 rounded-lg bg-canvas-surface border border-canvas-border text-sm text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              />
            </div>
          </div>
        </form>

        {/* Sticky Mobile/Desktop Action Bar */}
        <div className="px-4 sm:px-6 py-3 bg-canvas-elevated border-t border-canvas-border shrink-0 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg border border-canvas-border text-xs sm:text-sm font-semibold text-ink-secondary hover:bg-canvas-sunken transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="proposal-form"
            disabled={isSubmitting}
            className="px-5 py-2 rounded-lg bg-brass text-white text-xs sm:text-sm font-semibold hover:bg-brass/90 transition-colors shadow-xs flex items-center gap-1.5"
          >
            {isSubmitting ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Transacting...</span>
              </>
            ) : mode === 'counter_proposal' ? (
              <>
                <span>🔄</span>
                <span>Submit Counter-Offer</span>
              </>
            ) : (
              <>
                <span>🚀</span>
                <span>Submit Formal Proposal</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
