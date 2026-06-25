import React from 'react';

interface SignalPillProps {
  direction: 'BUY' | 'SELL' | 'HOLD';
  size?: 'sm' | 'md' | 'lg';
}

export const SignalPill: React.FC<SignalPillProps> = ({ direction, size = 'md' }) => {
  const getStyles = () => {
    switch (direction) {
      case 'BUY':
        return {
          backgroundColor: 'rgba(0, 255, 136, 0.12)',
          border: '1px solid var(--accent-green)',
          color: 'var(--accent-green)',
        };
      case 'SELL':
        return {
          backgroundColor: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid var(--risk-critical)',
          color: 'var(--risk-critical)',
        };
      case 'HOLD':
      default:
        return {
          backgroundColor: 'rgba(125, 135, 153, 0.12)',
          border: '1px solid var(--text-muted)',
          color: 'var(--text-muted)',
        };
    }
  };

  const getPaddingAndFont = () => {
    switch (size) {
      case 'sm':
        return {
          fontSize: '10px',
          padding: '3px 6px',
        };
      case 'lg':
        return {
          fontSize: '13px',
          padding: '6px 12px',
        };
      case 'md':
      default:
        return {
          fontSize: '11px',
          padding: '4px 8px',
        };
    }
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        textTransform: 'uppercase',
        borderRadius: 'var(--radius-sm)',
        letterSpacing: '0.04em',
        lineHeight: 1,
        ...getStyles(),
        ...getPaddingAndFont(),
      }}
    >
      {direction === 'BUY' && 'BUY'}
      {direction === 'SELL' && 'SELL'}
      {direction === 'HOLD' && 'HOLD'}
    </span>
  );
};

export default SignalPill;
