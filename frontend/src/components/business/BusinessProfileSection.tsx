import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMyBusinessProfile,
  updateMyBusinessProfile,
  createOffering,
  updateOffering,
  deleteOffering,
  confirmOffering,
  createRequirement,
  updateRequirement,
  deleteRequirement,
  getProductTaxonomies,
  getServiceTaxonomies,
} from '@/lib/api/business';
import {
  BusinessProfileUpdate,
  BusinessOffering,
  BusinessOfferingInput,
  BusinessRequirement,
  BusinessRequirementInput,
} from '@/types/business';
import { Card } from '@/components/ui/Card';
import { LoadingState } from '@/components/ui/LoadingState';

export const UNIVERSAL_UNITS = [
  // Mass
  { value: 'METRIC_TONNE', label: 'Metric Tonnes (MT)' },
  { value: 'KILOGRAM', label: 'Kilograms (kg)' },
  { value: 'QUINTAL', label: 'Quintals (100 kg)' },
  { value: 'BAG_50KG', label: '50kg Bags' },
  { value: 'POUND', label: 'Pounds (lbs)' },
  // Volume
  { value: 'CUBIC_METER', label: 'Cubic Meters (m³)' },
  { value: 'LITER', label: 'Liters (L)' },
  { value: 'KILOLITER', label: 'Kiloliters (kL)' },
  { value: 'GALLON_US', label: 'US Gallons (gal)' },
  { value: 'GALLON_IMP', label: 'Imperial Gallons (gal)' },
  { value: 'BARREL', label: 'Barrels (bbl)' },
  // Discrete Counts
  { value: 'UNIT', label: 'Units / Pieces (pcs)' },
  { value: 'SET', label: 'Sets' },
  { value: 'BOX', label: 'Boxes' },
  { value: 'PALLET', label: 'Pallets' },
  { value: 'CONTAINER', label: 'Containers (TEU)' },
  { value: 'TRUCKLOAD', label: 'Truckloads' },
  { value: 'DOZEN', label: 'Dozens (12 pcs)' },
  { value: 'THOUSAND', label: 'Thousand Units' },
  // Service & Professional Time
  { value: 'HOUR', label: 'Hours' },
  { value: 'MAN_DAY', label: 'Man-Days (8 hrs)' },
  { value: 'MAN_MONTH', label: 'Man-Months (160 hrs)' },
  { value: 'DAY_24H', label: 'Days (24 hrs)' },
];

export const INDUSTRY_SECTORS = [
  'Construction Materials & Cement',
  'Metals, Steel & Mining',
  'Heavy Machinery & Industrial Equipment',
  'Renewable Energy & Solar',
  'Logistics, Fleet & Warehousing',
  'Chemicals, Minerals & Polymers',
  'Testing, Inspection & Certification',
  'Electrical, Electronics & Automation',
  'IT, Software & Engineering Consulting',
  'General Industrial / Other',
];

export const BusinessProfileSection: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: businessProfile, isLoading: isProfileLoading } = useQuery({
    queryKey: ['myBusinessProfile'],
    queryFn: getMyBusinessProfile,
    retry: false,
  });

  const { data: productTaxonomies = [] } = useQuery({
    queryKey: ['productTaxonomies'],
    queryFn: getProductTaxonomies,
    staleTime: 10 * 60 * 1000,
  });

  const { data: serviceTaxonomies = [] } = useQuery({
    queryKey: ['serviceTaxonomies'],
    queryFn: getServiceTaxonomies,
    staleTime: 10 * 60 * 1000,
  });

  // State
  const [isBuyer, setIsBuyer] = useState(false);
  const [isSupplier, setIsSupplier] = useState(false);
  const [isVendor, setIsVendor] = useState(false);
  const [isDistributor, setIsDistributor] = useState(false);
  const [isPartner, setIsPartner] = useState(false);
  const [allowBusinessMatching, setAllowBusinessMatching] = useState(false);

  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [businessWebsite, setBusinessWebsite] = useState('');
  const [hqCity, setHqCity] = useState('');
  const [hqCountry, setHqCountry] = useState('');
  const [companyBio, setCompanyBio] = useState('');

  const [distributorTerritories, setDistributorTerritories] = useState<string[]>([]);
  const [territoryInput, setTerritoryInput] = useState('');
  const [warehousingSqft, setWarehousingSqft] = useState<number | ''>('');
  const [dealerCount, setDealerCount] = useState<number | ''>('');

  const [partnershipTypes, setPartnershipTypes] = useState<string[]>([]);

  // Modals & Edit Selection
  const [showOfferingModal, setShowOfferingModal] = useState(false);
  const [showRequirementModal, setShowRequirementModal] = useState(false);
  const [editingOffering, setEditingOffering] = useState<BusinessOffering | null>(null);
  const [editingRequirement, setEditingRequirement] = useState<BusinessRequirement | null>(null);

  // New offering form
  const [offeringTitle, setOfferingTitle] = useState('');
  const [offeringEntryMode, setOfferingEntryMode] = useState<'KNOWN' | 'CUSTOM'>('KNOWN');
  const [offeringItemType, setOfferingItemType] = useState<'PRODUCT' | 'SERVICE'>('PRODUCT');
  const [offeringProductCode, setOfferingProductCode] = useState('');
  const [offeringGradeCode, setOfferingGradeCode] = useState('');
  const [offeringServiceCode, setOfferingServiceCode] = useState('');
  const [offeringSector, setOfferingSector] = useState('');
  const [offeringSpecs, setOfferingSpecs] = useState('');
  const [offeringCapacity, setOfferingCapacity] = useState<number | ''>('');
  const [offeringCommittedVolume, setOfferingCommittedVolume] = useState<number | ''>('');
  const [offeringUnit, setOfferingUnit] = useState('METRIC_TONNE');
  const [offeringMoq, setOfferingMoq] = useState<number | ''>('');
  const [offeringLeadTime, setOfferingLeadTime] = useState<number | ''>('');
  const [offeringCoverage, setOfferingCoverage] = useState('');
  const [offeringCertificates, setOfferingCertificates] = useState(false);
  const [offeringCertifications, setOfferingCertifications] = useState('');
  const [offeringPublicIndicative, setOfferingPublicIndicative] = useState(false);
  const [offeringPriceMin, setOfferingPriceMin] = useState<number | ''>('');
  const [offeringPriceMax, setOfferingPriceMax] = useState<number | ''>('');
  const [offeringPricingBasis, setOfferingPricingBasis] = useState('EX_WORKS');

  // New requirement form
  const [reqTitle, setReqTitle] = useState('');
  const [reqEntryMode, setReqEntryMode] = useState<'KNOWN' | 'CUSTOM'>('KNOWN');
  const [reqItemType, setReqItemType] = useState<'PRODUCT' | 'SERVICE'>('PRODUCT');
  const [reqProductCode, setReqProductCode] = useState('');
  const [reqGradeCode, setReqGradeCode] = useState('');
  const [reqServiceCode, setReqServiceCode] = useState('');
  const [reqSector, setReqSector] = useState('');
  const [reqNotes, setReqNotes] = useState('');
  const [reqQuantity, setReqQuantity] = useState<number | ''>('');
  const [reqUnit, setReqUnit] = useState('METRIC_TONNE');
  const [reqCity, setReqCity] = useState('');
  const [reqTimeline, setReqTimeline] = useState<number | ''>('');
  const [reqBudget, setReqBudget] = useState<number | ''>('');
  const [reqBudgetPublic, setReqBudgetPublic] = useState(false);
  const [reqUrgency, setReqUrgency] = useState<'IMMEDIATE' | 'PLANNED' | 'EXPLORATORY'>('PLANNED');

  const [saveSuccessMsg, setSaveSuccessMsg] = useState('');
  const [saveErrorMsg, setSaveErrorMsg] = useState('');

  // Sync profile data
  useEffect(() => {
    if (businessProfile) {
      setIsBuyer(businessProfile.is_buyer);
      setIsSupplier(businessProfile.is_supplier);
      setIsVendor(businessProfile.is_vendor);
      setIsDistributor(businessProfile.is_distributor);
      setIsPartner(businessProfile.is_partner);
      setAllowBusinessMatching(businessProfile.allow_business_matching);

      setCompanyName(businessProfile.company_name || '');
      setIndustry(businessProfile.industry || '');
      setBusinessWebsite(businessProfile.business_website || '');
      setHqCity(businessProfile.hq_city || '');
      setHqCountry(businessProfile.hq_country || '');
      setCompanyBio(businessProfile.company_bio || '');

      setDistributorTerritories(businessProfile.distributor_territories || []);
      setWarehousingSqft(businessProfile.warehousing_capacity_sqft ? Number(businessProfile.warehousing_capacity_sqft) : '');
      setDealerCount(businessProfile.retail_dealer_count ? Number(businessProfile.retail_dealer_count) : '');
      setPartnershipTypes(businessProfile.partnership_types || []);
    }
  }, [businessProfile]);

  // Mutations
  const updateProfileMutation = useMutation({
    mutationFn: (payload: BusinessProfileUpdate) => updateMyBusinessProfile(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['myBusinessProfile'], data);
      setSaveSuccessMsg('Business profile and role configuration updated successfully.');
      setSaveErrorMsg('');
      setTimeout(() => setSaveSuccessMsg(''), 4000);
    },
    onError: (err: any) => {
      setSaveErrorMsg(err?.detail || err?.message || 'Failed to update business profile.');
      setSaveSuccessMsg('');
    },
  });

  const createOfferingMutation = useMutation({
    mutationFn: (input: BusinessOfferingInput) => createOffering(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
      setShowOfferingModal(false);
      resetOfferingForm();
    },
    onError: (err: any) => {
      setSaveErrorMsg(err?.detail || err?.message || 'Failed to add offering.');
    },
  });

  const updateOfferingMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<BusinessOfferingInput> }) =>
      updateOffering(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
      setShowOfferingModal(false);
      setEditingOffering(null);
      resetOfferingForm();
      setSaveSuccessMsg('Offering updated successfully.');
      setTimeout(() => setSaveSuccessMsg(''), 3000);
    },
    onError: (err: any) => {
      setSaveErrorMsg(err?.detail || err?.message || 'Failed to update offering.');
    },
  });

  const deleteOfferingMutation = useMutation({
    mutationFn: (id: string) => deleteOffering(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
    },
  });

  const confirmOfferingMutation = useMutation({
    mutationFn: (id: string) => confirmOffering(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
      setSaveSuccessMsg('Offering capacity and pricing confirmed fresh.');
      setTimeout(() => setSaveSuccessMsg(''), 3000);
    },
  });

  const createRequirementMutation = useMutation({
    mutationFn: (input: BusinessRequirementInput) => createRequirement(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
      setShowRequirementModal(false);
      resetRequirementForm();
    },
    onError: (err: any) => {
      setSaveErrorMsg(err?.detail || err?.message || 'Failed to add requirement.');
    },
  });

  const updateRequirementMutation = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<BusinessRequirementInput> }) =>
      updateRequirement(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
      setShowRequirementModal(false);
      setEditingRequirement(null);
      resetRequirementForm();
      setSaveSuccessMsg('Requirement updated successfully.');
      setTimeout(() => setSaveSuccessMsg(''), 3000);
    },
    onError: (err: any) => {
      setSaveErrorMsg(err?.detail || err?.message || 'Failed to update requirement.');
    },
  });

  const deleteRequirementMutation = useMutation({
    mutationFn: (id: string) => deleteRequirement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBusinessProfile'] });
    },
  });

  const resetOfferingForm = () => {
    setEditingOffering(null);
    setOfferingTitle('');
    setOfferingEntryMode('KNOWN');
    setOfferingItemType('PRODUCT');
    setOfferingProductCode('');
    setOfferingGradeCode('');
    setOfferingServiceCode('');
    setOfferingSector('');
    setOfferingSpecs('');
    setOfferingCapacity('');
    setOfferingCommittedVolume('');
    setOfferingUnit('METRIC_TONNE');
    setOfferingMoq('');
    setOfferingLeadTime('');
    setOfferingCoverage('');
    setOfferingCertificates(false);
    setOfferingCertifications('');
    setOfferingPublicIndicative(false);
    setOfferingPriceMin('');
    setOfferingPriceMax('');
    setOfferingPricingBasis('EX_WORKS');
  };

  const resetRequirementForm = () => {
    setEditingRequirement(null);
    setReqTitle('');
    setReqEntryMode('KNOWN');
    setReqItemType('PRODUCT');
    setReqProductCode('');
    setReqGradeCode('');
    setReqServiceCode('');
    setReqSector('');
    setReqNotes('');
    setReqQuantity('');
    setReqUnit('METRIC_TONNE');
    setReqCity('');
    setReqTimeline('');
    setReqBudget('');
    setReqBudgetPublic(false);
    setReqUrgency('PLANNED');
  };

  const handleStartEditOffering = (off: BusinessOffering) => {
    setEditingOffering(off);
    setOfferingTitle(off.custom_product_title || '');
    if (off.service_code) {
      setOfferingEntryMode('KNOWN');
      setOfferingItemType('SERVICE');
      setOfferingServiceCode(off.service_code);
      setOfferingProductCode('');
      setOfferingGradeCode('');
    } else if (off.product_code) {
      setOfferingEntryMode('KNOWN');
      setOfferingItemType('PRODUCT');
      setOfferingProductCode(off.product_code);
      setOfferingGradeCode(off.grade_code || '');
      setOfferingServiceCode('');
    } else {
      setOfferingEntryMode('CUSTOM');
      setOfferingProductCode('');
      setOfferingGradeCode('');
      setOfferingServiceCode('');
    }
    setOfferingSpecs(off.specifications_text || '');
    setOfferingCapacity(off.declared_monthly_capacity ? Number(off.declared_monthly_capacity) : '');
    setOfferingCommittedVolume(off.declared_committed_volume ? Number(off.declared_committed_volume) : '');
    setOfferingUnit(off.capacity_unit || 'METRIC_TONNE');
    setOfferingMoq(off.minimum_order_quantity ? Number(off.minimum_order_quantity) : '');
    setOfferingLeadTime(off.lead_time_days ?? '');
    setOfferingCoverage((off.geographic_coverage || []).join(', '));
    setOfferingCertificates(off.offers_test_certificates ?? false);
    setOfferingCertifications((off.vendor_certifications || []).join(', '));
    setOfferingPublicIndicative(off.is_public_indicative ?? false);
    setOfferingPriceMin(off.indicative_price_min ? Number(off.indicative_price_min) : '');
    setOfferingPriceMax(off.indicative_price_max ? Number(off.indicative_price_max) : '');
    setOfferingPricingBasis(off.pricing_basis || 'EX_WORKS');
    setShowOfferingModal(true);
  };

  const handleStartEditRequirement = (req: BusinessRequirement) => {
    setEditingRequirement(req);
    setReqTitle(req.custom_requirement_title || '');
    if (req.service_code) {
      setReqEntryMode('KNOWN');
      setReqItemType('SERVICE');
      setReqServiceCode(req.service_code);
      setReqProductCode('');
      setReqGradeCode('');
    } else if (req.product_code) {
      setReqEntryMode('KNOWN');
      setReqItemType('PRODUCT');
      setReqProductCode(req.product_code);
      setReqGradeCode(req.grade_code || '');
      setReqServiceCode('');
    } else {
      setReqEntryMode('CUSTOM');
      setReqProductCode('');
      setReqGradeCode('');
      setReqServiceCode('');
    }
    setReqQuantity(req.required_quantity ? Number(req.required_quantity) : '');
    setReqUnit(req.quantity_unit || 'METRIC_TONNE');
    setReqCity(req.delivery_city || '');
    setReqTimeline(req.target_timeline_days ?? '');
    setReqBudget(req.target_budget_indication ? Number(req.target_budget_indication) : '');
    setReqBudgetPublic(req.is_budget_public ?? false);
    setReqUrgency(req.urgency || 'PLANNED');
    setReqNotes(req.notes || '');
    setShowRequirementModal(true);
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (allowBusinessMatching && !(isBuyer || isSupplier || isVendor || isDistributor || isPartner)) {
      setSaveErrorMsg('Please select at least one commercial role to enable business matching.');
      return;
    }

    updateProfileMutation.mutate({
      is_buyer: isBuyer,
      is_supplier: isSupplier,
      is_vendor: isVendor,
      is_distributor: isDistributor,
      is_partner: isPartner,
      allow_business_matching: allowBusinessMatching,
      company_name: companyName.trim() || null,
      industry: industry.trim() || null,
      business_website: businessWebsite.trim() || null,
      hq_city: hqCity.trim() || null,
      hq_country: hqCountry.trim() || null,
      company_bio: companyBio.trim() || null,
      distributor_territories: distributorTerritories,
      warehousing_capacity_sqft: warehousingSqft ? Number(warehousingSqft) : null,
      retail_dealer_count: dealerCount ? Number(dealerCount) : null,
      partnership_types: partnershipTypes,
      partnership_interests: [],
    });
  };

  const handleAddTerritory = () => {
    if (territoryInput.trim() && !distributorTerritories.includes(territoryInput.trim())) {
      setDistributorTerritories([...distributorTerritories, territoryInput.trim()]);
      setTerritoryInput('');
    }
  };

  const handleRemoveTerritory = (t: string) => {
    setDistributorTerritories(distributorTerritories.filter((x) => x !== t));
  };

  const handleTogglePartnershipType = (type: string) => {
    if (partnershipTypes.includes(type)) {
      setPartnershipTypes(partnershipTypes.filter((x) => x !== type));
    } else {
      setPartnershipTypes([...partnershipTypes, type]);
    }
  };

  const handleAddOfferingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!offeringTitle.trim()) return;

    const payload: BusinessOfferingInput = {
      custom_product_title: offeringTitle.trim(),
      product_code: offeringEntryMode === 'KNOWN' && offeringItemType === 'PRODUCT' ? (offeringProductCode || null) : null,
      grade_code: offeringEntryMode === 'KNOWN' && offeringItemType === 'PRODUCT' ? (offeringGradeCode || null) : null,
      service_code: offeringEntryMode === 'KNOWN' && offeringItemType === 'SERVICE' ? (offeringServiceCode || null) : null,
      specifications_text: offeringSpecs.trim() || (offeringSector ? `Sector: ${offeringSector}` : null),
      declared_monthly_capacity: offeringCapacity !== '' ? Number(offeringCapacity) : null,
      declared_committed_volume: offeringCommittedVolume !== '' ? Number(offeringCommittedVolume) : null,
      capacity_unit: offeringUnit,
      minimum_order_quantity: offeringMoq ? Number(offeringMoq) : null,
      lead_time_days: offeringLeadTime ? Number(offeringLeadTime) : null,
      geographic_coverage: offeringCoverage ? offeringCoverage.split(',').map((s) => s.trim()).filter(Boolean) : [],
      offers_test_certificates: offeringCertificates,
      vendor_certifications: offeringCertifications ? offeringCertifications.split(',').map((s) => s.trim()).filter(Boolean) : [],
      is_public_indicative: offeringPublicIndicative,
      indicative_price_min: offeringPriceMin ? Number(offeringPriceMin) : null,
      indicative_price_max: offeringPriceMax ? Number(offeringPriceMax) : null,
      pricing_basis: offeringPricingBasis,
      price_currency: 'INR',
      quote_validity_days: 30,
    };

    if (editingOffering) {
      updateOfferingMutation.mutate({ id: editingOffering.id, input: payload });
    } else {
      createOfferingMutation.mutate(payload);
    }
  };

  const handleAddRequirementSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reqTitle.trim()) return;

    const payload: BusinessRequirementInput = {
      custom_requirement_title: reqTitle.trim(),
      product_code: reqEntryMode === 'KNOWN' && reqItemType === 'PRODUCT' ? (reqProductCode || null) : null,
      grade_code: reqEntryMode === 'KNOWN' && reqItemType === 'PRODUCT' ? (reqGradeCode || null) : null,
      service_code: reqEntryMode === 'KNOWN' && reqItemType === 'SERVICE' ? (reqServiceCode || null) : null,
      required_quantity: reqQuantity ? Number(reqQuantity) : null,
      quantity_unit: reqUnit,
      delivery_city: reqCity.trim() || null,
      target_timeline_days: reqTimeline ? Number(reqTimeline) : null,
      target_budget_indication: reqBudget ? Number(reqBudget) : null,
      is_budget_public: reqBudgetPublic,
      urgency: reqUrgency,
      notes: reqNotes.trim() || (reqSector ? `Sector: ${reqSector}` : null),
    };

    if (editingRequirement) {
      updateRequirementMutation.mutate({ id: editingRequirement.id, input: payload });
    } else {
      createRequirementMutation.mutate(payload);
    }
  };

  if (isProfileLoading) {
    return <LoadingState message="Loading commercial profile..." />;
  }

  // Selected product canonical info for grades dropdown
  const selectedProduct = productTaxonomies
    .flatMap((t) => t.canonical_products)
    .find((p) => p.product_code === offeringProductCode);

  const selectedReqProduct = productTaxonomies
    .flatMap((t) => t.canonical_products)
    .find((p) => p.product_code === reqProductCode);

  return (
    <div className="space-y-8 mt-6">
      <Card
        title="Commercial & Business Profile (Mode B Discovery)"
        subtitle="Manage dynamic commercial roles, procurement requirements, and supplier catalogs."
      >
        <form onSubmit={handleSaveProfile} className="space-y-6">
          {saveSuccessMsg && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs sm:text-sm text-emerald-700 dark:text-emerald-300">
              ✓ {saveSuccessMsg}
            </div>
          )}
          {saveErrorMsg && (
            <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-xs sm:text-sm text-rose-700 dark:text-rose-300">
              ⚠️ {saveErrorMsg}
            </div>
          )}

          {/* Global Opt-In Toggle */}
          <div className="p-4 bg-canvas-subtle dark:bg-slate-900 border border-canvas-border rounded-xl flex items-center justify-between">
            <div className="space-y-0.5 pr-4">
              <label className="text-sm font-semibold text-ink-primary flex items-center gap-2">
                <span>Enable Commercial & Business Discovery</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  Mode B
                </span>
              </label>
              <p className="text-xs text-ink-muted">
                Allows delegates to discover your business requirements and offerings in commercial RFQ searches.
                Separate from general attendee networking.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={allowBusinessMatching}
                onChange={(e) => setAllowBusinessMatching(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>

          {/* Dynamic Commercial Roles Multi-Select */}
          <div className="space-y-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-ink-secondary">
              Active Commercial Roles (Select All That Apply)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Buyer */}
              <div
                onClick={() => setIsBuyer(!isBuyer)}
                className={`p-3.5 border rounded-xl cursor-pointer transition-all flex items-start gap-3 ${
                  isBuyer
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/30'
                    : 'border-canvas-border hover:border-slate-400 bg-canvas-card'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isBuyer}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-ink-primary flex items-center gap-1.5">
                    <span>🛒</span> Buyer / Sourcing
                  </div>
                  <p className="text-[11px] text-ink-muted mt-0.5">
                    Procuring products, raw materials, or specialized services.
                  </p>
                </div>
              </div>

              {/* Supplier */}
              <div
                onClick={() => setIsSupplier(!isSupplier)}
                className={`p-3.5 border rounded-xl cursor-pointer transition-all flex items-start gap-3 ${
                  isSupplier
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/30'
                    : 'border-canvas-border hover:border-slate-400 bg-canvas-card'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSupplier}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-ink-primary flex items-center gap-1.5">
                    <span>🏭</span> Supplier / Manufacturer
                  </div>
                  <p className="text-[11px] text-ink-muted mt-0.5">
                    Producing & supplying physical goods or raw materials.
                  </p>
                </div>
              </div>

              {/* Vendor */}
              <div
                onClick={() => setIsVendor(!isVendor)}
                className={`p-3.5 border rounded-xl cursor-pointer transition-all flex items-start gap-3 ${
                  isVendor
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/30'
                    : 'border-canvas-border hover:border-slate-400 bg-canvas-card'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isVendor}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-ink-primary flex items-center gap-1.5">
                    <span>🛠️</span> Vendor / Service Provider
                  </div>
                  <p className="text-[11px] text-ink-muted mt-0.5">
                    Logistics fleet, testing laboratories, equipment rental, maintenance.
                  </p>
                </div>
              </div>

              {/* Distributor */}
              <div
                onClick={() => setIsDistributor(!isDistributor)}
                className={`p-3.5 border rounded-xl cursor-pointer transition-all flex items-start gap-3 ${
                  isDistributor
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/30'
                    : 'border-canvas-border hover:border-slate-400 bg-canvas-card'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isDistributor}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-ink-primary flex items-center gap-1.5">
                    <span>📦</span> Distributor / Channel Partner
                  </div>
                  <p className="text-[11px] text-ink-muted mt-0.5">
                    Regional dealership, warehousing network, wholesale retail reach.
                  </p>
                </div>
              </div>

              {/* Partner */}
              <div
                onClick={() => setIsPartner(!isPartner)}
                className={`p-3.5 border rounded-xl cursor-pointer transition-all flex items-start gap-3 ${
                  isPartner
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/30'
                    : 'border-canvas-border hover:border-slate-400 bg-canvas-card'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isPartner}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs sm:text-sm font-semibold text-ink-primary flex items-center gap-1.5">
                    <span>🤝</span> Commercial Partner
                  </div>
                  <p className="text-[11px] text-ink-muted mt-0.5">
                    Joint ventures, co-manufacturing, strategic supply alliances.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Company Details Grid */}
          <div className="space-y-3 pt-2 border-t border-canvas-border">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
              Company & Corporate Details
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-ink-secondary mb-1">Company / Organization Name</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. UltraTech Infrastructure Ltd"
                  className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle dark:bg-slate-900 px-3 py-2 text-ink-primary focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-secondary mb-1">Industry Sector</label>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. Heavy Construction & Materials"
                  className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle dark:bg-slate-900 px-3 py-2 text-ink-primary focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-secondary mb-1">HQ City</label>
                <input
                  type="text"
                  value={hqCity}
                  onChange={(e) => setHqCity(e.target.value)}
                  placeholder="e.g. Pune"
                  className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle dark:bg-slate-900 px-3 py-2 text-ink-primary focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-secondary mb-1">Website URL</label>
                <input
                  type="url"
                  value={businessWebsite}
                  onChange={(e) => setBusinessWebsite(e.target.value)}
                  placeholder="https://company.example.com"
                  className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle dark:bg-slate-900 px-3 py-2 text-ink-primary focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-ink-secondary mb-1">Company Bio / Capabilities Overview</label>
              <textarea
                rows={2}
                value={companyBio}
                onChange={(e) => setCompanyBio(e.target.value)}
                placeholder="Brief summary of your manufacturing capabilities, fleet, or procurement objectives..."
                className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle dark:bg-slate-900 px-3 py-2 text-ink-primary focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Conditional Distributor Details */}
          {isDistributor && (
            <div className="p-4 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                <span>📦</span> Distribution Network Specifications
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-ink-secondary mb-1">Warehousing Capacity (sq. ft.)</label>
                  <input
                    type="number"
                    value={warehousingSqft}
                    onChange={(e) => setWarehousingSqft(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 25000"
                    className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-1.5 text-ink-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink-secondary mb-1">Retail Dealer Count</label>
                  <input
                    type="number"
                    value={dealerCount}
                    onChange={(e) => setDealerCount(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 150"
                    className="w-full text-xs sm:text-sm rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-1.5 text-ink-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink-secondary mb-1">Territories Served</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={territoryInput}
                    onChange={(e) => setTerritoryInput(e.target.value)}
                    placeholder="e.g. Western Maharashtra"
                    className="flex-1 text-xs rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-1.5 text-ink-primary"
                  />
                  <button
                    type="button"
                    onClick={handleAddTerritory}
                    className="px-3 py-1 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700"
                  >
                    Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {distributorTerritories.map((t) => (
                    <span
                      key={t}
                      className="px-2 py-0.5 rounded-full text-[11px] bg-amber-100 dark:bg-amber-900 text-amber-800 dark:text-amber-200 flex items-center gap-1"
                    >
                      {t}
                      <button type="button" onClick={() => handleRemoveTerritory(t)} className="text-xs hover:font-bold">
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Conditional Partnership Details */}
          {isPartner && (
            <div className="p-4 bg-sky-50/50 dark:bg-sky-950/20 border border-sky-200 dark:border-sky-800 rounded-xl space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-sky-800 dark:text-sky-300 flex items-center gap-1.5">
                <span>🤝</span> Partnership Interests
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {['CO_MANUFACTURING', 'RAW_FEEDSTOCK', 'JOINT_VENTURE', 'R_AND_D'].map((type) => (
                  <label key={type} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={partnershipTypes.includes(type)}
                      onChange={() => handleTogglePartnershipType(type)}
                      className="rounded text-sky-600"
                    />
                    <span className="text-ink-secondary">{type.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={updateProfileMutation.isPending}
              className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-xs sm:text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {updateProfileMutation.isPending ? 'Saving...' : 'Save Business Profile & Roles'}
            </button>
          </div>
        </form>
      </Card>

      {/* Supplier & Vendor Catalog Section */}
      {(isSupplier || isVendor) && (
        <Card
          title="Product & Service Offerings (Supplier / Vendor Catalog)"
          subtitle="Declared capacity, dispatch lead times, and indicative commercial parameters."
        >
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs text-ink-muted">
                {businessProfile?.offerings?.length || 0} catalog item(s) declared
              </span>
              <button
                type="button"
                onClick={() => setShowOfferingModal(true)}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-1"
              >
                <span>+</span> Add Offering
              </button>
            </div>

            {(!businessProfile?.offerings || businessProfile.offerings.length === 0) ? (
              <div className="text-center py-8 text-xs text-ink-muted border border-dashed border-canvas-border rounded-xl">
                No catalog offerings published yet. Click &quot;Add Offering&quot; to list materials, capacity, or services.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {businessProfile.offerings.map((off) => (
                  <div
                    key={off.id}
                    className="p-4 border border-canvas-border rounded-xl bg-canvas-card dark:bg-slate-900/60 space-y-3 relative"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-semibold text-sm text-ink-primary">{off.custom_product_title}</h4>
                        <p className="text-xs text-ink-muted font-mono">{off.grade_code || off.product_code || off.service_code || 'General Item'}</p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleStartEditOffering(off)}
                          className="text-xs px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 font-semibold transition-colors flex items-center gap-1"
                          title="Edit offering"
                        >
                          <span>✏️</span> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteOfferingMutation.mutate(off.id)}
                          className="text-xs text-rose-500 hover:text-rose-700 p-1"
                          title="Delete offering"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-ink-muted block text-[10px] uppercase">Declared Monthly Capacity</span>
                        <span className="font-semibold text-ink-primary">
                          {off.declared_monthly_capacity ? `${Number(off.declared_monthly_capacity).toLocaleString()} ${off.capacity_unit}` : 'Not Specified'}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[10px] uppercase">Lead Time</span>
                        <span className="font-semibold text-ink-primary">
                          {off.lead_time_days ? `${off.lead_time_days} days` : 'Immediate / Spot'}
                        </span>
                      </div>
                    </div>

                    {/* Freshness Status & 1-Click Reconfirm Button */}
                    <div className="pt-2 border-t border-canvas-border flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        {off.reconfirmation_required ? (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                            ⚠️ Reconfirmation Needed
                          </span>
                        ) : off.is_capacity_stale ? (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200">
                            ⚠️ Stale Data (&gt;90d)
                          </span>
                        ) : (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                            ✓ Verified Fresh
                          </span>
                        )}
                        {off.offers_test_certificates && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200">
                            📜 Mill Certs
                          </span>
                        )}
                        {off.vendor_certifications && off.vendor_certifications.map((cert) => (
                          <span key={cert} className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200">
                            🎖️ {cert}
                          </span>
                        ))}
                      </div>

                      <button
                        type="button"
                        onClick={() => confirmOfferingMutation.mutate(off.id)}
                        disabled={confirmOfferingMutation.isPending}
                        className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                      >
                        Re-confirm Freshness
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Buyer Active Requirements Section */}
      {isBuyer && (
        <Card
          title="Active Procurement Requirements (Buyer Needs)"
          subtitle="Specific material volumes, destination cities, and target delivery windows."
        >
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-xs text-ink-muted">
                {businessProfile?.requirements?.length || 0} active requirement(s)
              </span>
              <button
                type="button"
                onClick={() => setShowRequirementModal(true)}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-1"
              >
                <span>+</span> Add Requirement
              </button>
            </div>

            {(!businessProfile?.requirements || businessProfile.requirements.length === 0) ? (
              <div className="text-center py-8 text-xs text-ink-muted border border-dashed border-canvas-border rounded-xl">
                No procurement requirements listed yet. Click &quot;Add Requirement&quot; to specify your material needs.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {businessProfile.requirements.map((req) => (
                  <div
                    key={req.id}
                    className="p-4 border border-canvas-border rounded-xl bg-canvas-card dark:bg-slate-900/60 space-y-3 relative"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-semibold text-sm text-ink-primary">
                          {req.custom_requirement_title || req.grade_code || req.product_code || req.service_code || 'Procurement Requirement'}
                        </h4>
                        <p className="text-xs text-ink-muted">
                          <span className="font-mono bg-canvas-subtle px-1.5 py-0.5 rounded text-[11px] text-ink-muted mr-1.5">
                            {req.grade_code || req.product_code || req.service_code || 'Custom Item'}
                          </span>
                          Destination: <strong className="text-ink-secondary">{req.delivery_city || 'Flexible'}</strong>
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleStartEditRequirement(req)}
                          className="text-xs px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 font-semibold transition-colors flex items-center gap-1"
                          title="Edit requirement"
                        >
                          <span>✏️</span> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteRequirementMutation.mutate(req.id)}
                          className="text-xs text-rose-500 hover:text-rose-700 p-1"
                          title="Delete requirement"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-ink-muted block text-[10px] uppercase">Quantity</span>
                        <span className="font-semibold text-ink-primary">
                          {req.required_quantity ? `${Number(req.required_quantity).toLocaleString()} ${req.quantity_unit}` : 'Unspecified'}
                        </span>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[10px] uppercase">Timeline</span>
                        <span className="font-semibold text-ink-primary">
                          {req.target_timeline_days ? `Within ${req.target_timeline_days} days` : 'Open'}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-canvas-border flex items-center justify-between text-xs">
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                        Urgency: {req.urgency}
                      </span>
                      <span className="text-[11px] text-ink-muted flex items-center gap-1">
                        {req.is_budget_public ? '🌐 Budget Public' : '🔒 Budget Private'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Add Offering Modal */}
      {showOfferingModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-canvas-card border border-canvas-border rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center pb-2 border-b border-canvas-border">
              <h3 className="font-bold text-base text-ink-primary">
                {editingOffering ? 'Edit Catalog Offering' : 'Add Catalog Offering'}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowOfferingModal(false);
                  resetOfferingForm();
                }}
                className="text-ink-muted hover:text-ink-primary text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddOfferingSubmit} className="space-y-4 text-xs">
              {/* Entry Mode Selector */}
              <div className="flex rounded-lg bg-canvas-subtle p-1 border border-canvas-border">
                <button
                  type="button"
                  onClick={() => {
                    setOfferingEntryMode('KNOWN');
                    setOfferingProductCode('');
                    setOfferingGradeCode('');
                    setOfferingServiceCode('');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all ${
                    offeringEntryMode === 'KNOWN'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  📦 Standard Catalog
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOfferingEntryMode('CUSTOM');
                    setOfferingProductCode('');
                    setOfferingGradeCode('');
                    setOfferingServiceCode('');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all ${
                    offeringEntryMode === 'CUSTOM'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  ✨ Custom Product / Service
                </button>
              </div>

              {offeringEntryMode === 'KNOWN' ? (
                <div className="space-y-3 p-3 bg-canvas-subtle/50 rounded-xl border border-canvas-border">
                  <div className="flex gap-4 pb-1 border-b border-canvas-border">
                    <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink-primary">
                      <input
                        type="radio"
                        name="offeringItemType"
                        checked={offeringItemType === 'PRODUCT'}
                        onChange={() => {
                          setOfferingItemType('PRODUCT');
                          setOfferingServiceCode('');
                        }}
                        className="text-indigo-600"
                      />
                      <span>Physical Product</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink-primary">
                      <input
                        type="radio"
                        name="offeringItemType"
                        checked={offeringItemType === 'SERVICE'}
                        onChange={() => {
                          setOfferingItemType('SERVICE');
                          setOfferingProductCode('');
                          setOfferingGradeCode('');
                        }}
                        className="text-indigo-600"
                      />
                      <span>Specialized Service</span>
                    </label>
                  </div>

                  {offeringItemType === 'PRODUCT' ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block font-medium text-ink-secondary mb-1">Standard Product</label>
                        <select
                          value={offeringProductCode}
                          onChange={(e) => {
                            setOfferingProductCode(e.target.value);
                            setOfferingGradeCode('');
                            const p = productTaxonomies.flatMap((t) => t.canonical_products).find((x) => x.product_code === e.target.value);
                            if (p) setOfferingTitle(p.canonical_name);
                          }}
                          className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                        >
                          <option value="">-- Select Product --</option>
                          {productTaxonomies.flatMap((t) => t.canonical_products).map((p) => (
                            <option key={p.product_code} value={p.product_code}>
                              {p.canonical_name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block font-medium text-ink-secondary mb-1">Standard Grade</label>
                        <select
                          value={offeringGradeCode}
                          onChange={(e) => setOfferingGradeCode(e.target.value)}
                          disabled={!selectedProduct || selectedProduct.grades.length === 0}
                          className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary disabled:opacity-50"
                        >
                          <option value="">-- Standard Grade --</option>
                          {selectedProduct?.grades.map((g) => (
                            <option key={g.grade_code} value={g.grade_code}>
                              {g.grade_name} ({g.governing_standard || 'Standard'})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block font-medium text-ink-secondary mb-1">Service Capability</label>
                      <select
                        value={offeringServiceCode}
                        onChange={(e) => {
                          setOfferingServiceCode(e.target.value);
                          const s = serviceTaxonomies.find((x) => x.service_code === e.target.value);
                          if (s) setOfferingTitle(s.canonical_name);
                        }}
                        className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                      >
                        <option value="">-- Select Service Capability --</option>
                        {serviceTaxonomies.map((s) => (
                          <option key={s.service_code} value={s.service_code}>
                            {s.canonical_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3 p-3 bg-canvas-subtle/50 rounded-xl border border-canvas-border">
                  <div>
                    <label className="block font-medium text-ink-secondary mb-1">Industry Sector</label>
                    <select
                      value={offeringSector}
                      onChange={(e) => setOfferingSector(e.target.value)}
                      className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                    >
                      <option value="">-- Select Industry / Sector --</option>
                      {INDUSTRY_SECTORS.map((sec) => (
                        <option key={sec} value={sec}>
                          {sec}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-ink-secondary mb-1">Technical Specifications / Scope</label>
                    <textarea
                      rows={2}
                      value={offeringSpecs}
                      onChange={(e) => setOfferingSpecs(e.target.value)}
                      placeholder="e.g. Dimensions, alloy grade, purity, mobilization readiness, certifications..."
                      className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block font-medium text-ink-secondary mb-1">
                  Offering Display Title *
                </label>
                <input
                  type="text"
                  required
                  value={offeringTitle}
                  onChange={(e) => setOfferingTitle(e.target.value)}
                  placeholder="e.g. Fe 550D TMT Steel Rebars 16mm or Heavy Fleet Haulage"
                  className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Declared Monthly Capacity</label>
                  <input
                    type="number"
                    min="0"
                    value={offeringCapacity}
                    onChange={(e) => setOfferingCapacity(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 5000"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Capacity Unit</label>
                  <select
                    value={offeringUnit}
                    onChange={(e) => setOfferingUnit(e.target.value)}
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  >
                    {UNIVERSAL_UNITS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Already Committed Volume (Optional)</label>
                  <input
                    type="number"
                    min="0"
                    max={typeof offeringCapacity === 'number' ? offeringCapacity : undefined}
                    value={offeringCommittedVolume}
                    onChange={(e) => setOfferingCommittedVolume(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 20 (prior contracted volume)"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                  <span className="text-[10px] text-ink-muted">Locks prior commitments to calculate available spot volume</span>
                </div>
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Minimum Order Qty (MOQ)</label>
                  <input
                    type="number"
                    min="1"
                    value={offeringMoq}
                    onChange={(e) => setOfferingMoq(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 5"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Lead Time (Days)</label>
                  <input
                    type="number"
                    min="0"
                    value={offeringLeadTime}
                    onChange={(e) => setOfferingLeadTime(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 7"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-ink-secondary mb-1">Geographic Coverage (Comma-separated)</label>
                <input
                  type="text"
                  value={offeringCoverage}
                  onChange={(e) => setOfferingCoverage(e.target.value)}
                  placeholder="Pune, Mumbai, Western Maharashtra"
                  className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                />
              </div>

              <div className="flex items-center gap-4 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={offeringCertificates}
                    onChange={(e) => setOfferingCertificates(e.target.checked)}
                    className="rounded text-indigo-600"
                  />
                  <span>Provides Test Certificates</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={offeringPublicIndicative}
                    onChange={(e) => setOfferingPublicIndicative(e.target.checked)}
                    className="rounded text-indigo-600"
                  />
                  <span>Share Indicative Price</span>
                </label>
              </div>

              <div>
                <label className="block font-medium text-ink-secondary mb-1">
                  Quality Accreditations / Certifications (Comma-separated)
                </label>
                <input
                  type="text"
                  value={offeringCertifications}
                  onChange={(e) => {
                    setOfferingCertifications(e.target.value);
                    if (e.target.value.trim() && !offeringCertificates) {
                      setOfferingCertificates(true);
                    }
                  }}
                  placeholder="e.g. IS 16415, ISO 9001:2015, NABL Lab Certified"
                  className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary text-sm"
                />
                <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                  <span className="text-[11px] text-ink-muted">Quick add:</span>
                  {['IS 16415', 'ISO 9001:2015', 'NABL Lab Certified', 'BIS Standard', 'GreenPro'].map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => {
                        const current = offeringCertifications ? offeringCertifications.split(',').map((s) => s.trim()).filter(Boolean) : [];
                        if (!current.includes(tag)) {
                          setOfferingCertifications([...current, tag].join(', '));
                          setOfferingCertificates(true);
                        }
                      }}
                      className="text-[11px] px-2 py-0.5 rounded-md bg-canvas-card border border-canvas-border hover:border-indigo-400 hover:text-indigo-600 transition-colors"
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              </div>

              {offeringPublicIndicative && (
                <div className="p-3 bg-canvas-subtle rounded-xl space-y-2 border border-canvas-border">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-medium text-ink-secondary mb-1">Price Min (₹)</label>
                      <input
                        type="number"
                        value={offeringPriceMin}
                        onChange={(e) => setOfferingPriceMin(e.target.value === '' ? '' : Number(e.target.value))}
                        placeholder="5200"
                        className="w-full rounded-lg border border-canvas-border bg-canvas-card px-2 py-1 text-ink-primary"
                      />
                    </div>
                    <div>
                      <label className="block font-medium text-ink-secondary mb-1">Price Max (₹)</label>
                      <input
                        type="number"
                        value={offeringPriceMax}
                        onChange={(e) => setOfferingPriceMax(e.target.value === '' ? '' : Number(e.target.value))}
                        placeholder="5600"
                        className="w-full rounded-lg border border-canvas-border bg-canvas-card px-2 py-1 text-ink-primary"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block font-medium text-ink-secondary mb-1">Pricing Basis</label>
                    <select
                      value={offeringPricingBasis}
                      onChange={(e) => setOfferingPricingBasis(e.target.value)}
                      className="w-full rounded-lg border border-canvas-border bg-canvas-card px-2 py-1 text-ink-primary"
                    >
                      <option value="EX_WORKS">Ex-Works (Site Dispatch)</option>
                      <option value="FOR_DELIVERED">FOR (Delivered to Destination)</option>
                      <option value="FOB">FOB (Freight on Board)</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-canvas-border">
                <button
                  type="button"
                  onClick={() => {
                    setShowOfferingModal(false);
                    resetOfferingForm();
                  }}
                  className="px-4 py-2 border border-canvas-border rounded-lg text-ink-secondary hover:bg-canvas-subtle"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editingOffering ? updateOfferingMutation.isPending : createOfferingMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50"
                >
                  {editingOffering
                    ? (updateOfferingMutation.isPending ? 'Updating...' : 'Update Offering')
                    : (createOfferingMutation.isPending ? 'Adding...' : 'Add Offering')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Requirement Modal */}
      {showRequirementModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-canvas-card border border-canvas-border rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center pb-2 border-b border-canvas-border">
              <h3 className="font-bold text-base text-ink-primary">
                {editingRequirement ? 'Edit Procurement Requirement' : 'Add Procurement Requirement'}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowRequirementModal(false);
                  resetRequirementForm();
                }}
                className="text-ink-muted hover:text-ink-primary text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddRequirementSubmit} className="space-y-4 text-xs">
              {/* Entry Mode Selector */}
              <div className="flex rounded-lg bg-canvas-subtle p-1 border border-canvas-border">
                <button
                  type="button"
                  onClick={() => {
                    setReqEntryMode('KNOWN');
                    setReqProductCode('');
                    setReqGradeCode('');
                    setReqServiceCode('');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all ${
                    reqEntryMode === 'KNOWN'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  🔍 Standard Catalog
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setReqEntryMode('CUSTOM');
                    setReqProductCode('');
                    setReqGradeCode('');
                    setReqServiceCode('');
                  }}
                  className={`flex-1 py-1.5 px-3 rounded-md text-xs font-semibold transition-all ${
                    reqEntryMode === 'CUSTOM'
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  ✨ Custom Product / Service
                </button>
              </div>

              {reqEntryMode === 'KNOWN' ? (
                <div className="space-y-3 p-3 bg-canvas-subtle/50 rounded-xl border border-canvas-border">
                  <div className="flex gap-4 pb-1 border-b border-canvas-border">
                    <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink-primary">
                      <input
                        type="radio"
                        name="reqItemType"
                        checked={reqItemType === 'PRODUCT'}
                        onChange={() => {
                          setReqItemType('PRODUCT');
                          setReqServiceCode('');
                        }}
                        className="text-indigo-600"
                      />
                      <span>Physical Material / Product</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer font-medium text-ink-primary">
                      <input
                        type="radio"
                        name="reqItemType"
                        checked={reqItemType === 'SERVICE'}
                        onChange={() => {
                          setReqItemType('SERVICE');
                          setReqProductCode('');
                          setReqGradeCode('');
                        }}
                        className="text-indigo-600"
                      />
                      <span>Specialized Service</span>
                    </label>
                  </div>

                  {reqItemType === 'PRODUCT' ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block font-medium text-ink-secondary mb-1">Target Product</label>
                        <select
                          value={reqProductCode}
                          onChange={(e) => {
                            setReqProductCode(e.target.value);
                            setReqGradeCode('');
                            const p = productTaxonomies.flatMap((t) => t.canonical_products).find((x) => x.product_code === e.target.value);
                            if (p) setReqTitle(p.canonical_name);
                          }}
                          className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                        >
                          <option value="">-- Select Product --</option>
                          {productTaxonomies.flatMap((t) => t.canonical_products).map((p) => (
                            <option key={p.product_code} value={p.product_code}>
                              {p.canonical_name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block font-medium text-ink-secondary mb-1">Required Grade</label>
                        <select
                          value={reqGradeCode}
                          onChange={(e) => setReqGradeCode(e.target.value)}
                          disabled={!selectedReqProduct || selectedReqProduct.grades.length === 0}
                          className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary disabled:opacity-50"
                        >
                          <option value="">-- Standard Grade --</option>
                          {selectedReqProduct?.grades.map((g) => (
                            <option key={g.grade_code} value={g.grade_code}>
                              {g.grade_name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block font-medium text-ink-secondary mb-1">Target Service Capability</label>
                      <select
                        value={reqServiceCode}
                        onChange={(e) => {
                          setReqServiceCode(e.target.value);
                          const s = serviceTaxonomies.find((x) => x.service_code === e.target.value);
                          if (s) setReqTitle(s.canonical_name);
                        }}
                        className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                      >
                        <option value="">-- Select Service --</option>
                        {serviceTaxonomies.map((s) => (
                          <option key={s.service_code} value={s.service_code}>
                            {s.canonical_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3 p-3 bg-canvas-subtle/50 rounded-xl border border-canvas-border">
                  <div>
                    <label className="block font-medium text-ink-secondary mb-1">Industry Sector</label>
                    <select
                      value={reqSector}
                      onChange={(e) => setReqSector(e.target.value)}
                      className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                    >
                      <option value="">-- Select Industry / Sector --</option>
                      {INDUSTRY_SECTORS.map((sec) => (
                        <option key={sec} value={sec}>
                          {sec}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-ink-secondary mb-1">Procurement Notes / Scope</label>
                    <textarea
                      rows={2}
                      value={reqNotes}
                      onChange={(e) => setReqNotes(e.target.value)}
                      placeholder="e.g. Specific dimension, delivery location requirements, special inspection needs..."
                      className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block font-medium text-ink-secondary mb-1">
                  Requirement Title / Material Name *
                </label>
                <input
                  type="text"
                  required
                  value={reqTitle}
                  onChange={(e) => setReqTitle(e.target.value)}
                  placeholder="e.g. 1000 MT Structural Steel Fe 500D or Crane Rental"
                  className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Required Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={reqQuantity}
                    onChange={(e) => setReqQuantity(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 1000"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Unit</label>
                  <select
                    value={reqUnit}
                    onChange={(e) => setReqUnit(e.target.value)}
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  >
                    {UNIVERSAL_UNITS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Delivery City</label>
                  <input
                    type="text"
                    value={reqCity}
                    onChange={(e) => setReqCity(e.target.value)}
                    placeholder="e.g. Pune"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Target Timeline (Days)</label>
                  <input
                    type="number"
                    min="1"
                    value={reqTimeline}
                    onChange={(e) => setReqTimeline(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 45"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Target Budget Indication (₹)</label>
                  <input
                    type="number"
                    value={reqBudget}
                    onChange={(e) => setReqBudget(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="e.g. 5400"
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  />
                </div>
                <div>
                  <label className="block font-medium text-ink-secondary mb-1">Urgency</label>
                  <select
                    value={reqUrgency}
                    onChange={(e: any) => setReqUrgency(e.target.value)}
                    className="w-full rounded-lg border border-canvas-border bg-canvas-subtle px-3 py-2 text-ink-primary"
                  >
                    <option value="IMMEDIATE">Immediate (Spot Requirement)</option>
                    <option value="PLANNED">Planned (Target Project)</option>
                    <option value="EXPLORATORY">Exploratory / Research</option>
                  </select>
                </div>
              </div>

              <div className="pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reqBudgetPublic}
                    onChange={(e) => setReqBudgetPublic(e.target.checked)}
                    className="rounded text-indigo-600"
                  />
                  <span>Disclose target budget in RFQ brief (Private by default)</span>
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-canvas-border">
                <button
                  type="button"
                  onClick={() => {
                    setShowRequirementModal(false);
                    resetRequirementForm();
                  }}
                  className="px-4 py-2 border border-canvas-border rounded-lg text-ink-secondary hover:bg-canvas-subtle"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editingRequirement ? updateRequirementMutation.isPending : createRequirementMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50"
                >
                  {editingRequirement
                    ? (updateRequirementMutation.isPending ? 'Updating...' : 'Update Requirement')
                    : (createRequirementMutation.isPending ? 'Adding...' : 'Add Requirement')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
