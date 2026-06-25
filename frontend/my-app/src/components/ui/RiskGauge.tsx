import React, { useEffect, useState, useRef } from 'react';
import { riskColor, riskLabel } from '../../utils/risk';

interface RiskGaugeProps {
  score: number;
  size?: number;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ score, size = 200 }) => {
  const [animatedScore, setAnimatedScore] = useState<number>(score);
  const prevScoreRef = useRef<number>(score);

  useEffect(() => {
    const start = prevScoreRef.current;
    const end = score;
    const duration = 800; // ms
    let startTime: number | null = null;
    let animationFrameId: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = timestamp - startTime;
      const progressPercentage = Math.min(progress / duration, 1);
      
      // Easing: ease-out quad
      const easedProgress = progressPercentage * (2 - progressPercentage);
      const current = start + (end - start) * easedProgress;

      setAnimatedScore(current);

      if (progress < duration) {
        animationFrameId = requestAnimationFrame(animate);
      } else {
        setAnimatedScore(end);
        prevScoreRef.current = end;
      }
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [score]);

  const cx = size / 2;
  const cy = size / 2;
  const strokeWidth = 12;
  const r = size / 2 - 20;
  
  const totalLength = 2 * Math.PI * r;
  const arcSweep = 270; // Sweep angle in degrees
  const arcLength = totalLength * (arcSweep / 360);
  
  // Calculate dash offset: full length when score is 0, 0 offset when score is 100
  const dashOffset = arcLength * (1 - animatedScore / 100);
  
  const currentColor = riskColor(score);
  const currentLabel = riskLabel(score);

  return (
    <div
      style={{
        position: 'relative',
        width: `${size}px`,
        height: `${size}px`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto',
      }}
    >
      <svg width={size} height={size} style={{ transform: 'scaleX(-1)' }}>
        {/* Background Track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${totalLength}`}
          strokeDashoffset={0}
          transform={`rotate(135, ${cx}, ${cy})`}
        />
        {/* Active Arc (Colored) */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={currentColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${arcLength} ${totalLength}`}
          strokeDashoffset={dashOffset}
          transform={`rotate(135, ${cx}, ${cy})`}
          style={{
            transition: 'stroke 400ms var(--ease-snap)',
          }}
        />
      </svg>
      {/* Center Text Panel */}
      <div
        style={{
          position: 'absolute',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
        }}
      >
        <span
          style={{
            fontSize: '40px',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: currentColor,
            lineHeight: 1,
            letterSpacing: '-0.04em',
            transition: 'color 400ms var(--ease-snap)',
          }}
        >
          {animatedScore.toFixed(1)}
        </span>
        <span
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            letterSpacing: '0.08em',
            marginTop: '6px',
            textTransform: 'uppercase',
          }}
        >
          {currentLabel}
        </span>
      </div>
    </div>
  );
};

export default RiskGauge;
