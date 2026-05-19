// F-083 — SSE hook for real-time BUY/SELL_SHORT alerts
import { useState, useEffect, useCallback, useRef } from 'react';
import { API_ENDPOINTS } from '../constants/api';
import helperService from '../services/helperService';

const MAX_HISTORY = 50;

export function useAlertStream() {
  const [alerts, setAlerts] = useState([]);     // newest first
  const [connected, setConnected] = useState(false);
  const [unread, setUnread] = useState(0);
  const esRef = useRef(null);

  // Seed from REST on mount
  useEffect(() => {
    helperService.getAlerts(20)
      .then(data => {
        if (data?.alerts?.length) {
          setAlerts(data.alerts.map((a, i) => ({ ...a, id: `hist-${i}`, read: true })));
        }
      })
      .catch(() => {});
  }, []);

  // SSE connection
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const url = `${API_ENDPOINTS.HELPER_ALERTS_STREAM}?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        const alert = { ...payload, id: `live-${Date.now()}`, read: false };
        setAlerts(prev => [alert, ...prev].slice(0, MAX_HISTORY));
        setUnread(n => n + 1);
      } catch { /* malformed event — ignore */ }
    };

    es.onerror = () => {
      setConnected(false);
      // Browser auto-reconnects EventSource — no manual retry needed
    };

    return () => {
      es.close();
      setConnected(false);
    };
  }, []);

  const markAllRead = useCallback(() => {
    setAlerts(prev => prev.map(a => ({ ...a, read: true })));
    setUnread(0);
  }, []);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
    setUnread(0);
  }, []);

  return { alerts, connected, unread, markAllRead, clearAlerts };
}
