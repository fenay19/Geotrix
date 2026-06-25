import { useState, useEffect } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import type { TradingSignal } from '../context/WebSocketContext';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export function useSignals() {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { subscribe, unsubscribe } = useWebSocket();

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const res = await axios.get(`${API_BASE}/signals/with-market`);
        setSignals(res.data || []);
      } catch (err) {
        console.warn('Failed to load initial signals, using empty list:', err);
        setError('Failed to fetch signals');
      } finally {
        setLoading(false);
      }
    };

    fetchSignals();

    // Subscribe to WS updates
    const subId = subscribe('signal_update', (msg: any) => {
      const liveSignal: TradingSignal = msg.signal;
      setSignals((prev) => {
        // Find if this signal exists in our list
        const idx = prev.findIndex((s) => s.market_id === liveSignal.market_id);
        if (idx > -1) {
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...liveSignal };
          return updated;
        } else {
          return [liveSignal, ...prev];
        }
      });
    });

    return () => {
      unsubscribe(subId);
    };
  }, []);

  return { signals, loading, error };
}
