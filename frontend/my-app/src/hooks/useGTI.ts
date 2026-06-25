import { useState, useEffect } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export interface GTIState {
  score: number;
  delta: number;
  trend: number[];
}

// Global shared state for GTI to prevent mismatch between components
let globalGTI: GTIState | null = null;
const globalListeners = new Set<(state: GTIState | null) => void>();
let globalFetchPromise: Promise<void> | null = null;
let globalWsSubscribed = false;

export function useGTI() {
  const [gti, setGTI] = useState<GTIState | null>(globalGTI);
  const { subscribe } = useWebSocket();

  useEffect(() => {
    // Register listener
    globalListeners.add(setGTI);

    // If we don't have the initial data and aren't fetching it yet, start fetching
    if (!globalGTI && !globalFetchPromise) {
      const fetchInitialGTI = async () => {
        try {
          const res = await axios.get(`${API_BASE}/risk/gti`);
          const historyRes = await axios.get(`${API_BASE}/risk/gti/history?limit=12`);
          
          const currentScore = res.data?.current_score ?? 50.0;
          let delta = 0.0;
          let trend = [50, 52, 48, 55, 60, 58, 62, 65, 68, 67, 66, 68];
          
          if (historyRes.data && historyRes.data.length > 0) {
            trend = historyRes.data.map((h: any) => h.score).reverse();
            if (historyRes.data.length > 1) {
              delta = parseFloat((currentScore - historyRes.data[1].score).toFixed(1));
            }
          }

          globalGTI = {
            score: currentScore,
            delta,
            trend,
          };
          
          // Notify all active hooks
          globalListeners.forEach((listener) => listener(globalGTI));
        } catch (err) {
          console.warn('Failed to load initial GTI, using defaults:', err);
          globalGTI = {
            score: 68.5,
            delta: 2.1,
            trend: [50, 52, 48, 55, 60, 58, 62, 65, 68, 67, 66, 68],
          };
          globalListeners.forEach((listener) => listener(globalGTI));
        }
      };
      globalFetchPromise = fetchInitialGTI();
    }

    // Subscribe to WebSocket updates only once globally
    let subId: string | null = null;
    if (!globalWsSubscribed) {
      globalWsSubscribed = true;
      subId = subscribe('gti_update', (msg: any) => {
        // Support both msg.gti (from mock) and msg.score (from backend)
        const score = msg.gti !== undefined ? msg.gti : msg.score;
        if (score === undefined) return;
        
        globalGTI = {
          score: score,
          delta: msg.delta !== undefined ? msg.delta : 0.0,
          trend: msg.trend || (globalGTI ? globalGTI.trend : []),
        };
        globalListeners.forEach((listener) => listener(globalGTI));
      });
    }

    return () => {
      globalListeners.delete(setGTI);
    };
  }, []);

  return gti;
}
