import { useState, useEffect } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import type { GeopoliticalEvent } from '../context/WebSocketContext';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export function useAlerts(minSeverity = 7) {
  const [alerts, setAlerts] = useState<GeopoliticalEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const { subscribe, unsubscribe } = useWebSocket();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await axios.get(`${API_BASE}/events/high-severity?min_severity=${minSeverity}`);
        setAlerts(res.data || []);
      } catch (err) {
        console.warn('Failed to fetch high severity alerts, using empty list:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();

    // Subscribe to WS updates
    const subId = subscribe('event_alert', (msg: any) => {
      const newEvent: GeopoliticalEvent = msg.event;
      
      // Only add if it meets severity filter and isn't already present
      if (newEvent.severity >= minSeverity) {
        setAlerts((prev) => {
          if (prev.some((e) => e.id === newEvent.id)) return prev;
          return [newEvent, ...prev];
        });
      }
    });

    return () => {
      unsubscribe(subId);
    };
  }, [minSeverity]);

  return { alerts, loading };
}
