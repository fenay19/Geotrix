import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

interface CandlestickData {
  timestamp: string | Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data: CandlestickData[];
  height?: number;
  livePrice?: number;
}

// Custom shape component for rendering the candlestick body & wicks
const CandlestickShape = (props: any) => {
  const { x, y, width, height, payload, yScale, minPrice, maxPrice } = props;
  if (!payload || height === undefined) return null;

  const { open, close, high, low } = payload;
  const isUp = close >= open;
  
  const color = isUp ? '#22c55e' : 'var(--risk-critical)';
  
  let yHigh, yLow, yBodyTop, yBodyHeight;

  if (typeof yScale === 'function') {
    const yOpen = yScale(open);
    const yClose = yScale(close);
    yHigh = yScale(high);
    yLow = yScale(low);
    yBodyTop = Math.min(yOpen, yClose);
    yBodyHeight = Math.abs(yOpen - yClose);
  } else {
    // Fallback: use the local bar coordinates and ratio
    const bodyPriceDelta = Math.abs(close - open);
    let ratio = 0;
    if (bodyPriceDelta > 0.001) {
      ratio = height / bodyPriceDelta;
      (window as any).__candlestick_ratio = ratio;
    } else {
      const fallbackRatio = (window as any).__candlestick_ratio || (140 / ((maxPrice - minPrice) || 1));
      ratio = fallbackRatio;
    }

    const refPrice = isUp ? close : open;
    yHigh = y + (refPrice - high) * ratio;
    yLow = y + (refPrice - low) * ratio;
    yBodyTop = y;
    yBodyHeight = height;
  }

  const xCenter = x + width / 2;

  return (
    <g>
      {/* Wick (High-Low line) */}
      <line
        x1={xCenter}
        y1={yHigh}
        x2={xCenter}
        y2={yLow}
        stroke={color}
        strokeWidth={1.5}
      />
      {/* Body */}
      <rect
        x={x}
        y={yBodyTop}
        width={width}
        height={Math.max(2, yBodyHeight)} // Ensure at least 2px body visible
        fill={color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
};

export const CandlestickChart: React.FC<CandlestickChartProps> = ({ data, height = 220, livePrice }) => {
  const [hoveredData, setHoveredData] = useState<CandlestickData | null>(null);

  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '12px',
          border: '1px dashed var(--border)',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(255, 255, 255, 0.02)'
        }}
      >
        No historical market data available.
      </div>
    );
  }

  // 1. Sort, incorporate the live price for today, and slice to the last 30 days
  const processedData = React.useMemo(() => {
    const sorted = [...data].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    
    // Resolve current date strings in local time to check if today is in the dataset
    const now = new Date();
    const todayStr = now.toDateString();
    
    const lastCandle = sorted[sorted.length - 1];
    const isLastToday = lastCandle && new Date(lastCandle.timestamp).toDateString() === todayStr;
    
    let finalData = [...sorted];
    
    if (livePrice !== undefined && livePrice !== null) {
      if (isLastToday) {
        // Today's candle is already in history, update it with the live price
        finalData[finalData.length - 1] = {
          ...lastCandle,
          close: livePrice,
          high: Math.max(lastCandle.high, livePrice),
          low: Math.min(lastCandle.low, livePrice),
        };
      } else {
        // Append today's candle
        const lastClose = lastCandle ? lastCandle.close : livePrice;
        const todayCandle: CandlestickData = {
          timestamp: now,
          open: lastClose,
          close: livePrice,
          high: Math.max(lastClose, livePrice),
          low: Math.min(lastClose, livePrice),
          volume: 0,
        };
        finalData.push(todayCandle);
      }
    }
    
    // Slice to the last 30 days
    return finalData.slice(-30);
  }, [data, livePrice]);

  // Format dates dynamically based on data range
  const isIntraday = processedData.length > 1 && 
    (new Date(processedData[processedData.length - 1].timestamp).getTime() - new Date(processedData[0].timestamp).getTime()) < 2 * 24 * 60 * 60 * 1000;

  const chartData = processedData.map((d) => {
    const dateObj = new Date(d.timestamp);
    const formattedDate = isIntraday
      ? dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
      : dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      
    return {
      ...d,
      formattedDate,
      ohlc: [d.open, d.close],
    };
  });

  // Calculate Y-axis padding using only the visible (sliced) data points to ensure proper scaling
  const prices = processedData.flatMap((d) => [d.high, d.low]);
  const minPrice = Math.min(...prices) * 0.99;
  const maxPrice = Math.max(...prices) * 1.01;

  const latestPrice = chartData[chartData.length - 1]?.close;
  const isLastUp = chartData[chartData.length - 1]?.close >= chartData[chartData.length - 1]?.open;
  const refColor = isLastUp ? '#22c55e' : 'var(--risk-critical)';

  const displayData = hoveredData || chartData[chartData.length - 1];

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', background: 'transparent' }}>
      <div style={{ width: '100%', height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 20, left: -20, bottom: 0 }}
            barGap={0}
            onMouseMove={(state) => {
              if (state && state.activePayload && state.activePayload.length > 0) {
                setHoveredData(state.activePayload[0].payload);
              }
            }}
            onMouseLeave={() => setHoveredData(null)}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" opacity={0.15} />
            <XAxis
              dataKey="formattedDate"
              stroke="var(--text-muted)"
              fontSize={10}
              fontFamily="var(--font-mono)"
              tickLine={false}
              axisLine={{ stroke: 'var(--border)' }}
              padding={{ left: 10, right: 30 }}
              interval={6}
            />
            <YAxis
              yAxisId="price"
              domain={[minPrice, maxPrice]}
              stroke="var(--text-muted)"
              fontSize={10}
              fontFamily="var(--font-mono)"
              tickLine={false}
              axisLine={false}
              orientation="right"
              width={60}
              tickFormatter={(val) => val.toFixed(2)}
            />
            <YAxis
              yAxisId="volume"
              domain={[0, (dataMax: any) => dataMax * 4]}
              width={0}
              tick={false}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as CandlestickData;
                  const isUp = item.close >= item.open;
                  return (
                    <div
                      style={{
                        background: 'rgba(26, 29, 36, 0.9)',
                        border: '1px solid var(--border-bright)',
                        borderRadius: 'var(--radius-md)',
                        padding: '8px 12px',
                        backdropFilter: 'blur(4px)',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-primary)',
                        textAlign: 'left',
                        boxShadow: 'var(--shadow)',
                      }}
                    >
                      <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        {new Date(item.timestamp).toLocaleDateString('en-US', {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                      <div>
                        O:{' '}
                        <span style={{ color: 'var(--text-primary)' }}>{item.open.toFixed(2)}</span>
                      </div>
                      <div>
                        H:{' '}
                        <span style={{ color: 'var(--accent-green)' }}>{item.high.toFixed(2)}</span>
                      </div>
                      <div>
                        L:{' '}
                        <span style={{ color: 'var(--risk-critical)' }}>{item.low.toFixed(2)}</span>
                      </div>
                      <div>
                        C:{' '}
                        <span style={{ color: isUp ? '#22c55e' : 'var(--risk-critical)', fontWeight: 600 }}>
                          {item.close.toFixed(2)}
                        </span>
                      </div>
                      <div style={{ marginTop: '4px', color: 'var(--text-muted)' }}>
                        Vol: {item.volume.toLocaleString()}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar
              yAxisId="volume"
              dataKey="volume"
              fill="rgba(6, 182, 212, 0.06)"
              barSize={6}
            />
            <Bar
              yAxisId="price"
              dataKey="ohlc"
              shape={<CandlestickShape minPrice={minPrice} maxPrice={maxPrice} />}
              barSize={12}
            />
            {latestPrice !== undefined && (
              <ReferenceLine
                y={latestPrice}
                yAxisId="price"
                stroke={refColor}
                strokeDasharray="3 3"
                label={{
                  value: latestPrice.toFixed(2),
                  position: 'insideRight',
                  fill: refColor,
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 'bold',
                  offset: 15,
                  dy: -8
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Stats display panel underneath the chart */}
      {displayData && (
        <div style={{
          display: 'flex',
          backgroundColor: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          marginTop: '12px',
          overflow: 'hidden',
        }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '8px 0' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>OPEN</span>
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
              {displayData.open.toFixed(2)}
            </span>
          </div>
          <div style={{ width: '1px', alignSelf: 'stretch', backgroundColor: 'var(--border)', opacity: 0.3 }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '8px 0' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>HIGH</span>
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
              {displayData.high.toFixed(2)}
            </span>
          </div>
          <div style={{ width: '1px', alignSelf: 'stretch', backgroundColor: 'var(--border)', opacity: 0.3 }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '8px 0' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>LOW</span>
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
              {displayData.low.toFixed(2)}
            </span>
          </div>
          <div style={{ width: '1px', alignSelf: 'stretch', backgroundColor: 'var(--border)', opacity: 0.3 }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '8px 0' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>CLOSE</span>
            <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: displayData.close >= displayData.open ? '#22c55e' : 'var(--risk-critical)' }}>
              {displayData.close.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandlestickChart;
