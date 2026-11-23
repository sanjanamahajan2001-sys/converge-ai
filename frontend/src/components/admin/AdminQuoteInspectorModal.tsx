import React, { useState } from 'react';
import { AdminQuoteDetailResponse } from '@/types/quote';
import { formatCurrencyValue, formatQuantity, formatUnit } from '@/lib/proposalUtils';

interface AdminQuoteInspectorModalProps {
  quote: AdminQuoteDetailResponse | null;
  isLoading: boolean;
  onClose: () => void;
}

export const AdminQuoteInspectorModal: React.FC<AdminQuoteInspectorModalProps> = ({
  quote,
  isLoading,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'audit' | 'email'>('audit');

  if (!quote && !isLoading) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
        role="dialog"
        aria-labelledby="modal-quote-reference"
      >
        <div
          className="relative w-full max-w-3xl bg-canvas-surface border border-canvas-border rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-canvas-border bg-canvas-elevated flex items-start justify-between gap-3 shrink-0">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  id="modal-quote-reference"
                  className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-brass/10 border border-brass/25 text-brass"
                >
                  {quote?.quote_reference_number || 'Loading...'}
                </span>

                {quote && (
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      quote.delivery_status === 'SENT'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                        : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                    }`}
                  >
                    {quote.delivery_status === 'SENT' ? '✓ SENT & DELIVERED' : `✕ ${quote.delivery_status}`}
                  </span>
                )}

                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-muted">
                  Audit Record
                </span>
              </div>

              <h2 className="font-serif text-base sm:text-lg font-bold text-ink-primary">
                {quote?.product_name || 'Commercial Quotation Transmission'}
              </h2>
              {quote && (
                <p className="text-xs text-ink-secondary">
                  Dispatched by <strong>{quote.vendor_name}</strong> to{' '}
                  <strong>{quote.customer_name}</strong> on{' '}
                  {new Date(quote.sent_at).toLocaleString()}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg border border-canvas-border bg-canvas-surface text-ink-muted hover:text-ink-primary text-xs transition"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>

          {/* Tab Selector */}
          <div className="flex items-center gap-2 px-4 sm:px-5 pt-3 pb-1 border-b border-canvas-border bg-canvas-base shrink-0">
            <button
              type="button"
              onClick={() => setActiveTab('audit')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'audit'
                  ? 'bg-white dark:bg-slate-900 text-ink-primary border border-canvas-border shadow-2xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              <span>📋</span>
              <span>Commercial Terms & Audit</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('email')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'email'
                  ? 'bg-white dark:bg-slate-900 text-ink-primary border border-canvas-border shadow-2xs'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              <span>✉️</span>
              <span>Delivered Email HTML</span>
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {isLoading || !quote ? (
              <div className="py-16 text-center text-xs text-ink-muted space-y-2">
                <div className="animate-spin text-2xl">⏳</div>
                <p>Loading quotation audit telemetry...</p>
              </div>
            ) : activeTab === 'audit' ? (
              <div className="space-y-5 text-xs">
                {/* Error Banner if Failed */}
                {quote.error_message && (
                  <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300 space-y-1">
                    <span className="font-bold flex items-center gap-1">
                      <span>⚠️</span> Delivery Error Logged
                    </span>
                    <p className="font-mono text-[11px]">{quote.error_message}</p>
                  </div>
                )}

                {/* Commercial Terms Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border">
                    <span className="text-[10px] uppercase font-mono text-ink-muted block">Quoted Quantity</span>
                    <span className="font-bold text-ink-primary text-sm">
                      {formatQuantity(quote.quantity)} {formatUnit(quote.quantity_unit || 'MT')}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border">
                    <span className="text-[10px] uppercase font-mono text-ink-muted block">Unit Price</span>
                    <span className="font-bold text-ink-primary text-sm">
                      {quote.currency} {Number(quote.unit_price).toLocaleString()}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border">
                    <span className="text-[10px] uppercase font-mono text-ink-muted block">Total Quoted Value</span>
                    <span className="font-mono font-bold text-ink-primary text-sm text-emerald-700 dark:text-emerald-400">
                      {formatCurrencyValue(quote.total_value, quote.currency)}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border">
                    <span className="text-[10px] uppercase font-mono text-ink-muted block">Incoterm</span>
                    <span className="font-bold text-ink-primary text-sm">{quote.incoterm}</span>
                  </div>
                </div>

                {/* Counterparty Attribution */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Vendor / Supplier */}
                  <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2">
                    <span className="block text-[10px] uppercase font-mono font-bold text-brass">
                      Vendor (Supplier / Seller)
                    </span>
                    <div>
                      <h4 className="font-bold text-ink-primary text-sm">{quote.vendor_name}</h4>
                      <p className="text-ink-secondary text-xs">{quote.vendor_company || 'Independent Supplier'}</p>
                    </div>
                    <div className="pt-2 border-t border-canvas-border space-y-1">
                      <div className="flex justify-between">
                        <span className="text-ink-muted">Sender Email:</span>
                        <span className="font-mono font-semibold text-ink-primary">{quote.sender_email}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-ink-muted">Vendor ID:</span>
                        <span className="font-mono text-[10px] text-ink-muted">{quote.vendor_id}</span>
                      </div>
                    </div>
                  </div>

                  {/* Customer / Buyer */}
                  <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2">
                    <span className="block text-[10px] uppercase font-mono font-bold text-indigo-600 dark:text-indigo-400">
                      Customer (Delegate / Buyer)
                    </span>
                    <div>
                      <h4 className="font-bold text-ink-primary text-sm">{quote.customer_name}</h4>
                      <p className="text-ink-secondary text-xs">{quote.customer_company || 'Procurement Organization'}</p>
                    </div>
                    <div className="pt-2 border-t border-canvas-border space-y-1">
                      <div className="flex justify-between">
                        <span className="text-ink-muted">Recipient Email:</span>
                        <span className="font-mono font-semibold text-ink-primary">{quote.recipient_email}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-ink-muted">Customer ID:</span>
                        <span className="font-mono text-[10px] text-ink-muted">{quote.customer_id}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Logistics & Payment Settlement */}
                <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-3">
                  <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                    Execution, Settlement & Tolerances
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <span className="text-ink-muted block text-[10px]">Lead Time</span>
                      <span className="font-semibold text-ink-primary">{quote.lead_time_days} Calendar Days</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block text-[10px]">Quote Validity</span>
                      <span className="font-semibold text-ink-primary">{quote.validity_days} Days</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block text-[10px]">Payment Terms</span>
                      <span className="font-semibold text-ink-primary">{quote.payment_terms}</span>
                    </div>
                  </div>

                  {quote.commercial_notes && (
                    <div className="pt-2.5 border-t border-canvas-border">
                      <span className="text-ink-muted block text-[10px] mb-1">Vendor Commercial Notes:</span>
                      <div className="p-2.5 rounded-lg bg-canvas-surface border border-canvas-border text-ink-secondary italic">
                        "{quote.commercial_notes}"
                      </div>
                    </div>
                  )}
                </div>

                {/* Delivery Telemetry */}
                <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2">
                  <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                    Transmission & Email Telemetry
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-ink-muted block">Subject:</span>
                      <span className="font-medium text-ink-primary">{quote.email_subject}</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block">External Message ID:</span>
                      <span className="font-mono text-ink-secondary">{quote.external_message_id || 'SMTP Relay Direct'}</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block">Dispatched Timestamp:</span>
                      <span className="font-mono text-ink-primary">{new Date(quote.sent_at).toISOString()}</span>
                    </div>
                    <div>
                      <span className="text-ink-muted block">Quote Request ID:</span>
                      <span className="font-mono text-[10px] text-ink-muted">{quote.quote_request_id}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Rendered Email HTML Tab */
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-ink-muted px-1">
                  <span>Exact HTML payload delivered to <strong>{quote.recipient_email}</strong></span>
                  <span className="font-mono text-[10px]">Verified Google SMTP Format</span>
                </div>
                <div className="border border-canvas-border rounded-xl overflow-hidden bg-white shadow-inner">
                  <iframe
                    title="Rendered Commercial Quote Email"
                    srcDoc={quote.email_body_html}
                    className="w-full h-[500px] border-0"
                    sandbox="allow-same-origin"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-3.5 sm:p-4 border-t border-canvas-border bg-canvas-elevated flex items-center justify-between shrink-0">
            <span className="text-[10px] text-ink-muted font-mono">
              Converge AI • Administrative Audit System
            </span>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg border border-canvas-border bg-canvas-surface hover:bg-canvas-sunken text-xs font-semibold text-ink-primary transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
