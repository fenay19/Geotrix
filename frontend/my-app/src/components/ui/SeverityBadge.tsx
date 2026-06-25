import React from 'react';

type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

interface SeverityBadgeProps {
  level?: SeverityLevel;
  score?: number;
  showScore?: boolean;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ level, score, showScore = true }) => {
  // Determine level from score if level is not explicitly provided
  const getLevel = (): SeverityLevel => {
    if (level) return level;
    if (score == null) return 'LOW';
    // Match the risk tiers
    if (score >= 8.0 || score >= 80) return 'CRITICAL';
    if (score >= 6.0 || score >= 60) return 'HIGH';
    if (score >= 3.5 || score >= 35) return 'MEDIUM';
    return 'LOW';
  };

  const activeLevel = getLevel();

  const getStyles = () => {
    switch (activeLevel) {
      case 'CRITICAL':
        return {
          color: 'var(--risk-critical)',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
        };
      case 'HIGH':
        return {
          color: 'var(--accent-amber)',
          backgroundColor: 'rgba(245, 158, 11, 0.12)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
        };
      case 'MEDIUM':
        return {
          color: 'var(--accent-cyan)',
          backgroundColor: 'rgba(6, 182, 212, 0.12)',
          border: '1px solid rgba(6, 182, 212, 0.25)',
        };
      case 'LOW':
      default:
        return {
          color: 'var(--risk-low)',
          backgroundColor: 'rgba(34, 197, 94, 0.12)',
          border: '1px solid rgba(34, 197, 94, 0.25)',
        };
    }
  };

  // Score display format, support both 0-10 scale (backend format) and 0-100 scale
  const formatScore = () => {
    if (score == null) return '';
    return score > 10 ? score.toFixed(0) : score.toFixed(1);
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        fontWeight: 600,
        borderRadius: 'var(--radius-sm)',
        padding: '2px 6px',
        letterSpacing: '0.04em',
        lineHeight: 1.2,
        ...getStyles(),
      }}
    >
      {activeLevel} {showScore && score != null && `· ${formatScore()}`}
    </span>
  );
};

export default SeverityBadge;
