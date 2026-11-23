import React, { useEffect, useState } from 'react';
import { QuoteVendorPanelItem, QuoteRequestDetail, SendQuoteEmailResponse } from '@/types/quote';
import { quoteApi } from '@/lib/api/quote';
import { QuoteStatusBadge, QuoteUrgencyBadge } from './QuoteStatusBadge';
import { SendQuoteEmailModal } from './SendQuoteEmailModal';
import { formatQuantity, formatUnit, formatCurrencyValue } from '@/lib/proposalUtils';

interface AskSpecificationsDrawerProps {
  item: QuoteVendorPanelItem;
  isOpen: boolean;
  onClose: () => void;
  onStatusUpdated?: () => void;
}

export const AskSpecificationsDrawer: React.FC<AskSpecificationsDrawerProps> = ({
  item,
  isOpen,
  onClose,
  onStatusUpdated,
}) => {
  const [detail, setDetail] = useState<QuoteRequestDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isQuotingModalOpen, setIsQuotingModalOpen] = useState<boolean>(false);
  const [isDeclining, setIsDeclining] = useState<boolean>(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let mounted = true;
    setIsLoading(true);
    setError(null);

    quoteApi
      .getQuoteDetail(item.quote_request_id)
      .then((data) => {
        if (mounted) {
          setDetail(data);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to load ask specifications.');
          setIsLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, item.quote_request_id]);

  if (!isOpen) return null;

  const handleDecline = async () => {
    if (!window.confirm('Are you sure you want to decline this procurement inquiry?')) return;
    try {
      setIsDeclining(true);
      await quoteApi.declineQuote(item.match_id);
      setSuccessToast('Inquiry marked as declined.');
      if (onStatusUpdated) onStatusUpdated();
    } catch (err: any) {
      alert(err.message || 'Failed to decline inquiry.');
    } finally {
      setIsDeclining(false);
    }
  };

  const handleQuoteSent = (res: SendQuoteEmailResponse) => {
    setIsQuotingModalOpen(false);
    setSuccessToast(`Quotation ${res.quote_reference_number} dispatched to ${res.recipient_email}!`);
    if (onStatusUpdated) onStatusUpdated();
    // Refresh details to show dispatches trail
    quoteApi.getQuoteDetail(item.quote_request_id).then(setDetail);
  };

  const qty = detail?.quantity ?? item.quantity;
  const unit = formatUnit(detail?.quantity_unit ?? item.quantity_unit ?? 'MT');
  const deliveryLocation = detail?.delivery_location ?? item.delivery_location ?? 'Not Specified';
  const timelineDays = detail?.timeline_days ?? item.timeline_days;
  const urgency = detail?.urgency ?? item.urgency;
  const status = detail?.vendor_match_status ?? item.status;
  const customer = detail?.customer ?? item.customer;
  const customerAgent = detail?.customer_agent_persona ?? item.customer_agent_persona ?? 'Procurement AI Agent';

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-canvas-surface border-l border-canvas-border shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out"
        role="dialog"
        aria-labelledby="drawer-title"
        data-testid="ask-specifications-drawer"
      >
        {/* Drawer Header */}
        <div className="p-4 sm:p-5 border-b border-canvas-border bg-canvas-elevated flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <QuoteStatusBadge status={status} size="sm" />
              <QuoteUrgencyBadge urgency={urgency} />
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-muted">
                Match {typeof item.match_score === 'number' ? Math.round(item.match_score) : item.match_score}%
              </span>
            </div>
            <h2 id="drawer-title" className="font-serif text-base sm:text-lg font-bold text-ink-primary">
              {item.title}
            </h2>
            <p className="text-xs text-ink-secondary flex items-center gap-1.5">
              <span>🤖</span>
              <span>Inquiry initiated by <strong>{customerAgent}</strong></span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg border border-canvas-border bg-canvas-surface text-ink-muted hover:text-ink-primary text-xs"
            aria-label="Close drawer"
          >
            ✕
          </button>
        </div>

        {/* Drawer Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {successToast && (
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-700 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>✓</span>
                <span>{successToast}</span>
              </div>
              <button
                type="button"
                onClick={() => setSuccessToast(null)}
                className="text-emerald-700 hover:text-emerald-900 text-xs"
              >
                ✕
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="py-12 text-center text-xs text-ink-muted space-y-2">
              <div className="animate-spin text-xl">⏳</div>
              <p>Loading ask specifications...</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-xs text-rose-700">
              {error}
            </div>
          ) : (
            <>
              {/* Buyer Delegate & Organization Card */}
              <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2.5">
                <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                  Customer Delegate Information
                </span>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-sm text-ink-primary">{customer.full_name}</h3>
                    <p className="text-xs text-ink-secondary">
                      {customer.job_title ? `${customer.job_title} • ` : ''}
                      <strong>{customer.company_name || 'Industrial Procurement Delegate'}</strong>
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-muted">
                      Direct Email Quote Flow
                    </span>
                  </div>
                </div>

                {item.match_reasons && item.match_reasons.length > 0 && (
                  <div className="pt-2 border-t border-canvas-border/70 flex flex-wrap gap-1.5">
                    {item.match_reasons.map((r, i) => (
                      <span
                        key={i}
                        className="text-[10px] font-medium px-2 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-secondary"
                      >
                        ✓ {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Core Commercial Scope */}
              <div className="space-y-2">
                <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                  Procurement Scope & Logistics
                </span>
                <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-canvas-elevated border border-canvas-border text-xs">
                  <div>
                    <span className="text-[10px] text-ink-muted block">Inquired Commodity</span>
                    <span className="font-bold text-ink-primary text-sm">{item.product_name}</span>
                    {item.product_code && (
                      <span className="text-[10px] font-mono text-ink-muted block mt-0.5">
                        SKU: {item.product_code}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block">Requested Volume</span>
                    <span className="font-bold text-ink-primary text-sm">
                      {formatQuantity(qty)} {unit}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block">Destination Yard / Port</span>
                    <span className="font-semibold text-ink-primary">{deliveryLocation}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block">Target Delivery Window</span>
                    <span className="font-semibold text-ink-primary">
                      {timelineDays ? `${timelineDays} Calendar Days` : 'Standard Lead Time'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Technical Specifications & Tolerances */}
              {detail?.technical_specifications &&
                Object.keys(detail.technical_specifications).length > 0 && (
                  <div className="space-y-2">
                    <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                      Technical Standards & Quality Tolerances
                    </span>
                    <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2 text-xs">
                      {Object.entries(detail.technical_specifications).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between border-b border-canvas-border/50 pb-1.5 last:border-0 last:pb-0">
                          <span className="text-[11px] text-ink-muted capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="font-mono font-semibold text-ink-primary">
                            {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Inquiry Notes */}
              {detail?.inquiry_notes && (
                <div className="space-y-2">
                  <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                    Buyer Inquiry Notes
                  </span>
                  <div className="p-3.5 rounded-xl bg-canvas-elevated border border-canvas-border text-xs text-ink-secondary italic">
                    "{detail.inquiry_notes}"
                  </div>
                </div>
              )}

              {/* Quoting Email Dispatch History */}
              {detail?.dispatches && detail.dispatches.length > 0 && (
                <div className="space-y-2.5">
                  <span className="block text-[10px] uppercase font-mono font-bold text-ink-muted">
                    Dispatched Email Quotations ({detail.dispatches.length})
                  </span>
                  <div className="space-y-2.5">
                    {detail.dispatches.map((disp) => (
                      <div
                        key={disp.id}
                        className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between border-b border-emerald-200/60 dark:border-emerald-800/60 pb-2">
                          <span className="font-mono font-bold text-emerald-800 dark:text-emerald-300">
                            {disp.quote_reference_number}
                          </span>
                          <span className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                            ✓ {disp.delivery_status}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[10px] text-ink-muted block">Unit Consideration</span>
                            <span className="font-semibold text-ink-primary">
                              {disp.currency} {parseFloat(String(disp.unit_price)).toLocaleString()} / {unit}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-ink-muted block">Total Quoted Value</span>
                            <span className="font-mono font-bold text-ink-primary">
                              {formatCurrencyValue(disp.total_value, disp.currency)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-ink-muted block">Incoterm</span>
                            <span className="font-semibold text-ink-primary">{disp.incoterm}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-ink-muted block">Delivery Lead Time</span>
                            <span className="font-semibold text-ink-primary">{disp.lead_time_days} Days</span>
                          </div>
                        </div>
                        <div className="text-[10px] text-ink-muted pt-1 border-t border-emerald-200/40">
                          Sent on {new Date(disp.sent_at).toLocaleDateString()} at{' '}
                          {new Date(disp.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}{' '}
                          to {disp.recipient_email}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Drawer Sticky Footer Actions */}
        <div className="p-4 sm:p-5 border-t border-canvas-border bg-canvas-elevated flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-canvas-border bg-canvas-surface text-xs font-semibold text-ink-secondary hover:text-ink-primary transition-colors"
          >
            Close
          </button>

          {!item.match_id ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-ink-muted font-medium px-3 py-1.5 rounded-lg bg-canvas-surface border border-canvas-border">
                {detail?.dispatches && detail.dispatches.length > 0
                  ? `✓ ${detail.dispatches.length} quotation(s) received`
                  : '📢 Broadcast Active • Awaiting Vendor Quotations'}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {status !== 'DECLINED' && (
                <button
                  type="button"
                  onClick={handleDecline}
                  disabled={isDeclining}
                  className="px-3.5 py-2 rounded-lg border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors disabled:opacity-50"
                >
                  ✕ Decline
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsQuotingModalOpen(true)}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5"
              >
                <span>✉️</span>
                <span>{status === 'QUOTE_SENT' ? 'Send Revised Quote via Email' : 'Prepare & Send Quote via Email'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {isQuotingModalOpen && (
        <SendQuoteEmailModal
          ask={detail || item}
          onClose={() => setIsQuotingModalOpen(false)}
          onSuccess={handleQuoteSent}
        />
      )}
    </>
  );
};
