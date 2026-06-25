import React, { useState, useEffect } from 'react';
import { formatNumber } from '../../utils/format';

interface StatCardProps {
  label: string;
  value: number | string;
  sub?: string;
  delta?: number;
  valueColor?: string;
  decimals?: number;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  sub,
  delta,
  valueColor = 'var(--text-primary)',
  decimals = 2,
}) => {
  const [displayValue, setDisplayValue] = useState<string | number>('0');

  useEffect(() => {
    if (typeof value !== 'number') {
      setDisplayValue(value);
      return;
    }

    const start = 0;
    const end = value;
    const duration = 800; // ms
    let startTime: number | null = null;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = timestamp - startTime;
      const progressPercentage = Math.min(progress / duration, 1);
      
      // Easing function: ease-out quad
      const easedProgress = progressPercentage * (2 - progressPercentage);
      const current = start + (end - start) * easedProgress;

      setDisplayValue(formatNumber(current, decimals));

      if (progress < duration) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(formatNumber(end, decimals));
      }
    };

    requestAnimationFrame(animate);
  }, [value, decimals]);

  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        flex: 1,
        minWidth: '120px',
      }}
    >
      <div>
        <p
          style={{
            fontSize: '10px',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            margin: 0,
            fontWeight: 600,
            fontFamily: 'var(--font-display)',
          }}
        >
          {label}
        </p>
        <p
          style={{
            fontSize: '20px',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: valueColor,
            margin: '4px 0 0',
            lineHeight: 1.2,
          }}
        >
          {displayValue}
        </p>
      </div>
      {(delta !== undefined || sub) && (
        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          {delta !== undefined && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                fontFamily: 'var(--font-mono)',
                color: delta > 0 ? 'var(--accent-green)' : 'var(--risk-critical)',
              }}
            >
              {delta > 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
            </span>
          )}
          {sub && (
            <span
              style={{
                fontSize: '11px',
                color: 'var(--text-secondary)',
              }}
            >
              {sub}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default StatCard;
