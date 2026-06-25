import React from 'react';

interface LiveDotProps {
  status?: 'live' | 'degraded' | 'offline';
}

export const LiveDot: React.FC<LiveDotProps> = ({ status = 'live' }) => {
  const getClassName = () => {
    switch (status) {
      case 'degraded':
        return 'live-dot-amber';
      case 'offline':
        return 'live-dot-red';
      case 'live':
      default:
        return 'live-dot-green';
    }
  };

  return (
    <span
      className={getClassName()}
      style={{
        display: 'inline-block',
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        flexShrink: 0,
        marginRight: '6px',
        verticalAlign: 'middle',
      }}
    />
  );
};

export default LiveDot;
