export function riskColor(score: number): string {
  if (score >= 80) return 'var(--risk-critical)';
  if (score >= 60) return 'var(--risk-high)';
  if (score >= 35) return 'var(--risk-medium)';
  return 'var(--risk-low)';
}

export function riskLabel(score: number): 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 35) return 'MEDIUM';
  return 'LOW';
}
