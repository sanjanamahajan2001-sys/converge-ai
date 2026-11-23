import React, { useState } from 'react';
import { QuoteVendorPanelItem, QuoteRequestDetail, SendQuoteEmailResponse } from '@/types/quote';
import { quoteApi } from '@/lib/api/quote';
import { formatQuantity, formatUnit, formatCurrencyValue } from '@/lib/proposalUtils';

interface SendQuoteEmailModalProps {
  ask: QuoteVendorPanelItem | QuoteRequestDetail | any;
  conversationId?: string;
  onClose: () => void;
  onSuccess: (res: SendQuoteEmailResponse) => void;
}

export const SendQuoteEmailModal: React.FC<SendQuoteEmailModalProps> = ({
  ask,
  conversationId,
  onClose,
  onSuccess,
}) => {
  const matchId = 'match_id' in ask && ask.match_id ? ask.match_id : '';
  const qtyNum = ask.quantity ? parseFloat(String(ask.quantity)) : 1000;
  const unitLabel = formatUnit(ask.quantity_unit || 'MT');
  const initialCurrency = 'currency' in ask && ask.currency ? ask.currency : 'INR';

  const [activeTab, setActiveTab] = useState<'form' | 'preview'>('form');
  const [unitPrice, setUnitPrice] = useState<number>(3500);
  const [currency, setCurrency] = useState<string>(initialCurrency);
  const [incoterm, setIncoterm] = useState<string>('EXW');
  const [leadTimeDays, setLeadTimeDays] = useState<number>(ask.timeline_days || 18);
  const [validityDays, setValidityDays] = useState<number>(14);
  const [paymentTerms, setPaymentTerms] = useState<string>(
    '20% Advance, 80% Delivery against Proforma'
  );
  const [commercialNotes, setCommercialNotes] = useState<string>(
    'Third-party lab quality certificate included per 50 MT batch.'
  );

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const totalValue = Math.round(unitPrice * qtyNum * 100) / 100;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!matchId && !conversationId) {
      setErrorMessage('Missing vendor match or conversation identifier.');
      return;
    }
    if (unitPrice <= 0) {
      setErrorMessage('Please specify a positive unit price.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const payload = {
        unit_price: unitPrice,
        total_value: totalValue,
        currency,
        incoterm,
        lead_time_days: leadTimeDays,
        validity_days: validityDays,
        payment_terms: paymentTerms,
        commercial_notes: commercialNotes,
      };

      const res = conversationId
        ? await quoteApi.sendDirectQuoteFromConversation(conversationId, payload)
        : await quoteApi.sendQuoteEmail(matchId, payload);

      onSuccess(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to dispatch quote email. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const expiryDate = new Date(Date.now() + validityDays * 86400000).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto"
      data-testid="send-quote-email-modal"
    >
      <div className="bg-canvas-surface border border-canvas-border rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden my-6">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-canvas-border flex items-center justify-between bg-canvas-elevated">
          <div className="flex items-center gap-2.5">
            <span className="text-xl sm:text-2xl">✉️</span>
            <div>
              <h2 className="font-serif text-base sm:text-lg font-bold text-ink-primary">
                Send Quotation via Email
              </h2>
              <p className="text-xs text-ink-muted">
                Off-platform commercial quotation delivered to {ask.customer.full_name} ({ask.customer.company_name || 'Buyer'})
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-muted hover:text-ink-primary p-1.5 rounded-lg text-sm"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Tab Toggle: Formulate vs Email Live Preview */}
        <div className="flex border-b border-canvas-border bg-canvas-surface px-4 pt-2 gap-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('form')}
            className={`pb-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'form'
                ? 'border-brass text-brass'
                : 'border-transparent text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <span>📝</span>
            <span>Quotation Terms</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('preview')}
            className={`pb-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'preview'
                ? 'border-brass text-brass'
                : 'border-transparent text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <span>👁️</span>
            <span>Live Email Preview</span>
          </button>
        </div>

        {errorMessage && (
          <div className="mx-4 sm:mx-6 mt-4 p-3 rounded-lg bg-rose-50 border border-rose-300 text-xs text-rose-700">
            {errorMessage}
          </div>
        )}

        {/* Tab 1: Formulate Commercial Terms */}
        {activeTab === 'form' ? (
          <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Ask Summary Strip */}
            <div className="p-3 rounded-xl bg-canvas-elevated/70 border border-canvas-border flex flex-wrap items-center justify-between gap-2 text-xs">
              <div>
                <span className="block text-[10px] uppercase font-mono text-ink-muted">Inquired Commodity</span>
                <span className="font-bold text-ink-primary">{ask.product_name}</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-mono text-ink-muted">Requested Quantity</span>
                <span className="font-bold text-ink-primary">
                  {formatQuantity(ask.quantity)} {unitLabel}
                </span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-mono text-ink-muted">Destination Location</span>
                <span className="font-semibold text-ink-primary">{ask.delivery_location || 'Not Specified'}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
              {/* Unit Price */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Unit Consideration ({currency} / {unitLabel}) *
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={unitPrice}
                    onChange={(e) => setUnitPrice(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                  />
                </div>
              </div>

              {/* Currency */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Commercial Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                >
                  <option value="INR">INR (₹) — Indian Rupee</option>
                  <option value="USD">USD ($) — US Dollar</option>
                  <option value="EUR">EUR (€) — Euro</option>
                  <option value="AED">AED (د.إ) — UAE Dirham</option>
                </select>
              </div>

              {/* Incoterm */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Governing Incoterm
                </label>
                <select
                  value={incoterm}
                  onChange={(e) => setIncoterm(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                >
                  <option value="EXW">EXW — Ex Works (Factory Yard)</option>
                  <option value="FOB">FOB — Free On Board (Origin Port)</option>
                  <option value="CIF">CIF — Cost, Insurance & Freight</option>
                  <option value="DDP">DDP — Delivered Duty Paid (Jobsite)</option>
                  <option value="CIP">CIP — Carriage and Insurance Paid</option>
                </select>
              </div>

              {/* Lead Time */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Delivery Lead Time (Calendar Days) *
                </label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={leadTimeDays}
                  onChange={(e) => setLeadTimeDays(parseInt(e.target.value, 10) || 1)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>

              {/* Validity Days */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Quote Validity Window (Days) *
                </label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={validityDays}
                  onChange={(e) => setValidityDays(parseInt(e.target.value, 10) || 1)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>

              {/* Payment Terms */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                  Payment Settlement Terms *
                </label>
                <input
                  type="text"
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
                />
              </div>
            </div>

            {/* Total Computed Value Highlight */}
            <div className="p-3.5 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 flex items-center justify-between">
              <div>
                <span className="block text-[10px] font-mono uppercase font-bold text-amber-800 dark:text-amber-300">
                  Total Commercial Consideration
                </span>
                <span className="text-xs text-ink-secondary">
                  {formatQuantity(qtyNum)} {unitLabel} × {currency} {unitPrice.toLocaleString()}
                </span>
              </div>
              <div className="text-right">
                <span className="font-mono text-base sm:text-lg font-extrabold text-ink-primary">
                  {formatCurrencyValue(totalValue, currency)}
                </span>
              </div>
            </div>

            {/* Commercial Notes / Quality Specifications */}
            <div>
              <label className="block text-[11px] font-semibold text-ink-primary mb-1">
                Vendor Notes, Quality Assurances & Batch Specifications
              </label>
              <textarea
                rows={3}
                value={commercialNotes}
                onChange={(e) => setCommercialNotes(e.target.value)}
                placeholder="Include certification details, testing reports, batch dispatch schedules..."
                className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass resize-none"
              />
            </div>

            {/* Footer Buttons */}
            <div className="pt-2 border-t border-canvas-border flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-canvas-border bg-canvas-elevated text-xs font-semibold text-ink-secondary hover:text-ink-primary transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <span>{isSubmitting ? '✉️ Dispatching...' : '✉️ Send Quote via Email'}</span>
              </button>
            </div>
          </form>
        ) : (
          /* Tab 2: Live HTML Email Preview */
          <div className="p-4 sm:p-6 space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="text-[11px] text-ink-muted flex items-center justify-between">
              <span>Previewing branded customer quotation email:</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400">✓ Google SMTP Verified</span>
            </div>

            <div className="border border-slate-200 dark:border-slate-700 rounded-xl bg-white text-slate-800 p-5 space-y-4 shadow-sm text-xs font-sans">
              <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
                <div>
                  <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                    Commercial Quotation • QUO-2026-DRAFT
                  </span>
                  <h3 className="font-bold text-sm text-slate-900 mt-1">{ask.product_name}</h3>
                  <p className="text-[11px] text-slate-500">
                    In response to ask by {ask.customer_agent_persona || 'Procurement AI Agent'} ({ask.customer.company_name || 'Buyer'})
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-mono text-slate-400">SOFUELED RELAY</span>
                </div>
              </div>

              <div className="space-y-1.5 text-xs text-slate-700">
                <p>Dear {ask.customer.full_name},</p>
                <p>A formal commercial quotation has been prepared in response to your procurement inquiry:</p>
              </div>

              <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 block">Quoted Commodity</span>
                  <span className="font-semibold text-slate-900">{ask.product_name}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Offered Quantity</span>
                  <span className="font-semibold text-slate-900">
                    {formatQuantity(qtyNum)} {unitLabel}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Unit Consideration</span>
                  <span className="font-semibold text-slate-900">
                    {currency} {unitPrice.toLocaleString()} / {unitLabel}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Governing Incoterm</span>
                  <span className="font-semibold text-slate-900">{incoterm}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Delivery Timeline</span>
                  <span className="font-semibold text-slate-900">
                    {leadTimeDays} Calendar Days to {ask.delivery_location || 'Customer Site'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Quote Validity</span>
                  <span className="font-semibold text-slate-900">
                    {validityDays} Days (Expires {expiryDate})
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200 flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase font-bold text-amber-900">
                  Total Commercial Consideration
                </span>
                <span className="font-mono text-base font-extrabold text-slate-900">
                  {formatCurrencyValue(totalValue, currency)}
                </span>
              </div>

              {commercialNotes && (
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                  <span className="font-bold text-slate-700 block mb-1 text-[11px] uppercase">
                    Vendor Notes & Batch Specifications:
                  </span>
                  <p className="text-slate-600">{commercialNotes}</p>
                </div>
              )}

              <div className="border-t border-slate-100 pt-3 text-[10px] text-slate-400">
                Dispatched via Converge AI Conference Network • Sender Contact: sanjana.mahajan@sofueled.com
              </div>
            </div>

            <div className="pt-2 border-t border-canvas-border flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setActiveTab('form')}
                className="px-4 py-2 rounded-lg border border-canvas-border bg-canvas-elevated text-xs font-semibold text-ink-secondary hover:text-ink-primary transition-colors"
              >
                ← Edit Terms
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <span>{isSubmitting ? '✉️ Dispatching...' : 'Confirm & Dispatch via Email ✉️'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
