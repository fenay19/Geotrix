import React from 'react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

interface SparklineProps {
  data: number[];
  color?: 'amber' | 'cyan' | 'green' | 'red';
  height?: number;
  width?: number;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  color = 'cyan',
  height = 48,
  width = 200,
}) => {
  const getStrokeColor = () => {
    switch (color) {
      case 'amber':
        return 'var(--accent-amber)';
      case 'green':
        return 'var(--accent-green)';
      case 'red':
        return 'var(--risk-critical)';
      case 'cyan':
      default:
        return 'var(--accent-cyan)';
    }
  };

  const strokeColor = getStrokeColor();

  // Handle empty or small data arrays safely
  const chartData = (data && data.length > 0 ? data : [0, 0]).map((v, i) => ({
    i,
    v: v ?? 0,
  }));

  return (
    <div style={{ width: width === 200 ? '100%' : `${width}px`, height: `${height}px`, maxWidth: `${width}px` }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Area
            type="monotone"
            dataKey="v"
            stroke={strokeColor}
            fill={strokeColor}
            fillOpacity={0.12}
            strokeWidth={1.5}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Sparkline;
