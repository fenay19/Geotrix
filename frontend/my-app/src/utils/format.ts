export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return '—';
  // Check if value is already a decimal representation (e.g. 0.082) or percentage representation (e.g. 8.2)
  // Let's assume input is percentage score (e.g. 8.2 representing 8.2%) or standard multiplier.
  return `${formatNumber(value, decimals)}%`;
}

export function formatCurrency(value: number | null | undefined, currencySymbol = '$', decimals = 2): string {
  if (value == null || isNaN(value)) return '—';
  return `${currencySymbol}${formatNumber(value, decimals)}`;
}

export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  const now = new Date();
  const date = new Date(dateString);
  const diffMs = now.getTime() - date.getTime();
  
  if (isNaN(diffMs) || diffMs < 0) return 'Just now';
  
  const diffSecs = Math.floor(diffMs / 1000);
  if (diffSecs < 60) return `${diffSecs}s ago`;
  
  const diffMins = Math.floor(diffSecs / 60);
  if (diffMins < 60) return `${diffMins}m ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
