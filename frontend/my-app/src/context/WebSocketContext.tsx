import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000';
const WS_URL = `${WS_BASE}/api/v1/ws/live-risk`;

type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

export interface GeopoliticalEvent {
  id: number;
  title: string;
  description: string;
  event_type: 'war' | 'economic' | 'sanctions' | 'policy' | 'disaster';
  severity: number;
  impact_label: string;
  source: string;
  country_id: number;
  timestamp: string;
  casualties?: number;
  economic_damage?: number;
  escalation_potential?: number;
}

export interface TradingSignal {
  id: number;
  market_id: number;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  uncertainty: number;
  bullish_strength: number;
  bearish_strength: number;
  entry_price: number;
  stop_loss: number;
  target_price: number;
  risk_reward_ratio: number;
  volatility_level: string;
  reasoning: string;
  risk_factors: string[];
  tags: string[];
  created_at?: string;
  market_symbol?: string;
  market_name?: string;
  market_price?: number;
  market_asset_class?: string;
  market_geo_sensitivity?: number;
  win_rate?: number;
  avg_return?: number;
  hold_days?: number;
  total_runs?: number;
  past_signals?: { date: string; type: string; entry: number; exit: number; ret: string; win: boolean }[];
}

type LiveRiskMessage =
  | { type: 'gti_update'; gti: number; delta: number; trend: number[] }
  | { type: 'risk_update'; country_id: string; risk_score: number }
  | { type: 'event_alert'; event: GeopoliticalEvent }
  | { type: 'signal_update'; signal: TradingSignal };

interface WebSocketContextType {
  status: ConnectionStatus;
  feedCount: number;
  subscribe: (type: string, callback: (msg: any) => void) => string;
  unsubscribe: (id: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [feedCount, setFeedCount] = useState<number>(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Map<string, { type: string; cb: (msg: any) => void }>>(new Map());
  const reconnectTimeoutRef = useRef<any>(null);
  const reconnectDelayRef = useRef<number>(1000); // starts at 1s
  const isConnectingRef = useRef<boolean>(false);

  // Throttling buffer
  const bufferRef = useRef<Map<string, any>>(new Map());
  const throttleIntervalRef = useRef<any>(null);

  // Sub/Unsub helpers
  const subscribe = (type: string, callback: (msg: any) => void): string => {
    const id = Math.random().toString(36).substring(2, 9);
    listenersRef.current.set(id, { type, cb: callback });
    return id;
  };

  const unsubscribe = (id: string) => {
    listenersRef.current.delete(id);
  };

  // Connect logic
  const connect = () => {
    if (wsRef.current || isConnectingRef.current) return;

    isConnectingRef.current = true;
    setStatus('reconnecting');
    console.log('Connecting to WebSocket at:', WS_URL);

    try {
      const socket = new WebSocket(WS_URL);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log('WebSocket connection established.');
        setStatus('connected');
        setFeedCount(12); // Mock 12 active API feeds connected
        reconnectDelayRef.current = 1000; // Reset delay
        isConnectingRef.current = false;
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      };

      socket.onmessage = (event) => {
        if (event.data === 'pong') return;
        try {
          const message: LiveRiskMessage = JSON.parse(event.data);
          
          // Queue in buffer for throttled delivery
          bufferRef.current.set(message.type, message);
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      socket.onclose = (event) => {
        console.log(`WebSocket closed (code: ${event.code}). Attempting reconnect...`);
        cleanup();
        scheduleReconnect();
      };

      socket.onerror = (error) => {
        console.warn('WebSocket error:', error);
        socket.close();
      };
    } catch (err) {
      console.error('WebSocket connection crash:', err);
      cleanup();
      scheduleReconnect();
    }
  };

  const cleanup = () => {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current = null;
    }
    isConnectingRef.current = false;
  };

  const scheduleReconnect = () => {
    setStatus('disconnected');
    setFeedCount(0);
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

    const delay = reconnectDelayRef.current;
    console.log(`Scheduling reconnect in ${delay}ms...`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      // Double delay for next attempt (exponential backoff capped at 30s)
      reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
      connect();
    }, delay);
  };

  // Setup connection and throttling intervals
  useEffect(() => {
    connect();

    // Start 250ms throttle flush interval
    throttleIntervalRef.current = setInterval(() => {
      if (bufferRef.current.size === 0) return;

      // Flush all buffered updates to their respective subscribers
      bufferRef.current.forEach((message) => {
        listenersRef.current.forEach((listener) => {
          if (listener.type === message.type) {
            listener.cb(message);
          }
        });
      });
      bufferRef.current.clear();
    }, 250);

    return () => {
      cleanup();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (throttleIntervalRef.current) clearInterval(throttleIntervalRef.current);
    };
  }, []);

  // Mock Feed Generator (for local testing/fallback when connection is offline)
  useEffect(() => {
    let mockInterval: any = null;

    const generateMockMessage = () => {
      if (status === 'connected') return;

      const randomValue = Math.random();
      
      if (randomValue < 0.3) {
        // Mock GTI update
        const change = (Math.random() - 0.48) * 4;
        const baseGti = 62.5 + change;
        const trend = Array.from({ length: 12 }, () => Math.round(55 + Math.random() * 20));
        const gtiMsg = {
          type: 'gti_update',
          gti: parseFloat(baseGti.toFixed(1)),
          delta: parseFloat(change.toFixed(1)),
          trend,
        };
        // Buffer it
        bufferRef.current.set('gti_update', gtiMsg);
      } else if (randomValue < 0.6) {
        // Mock Event Alert
        const regions = [
          { id: 3, name: 'Taiwan Strait', code: 'TW', lat: 23.5, lon: 121 },
          { id: 5, name: 'Red Sea', code: 'SA', lat: 20, lon: 40 },
          { id: 4, name: 'Ukraine Border', code: 'UA', lat: 49, lon: 31 },
          { id: 8, name: 'Strait of Hormuz', code: 'IR', lat: 26, lon: 56 }
        ];
        const selectedRegion = regions[Math.floor(Math.random() * regions.length)];
        const titles = [
          'Military Patrol Activities Intensified',
          'Cyberattack Disrupts Port Infrastructures',
          'Export Tariffs Officially Ratified',
          'Naval Drills Declared in Transit Channel'
        ];
        const event: GeopoliticalEvent = {
          id: Math.floor(Math.random() * 10000),
          title: `${selectedRegion.name}: ${titles[Math.floor(Math.random() * titles.length)]}`,
          description: `Security agencies reported heightened strategic activities and localized countermeasures in the vicinity. Analysts predict short-term trade ripples.`,
          event_type: Math.random() < 0.4 ? 'war' : Math.random() < 0.7 ? 'sanctions' : 'economic',
          severity: parseFloat((6 + Math.random() * 4).toFixed(1)),
          impact_label: Math.random() < 0.5 ? 'HIGH' : 'CRITICAL',
          source: 'Reuters Intel',
          country_id: selectedRegion.id,
          timestamp: new Date().toISOString(),
          casualties: Math.random() < 0.2 ? Math.floor(Math.random() * 10) : 0,
          economic_damage: Math.random() < 0.8 ? parseFloat((10 + Math.random() * 200).toFixed(1)) : 0,
          escalation_potential: Math.floor(3 + Math.random() * 6)
        };

        bufferRef.current.set('event_alert', { type: 'event_alert', event });
      } else {
        // Mock Signal update
        const symbols = ['GOLD', 'OIL_BRENT', 'SP500', 'BTCUSD', 'LMT'];
        const selectedSym = symbols[Math.floor(Math.random() * symbols.length)];
        const types: ('BUY' | 'SELL' | 'HOLD')[] = ['BUY', 'SELL', 'HOLD'];
        const sigType = types[Math.floor(Math.random() * types.length)];
        const confidence = parseFloat((0.55 + Math.random() * 0.4).toFixed(2));
        
        const signal: TradingSignal = {
          id: Math.floor(Math.random() * 10000),
          market_id: symbols.indexOf(selectedSym) + 1,
          signal_type: sigType,
          confidence,
          uncertainty: parseFloat((1 - confidence).toFixed(2)),
          bullish_strength: sigType === 'BUY' ? confidence : sigType === 'SELL' ? parseFloat((1 - confidence).toFixed(2)) : 0.5,
          bearish_strength: sigType === 'SELL' ? confidence : sigType === 'BUY' ? parseFloat((1 - confidence).toFixed(2)) : 0.5,
          entry_price: 100 + Math.random() * 2000,
          stop_loss: 95 + Math.random() * 1900,
          target_price: 110 + Math.random() * 2200,
          risk_reward_ratio: parseFloat((1.5 + Math.random() * 2).toFixed(1)),
          volatility_level: Math.random() < 0.3 ? 'Low' : Math.random() < 0.8 ? 'Medium' : 'High',
          reasoning: `Technical signals cross-referenced with recent updates indicate a strong tactical directional push for ${selectedSym}.`,
          risk_factors: ['Systemic volatility', 'Policy adjustments', 'Macro fluctuations'],
          tags: ['automated-model', selectedSym.toLowerCase()],
          market_symbol: selectedSym,
          market_name: selectedSym === 'GOLD' ? 'Gold Spot' : selectedSym === 'OIL_BRENT' ? 'Brent Crude Oil' : selectedSym
        };

        bufferRef.current.set('signal_update', { type: 'signal_update', signal });
      }
    };

    // If offline, run generator every 7 seconds to keep dashboard active
    if (status !== 'connected') {
      setFeedCount(8); // Mock 8 simulated feeds
      mockInterval = setInterval(generateMockMessage, 7000);
    }

    return () => {
      if (mockInterval) clearInterval(mockInterval);
    };
  }, [status]);

  return (
    <WebSocketContext.Provider value={{ status, feedCount, subscribe, unsubscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
