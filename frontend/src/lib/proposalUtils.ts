/**
 * Utility helpers for formatting commercial proposal parameters cleanly across UI surfaces.
 */

export function formatUnit(unit?: string | null): string {
  if (!unit) return '';
  const clean = unit.trim().toUpperCase();
  if (clean === 'METRIC_TONNE' || clean === 'METRIC_TON' || clean === 'METRIC_TONNES') {
    return 'MT';
  }
  if (clean === 'KILOGRAM' || clean === 'KILOGRAMS') {
    return 'kg';
  }
  return unit.replace(/_/g, ' ');
}

export function formatQuantity(qty?: number | string | null): string {
  if (qty === null || qty === undefined || qty === '') return '0';
  const num = typeof qty === 'number' ? qty : parseFloat(String(qty));
  if (isNaN(num)) return String(qty);
  return num.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

export function formatCurrencyValue(
  val?: number | string | null,
  currency = 'INR'
): string {
  if (val === null || val === undefined || val === '') return '';
  const num = typeof val === 'number' ? val : parseFloat(String(val));
  if (isNaN(num)) return `${currency} ${val}`;
  return `${currency} ${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function cleanProposalTitle(title?: string | null): string {
  if (!title) return '';
  return title
    .replace(/(\d+)\.0000\s+METRIC_TONNE/g, '$1 MT')
    .replace(/(\d+)\.0000\s+/g, '$1 ')
    .replace(/METRIC_TONNE/g, 'MT');
}
