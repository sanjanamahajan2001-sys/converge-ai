import React, { useState, useEffect } from 'react';
import { conversationApi } from '@/lib/api/conversation';
import { BusinessMatchCandidate, ParsedBusinessRequirement, BusinessRequirement } from '@/types/business';
import { ConversationBusinessContextCreate } from '@/types/conversation';

interface BusinessConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: BusinessMatchCandidate | null;
  requirement?: BusinessRequirement | null;
  parsedQuery?: ParsedBusinessRequirement | null;
  onSuccess: (conversationId: string) => void;
}

export const BusinessConnectionModal: React.FC<BusinessConnectionModalProps> = ({
  isOpen,
  onClose,
  candidate,
  requirement,
  parsedQuery,
  onSuccess,
}) => {
  const [inquiryType, setInquiryType] = useState<string>('RFQ_PRODUCT');
  const [productName, setProductName] = useState<string>('');
  const [productCode, setProductCode] = useState<string>('');
  const [gradeCode, setGradeCode] = useState<string>('');
  const [serviceCode, setServiceCode] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('');
  const [unit, setUnit] = useState<string>('METRIC_TONNE');
  const [deliveryLocation, setDeliveryLocation] = useState<string>('');
  const [timelineDays, setTimelineDays] = useState<string>('');
  const [isBudgetPublic, setIsBudgetPublic] = useState<boolean>(false);
  const [targetPrice, setTargetPrice] = useState<string>('');
  const [urgency, setUrgency] = useState<string>('PLANNED');
  const [inquiryNotes, setInquiryNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Pre-fill fields whenever modal opens with candidate & requirement/query
  useEffect(() => {
    if (isOpen && candidate) {
      setErrorMsg(null);
      setIsSubmitting(false);

      // Determine initial inquiry type: Service vs Product vs Pitch vs Alternative
      const isPitch = candidate.candidate_type === 'REQUIREMENT';
      const isAlternative = candidate.confidence_badges.some((b) => b.includes('Alternative') || b.includes('Substitute'));
      const isServiceOffering = !!(
        candidate.service_code ||
        candidate.offering_title?.toLowerCase().includes('haulage') ||
        candidate.offering_title?.toLowerCase().includes('rental')
      );
      if (isPitch) {
        if (candidate.supplier_role === 'DISTRIBUTOR') {
          setInquiryType('DISTRIBUTION_EXPANSION');
        } else {
          setInquiryType(isServiceOffering ? 'VENDOR_PITCH' : 'SUPPLIER_PROSPECTING');
        }
      } else if (parsedQuery?.inquiry_type && [
        'EXPLORATORY_COLLABORATION',
        'SOURCING_PARTNERSHIP',
        'DISTRIBUTOR_APPLICATION',
        'DISTRIBUTION_EXPANSION',
        'ALTERNATIVE_SOURCING',
      ].includes(parsedQuery.inquiry_type)) {
        setInquiryType(parsedQuery.inquiry_type);
      } else if (isAlternative) {
        setInquiryType('ALTERNATIVE_SOURCING');
      } else {
        setInquiryType(isServiceOffering ? 'RFI_SERVICE' : 'RFQ_PRODUCT');
      }

      // Pre-fill Product / Item Name
      const initialItemName =
        requirement?.custom_requirement_title ||
        parsedQuery?.item_name ||
        candidate.offering_title ||
        candidate.product_code ||
        '';
      setProductName(initialItemName);

      setProductCode(requirement?.product_code || candidate.product_code || '');
      setGradeCode(requirement?.grade_code || candidate.grade_code || '');
      setServiceCode(requirement?.service_code || candidate.service_code || '');

      // Pre-fill Quantity & Unit
      const initialQty = candidate.required_quantity ?? requirement?.required_quantity ?? parsedQuery?.quantity ?? '';
      setQuantity(initialQty ? String(initialQty) : '');

      const initialUnit =
        candidate.capacity_unit || requirement?.quantity_unit || parsedQuery?.quantity_unit || 'METRIC_TONNE';
      setUnit(initialUnit);

      // Pre-fill Location
      const initialLocation =
        candidate.destination_city ||
        requirement?.delivery_city ||
        parsedQuery?.destination_city ||
        (candidate.geographic_coverage && candidate.geographic_coverage[0]) ||
        '';
      setDeliveryLocation(initialLocation);

      // Pre-fill Timeline
      const initialDays =
        candidate.target_timeline_days ?? requirement?.target_timeline_days ?? parsedQuery?.target_timeline_days ?? candidate.lead_time_days ?? 30;
      setTimelineDays(String(initialDays));

      // Target budget default: unchecked and private
      setIsBudgetPublic(false);
      const initialBudget = requirement?.target_budget_indication ?? '';
      setTargetPrice(initialBudget ? String(initialBudget) : '');

      setUrgency(requirement?.urgency || 'PLANNED');
      setInquiryNotes('');
    }
  }, [isOpen, candidate, requirement, parsedQuery]);

  if (!isOpen || !candidate) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim()) {
      setErrorMsg('Please specify the product or service title.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    const businessContextPayload: ConversationBusinessContextCreate = {
      inquiry_type: inquiryType,
      product_name: productName.trim(),
      product_code: productCode.trim() || null,
      grade_code: gradeCode.trim() || null,
      service_code: serviceCode.trim() || null,
      quantity: quantity ? parseFloat(quantity) : null,
      unit: unit.trim() || null,
      delivery_location: deliveryLocation.trim() || null,
      timeline_days: timelineDays ? parseInt(timelineDays, 10) : null,
      target_price_indication: isBudgetPublic && targetPrice ? parseFloat(targetPrice) : null,
      is_budget_public: isBudgetPublic,
      urgency: urgency || 'PLANNED',
      inquiry_notes: inquiryNotes.trim() || null,
    };

    try {
      const conv = await conversationApi.initiateConversation(
        candidate.supplier_user_id,
        businessContextPayload
      );
      onSuccess(conv.id);
    } catch (err: unknown) {
      console.error('Failed to initiate RFQ conversation:', err);
      const msg =
        err instanceof Error
          ? err.message
          : 'Could not send connection request. You may already have an active conversation or reached your limit.';
      setErrorMsg(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs overflow-y-auto animate-fade-in">
      <div className="relative w-full max-w-2xl bg-canvas-surface border border-canvas-border rounded-2xl shadow-xl overflow-hidden my-8">
        {/* Header */}
        <div className="px-6 py-4 bg-canvas-elevated border-b border-canvas-border flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">📜</span>
              <h3 className="font-serif text-lg font-bold text-ink-primary">
                Send Commercial RFQ & Connection Request
              </h3>
            </div>
            <p className="text-xs text-ink-secondary mt-0.5">
              To: <strong>{candidate.supplier_company_name || 'Industrial Partner'}</strong>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-muted hover:text-ink-primary text-xl leading-none px-2 py-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
              {errorMsg}
            </div>
          )}

          {/* Row 1: Inquiry Type & Urgency */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Inquiry Category *
              </label>
              <select
                value={inquiryType}
                onChange={(e) => setInquiryType(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              >
                <option value="RFQ_PRODUCT">RFQ: Physical Product / Material</option>
                <option value="RFI_SERVICE">RFI: Logistics / Equipment / Service</option>
                <option value="ALTERNATIVE_SOURCING">Alternative / Low-Carbon Sourcing</option>
                <option value="DISTRIBUTOR_APPLICATION">Regional Distributorship Application</option>
                <option value="DISTRIBUTION_EXPANSION">Distribution Network Sourcing</option>
                <option value="SOURCING_PARTNERSHIP">Strategic Commercial Alliance</option>
                <option value="EXPLORATORY_COLLABORATION">Exploratory Technical Discussion</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Procurement Urgency
              </label>
              <select
                value={urgency}
                onChange={(e) => setUrgency(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              >
                <option value="PLANNED">Planned Project (Standard)</option>
                <option value="IMMEDIATE">Immediate Requirement (&lt; 15 Days)</option>
                <option value="EXPLORATORY">Long-Term Contract Evaluation</option>
              </select>
            </div>
          </div>

          {/* Row 2: Product / Service Title */}
          <div>
            <label className="block text-xs font-semibold text-ink-primary mb-1">
              Required Product or Service Description *
            </label>
            <input
              type="text"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. Limestone Calcined Clay Cement (LC3) or Bulk Pneumatic Bulker Fleet"
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
            />
          </div>

          {/* Row 3: Quantity, Unit & Delivery City */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Required Volume / Qty
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="e.g. 1000"
                className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Unit
              </label>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              >
                <option value="METRIC_TONNE">Metric Tonnes (MT)</option>
                <option value="BAG_50KG">50kg Bags</option>
                <option value="TRUCKLOAD">Truckloads</option>
                <option value="HOUR">Hours (Equipment Rental)</option>
                <option value="DAY">Days (Equipment Rental)</option>
                <option value="PIECE">Pieces / Units</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-primary mb-1">
                Destination City
              </label>
              <input
                type="text"
                value={deliveryLocation}
                onChange={(e) => setDeliveryLocation(e.target.value)}
                placeholder="e.g. Pune, MH"
                className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
              />
            </div>
          </div>

          {/* Row 4: Timeline */}
          <div>
            <label className="block text-xs font-semibold text-ink-primary mb-1">
              Required Delivery / Execution Timeline (Days)
            </label>
            <input
              type="number"
              min="1"
              value={timelineDays}
              onChange={(e) => setTimelineDays(e.target.value)}
              placeholder="e.g. 45"
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
            />
          </div>

          {/* Privacy Section: Buyer Target Budget */}
          <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2">
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                id="isBudgetPublic"
                checked={isBudgetPublic}
                onChange={(e) => setIsBudgetPublic(e.target.checked)}
                className="mt-0.5 rounded border-canvas-border text-brass focus:ring-brass"
              />
              <label htmlFor="isBudgetPublic" className="text-xs font-semibold text-ink-primary cursor-pointer">
                Disclose Target Budget in RFQ Brief (Private by default)
              </label>
            </div>

            {isBudgetPublic ? (
              <div className="mt-2 pl-6 space-y-1">
                <label className="block text-[11px] font-medium text-ink-secondary">
                  Target Price Indication (₹)
                </label>
                <input
                  type="number"
                  step="any"
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                  placeholder="e.g. 5400"
                  className="w-full sm:w-64 px-3 py-1.5 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
                />
                <p className="text-[10px] text-ink-muted">
                  This target budget indication will be included in the commercial brief presented to the supplier.
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-ink-muted pl-6">
                🔒 Private Buyer Budget Preserved: Your internal target budget remains strictly hidden from the supplier.
              </p>
            )}
          </div>

          {/* Initial Brief Notes */}
          <div>
            <label className="block text-xs font-semibold text-ink-primary mb-1">
              Inquiry Notes / Specific Technical Requirements (Optional)
            </label>
            <textarea
              rows={2}
              value={inquiryNotes}
              onChange={(e) => setInquiryNotes(e.target.value)}
              placeholder="e.g. Project requires NABL test reports with every rake delivery. Site requires pneumatic bulker unloader compatibility."
              className="w-full px-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary focus:border-brass focus:outline-none"
            />
          </div>

          {/* Integrity Assurance Badge */}
          <div className="p-3 rounded-lg bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200/60 dark:border-indigo-900/40 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-2.5">
            <span className="text-base shrink-0">🛡️</span>
            <div>
              <p className="font-semibold text-[11px] leading-tight">
                Point-in-Time Immutable Commercial Brief (v1)
              </p>
              <p className="text-[10px] text-indigo-700 dark:text-indigo-300 mt-0.5 leading-relaxed">
                A cryptographic SHA-256 fingerprint will seal these commercial parameters. The recipient will preview this immutable brief before accepting the connection.
              </p>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-3 border-t border-canvas-border flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold rounded-lg border border-canvas-border text-ink-secondary hover:text-ink-primary hover:bg-canvas-elevated transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass/90 transition shadow-xs flex items-center gap-1.5"
            >
              <span>🚀</span>
              <span>{isSubmitting ? 'Sealing Brief & Sending...' : 'Send RFQ Connection Request'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
