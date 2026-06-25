import React from 'react';

interface ConfidenceBarProps {
  label: string;
  value: number; // 0 to 100
  color?: 'green' | 'red' | 'amber' | 'cyan' | 'purple';
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ label, value, color = 'green' }) => {
  const getBarColor = () => {
    switch (color) {
      case 'red':
        return 'var(--risk-critical)';
      case 'amber':
        return 'var(--accent-amber)';
      case 'cyan':
        return 'var(--accent-cyan)';
      case 'purple':
        return 'var(--accent-purple)';
      case 'green':
      default:
        return 'var(--accent-green)';
    }
  };

  const barColor = getBarColor();
  const clampedValue = Math.max(0, Math.min(100, value));

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        width: '100%',
        margin: '6px 0',
      }}
    >
      <span
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-display)',
          color: 'var(--text-secondary)',
          minWidth: '110px',
          textAlign: 'left',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: '4px',
          background: 'var(--bg-elevated)',
          borderRadius: '2px',
          overflow: 'hidden',
          border: '1px solid var(--border)',
        }}
      >
        <div
          style={{
            width: `${clampedValue}%`,
            height: '100%',
            background: barColor,
            borderRadius: '2px',
            transition: 'width 600ms var(--ease-snap)',
          }}
        />
      </div>
      <span
        style={{
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          minWidth: '36px',
          textAlign: 'right',
          color: barColor,
          fontWeight: 600,
        }}
      >
        {clampedValue.toFixed(0)}%
      </span>
    </div>
  );
};

export default ConfidenceBar;
