// F-083 — Live alert toast + alert history panel
import React, { useState, useEffect, useRef } from 'react';
import { Bell, BellOff, X, TrendingUp, TrendingDown, Wifi, WifiOff } from 'lucide-react';

// ── Toast notification ────────────────────────────────────────────────────────

const Toast = ({ alert, onClose }) => {
  useEffect(() => {
    const t = setTimeout(onClose, 6000);
    return () => clearTimeout(t);
  }, [onClose]);

  const isBuy = alert.action === 'BUY';
  const color = isBuy ? '#10b981' : '#f59e0b';
  const Icon = isBuy ? TrendingUp : TrendingDown;

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
      background: '#1f2937', border: `1px solid ${color}66`,
      borderRadius: 12, padding: '14px 16px', minWidth: 280, maxWidth: 360,
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      animation: 'slideIn 0.3s ease',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: color + '22', display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={18} color={color} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontWeight: 800, fontSize: 15, color: '#f9fafb' }}>{alert.ticker}</span>
            <span style={{
              padding: '1px 8px', borderRadius: 5, fontSize: 11, fontWeight: 700,
              background: color + '22', color,
            }}>{alert.action}</span>
          </div>
          <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>
            {alert.regime && <span>{alert.regime} · </span>}
            {alert.confidence != null && <span>{(alert.confidence * 100).toFixed(0)}% confidence</span>}
          </div>
          {(alert.stop_price || alert.target_price) && (
            <div style={{ fontSize: 11, color: '#6b7280', marginTop: 3, display: 'flex', gap: 10 }}>
              {alert.stop_price && <span>Stop {alert.stop_price.toFixed(2)}</span>}
              {alert.target_price && <span>Target {alert.target_price.toFixed(2)}</span>}
            </div>
          )}
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#6b7280',
          cursor: 'pointer', padding: 4, flexShrink: 0,
        }}>
          <X size={14} />
        </button>
      </div>
    </div>
  );
};

// ── History panel ─────────────────────────────────────────────────────────────

const HistoryPanel = ({ alerts, onClose, onMarkAllRead, onClear, connected }) => {
  const color = (action) => action === 'BUY' ? '#10b981' : '#f59e0b';

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 340, zIndex: 9998,
      background: '#111827', borderLeft: '1px solid #374151',
      display: 'flex', flexDirection: 'column',
      boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
    }}>
      {/* header */}
      <div style={{
        padding: '16px 16px 12px', borderBottom: '1px solid #1f2937',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Bell size={16} color="#a78bfa" />
        <span style={{ fontWeight: 700, fontSize: 15, color: '#f9fafb', flex: 1 }}>Alert History</span>
        <span style={{
          display: 'flex', alignItems: 'center', gap: 4, fontSize: 11,
          color: connected ? '#10b981' : '#6b7280',
        }}>
          {connected ? <Wifi size={11} /> : <WifiOff size={11} />}
          {connected ? 'Live' : 'Offline'}
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', padding: 4 }}>
          <X size={16} />
        </button>
      </div>

      {/* actions */}
      {alerts.length > 0 && (
        <div style={{ padding: '8px 16px', display: 'flex', gap: 8, borderBottom: '1px solid #1f2937' }}>
          <button onClick={onMarkAllRead} style={btnStyle}>Mark all read</button>
          <button onClick={onClear} style={{ ...btnStyle, color: '#ef4444' }}>Clear</button>
        </div>
      )}

      {/* list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {alerts.length === 0 ? (
          <div style={{ color: '#6b7280', textAlign: 'center', padding: 40, fontSize: 13 }}>
            No alerts yet. Alerts fire when the scheduler detects a BUY or SELL_SHORT signal.
          </div>
        ) : (
          alerts.map(a => (
            <div key={a.id} style={{
              padding: '12px 16px', borderBottom: '1px solid #1f2937',
              background: a.read ? 'transparent' : 'rgba(167,139,250,0.06)',
              display: 'flex', gap: 10, alignItems: 'flex-start',
            }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                background: a.read ? 'transparent' : '#a78bfa',
              }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: 13, color: '#f9fafb' }}>{a.ticker}</span>
                  <span style={{
                    padding: '1px 7px', borderRadius: 5, fontSize: 10, fontWeight: 700,
                    background: color(a.action) + '22', color: color(a.action),
                  }}>{a.action}</span>
                  <span style={{ fontSize: 10, color: '#6b7280', marginLeft: 'auto' }}>{a.bar_date}</span>
                </div>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>
                  {a.regime && `${a.regime} · `}
                  {a.confidence != null && `${(a.confidence * 100).toFixed(0)}% conf`}
                  {a.stop_price && ` · Stop ${a.stop_price.toFixed(2)}`}
                  {a.target_price && ` · Target ${a.target_price.toFixed(2)}`}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const btnStyle = {
  background: 'none', border: '1px solid #374151', borderRadius: 6,
  padding: '4px 10px', color: '#9ca3af', cursor: 'pointer', fontSize: 11,
};

// ── AlertCenter — combines bell button + toast + history ──────────────────────

let _toastId = 0;

const AlertCenter = ({ alerts, unread, connected, onMarkAllRead, onClear }) => {
  const [open, setOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  const prevLen = useRef(alerts.length);

  // Show toast for the newest unread alert
  useEffect(() => {
    if (alerts.length > prevLen.current) {
      const newest = alerts[0];
      if (!newest.read) {
        const id = ++_toastId;
        setToasts(ts => [...ts, { ...newest, _toastId: id }]);
      }
    }
    prevLen.current = alerts.length;
  }, [alerts]);

  const dismissToast = (id) => setToasts(ts => ts.filter(t => t._toastId !== id));

  const handleOpen = () => {
    setOpen(true);
    onMarkAllRead();
  };

  return (
    <>
      {/* Bell button — injected into the Header toolbar */}
      <button
        onClick={handleOpen}
        title="Alert history"
        style={{
          position: 'relative',
          background: 'none', border: 'none', color: unread > 0 ? '#a78bfa' : '#6b7280',
          cursor: 'pointer', padding: 6, display: 'flex', alignItems: 'center',
        }}
      >
        {unread > 0 ? <Bell size={18} /> : <BellOff size={18} />}
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: 1, right: 1,
            width: 16, height: 16, borderRadius: '50%',
            background: '#ef4444', color: '#fff',
            fontSize: 9, fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {/* Toast notifications */}
      {toasts.map(t => (
        <Toast key={t._toastId} alert={t} onClose={() => dismissToast(t._toastId)} />
      ))}

      {/* History slide-in panel */}
      {open && (
        <HistoryPanel
          alerts={alerts}
          connected={connected}
          onClose={() => setOpen(false)}
          onMarkAllRead={onMarkAllRead}
          onClear={onClear}
        />
      )}

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);   opacity: 1; }
        }
      `}</style>
    </>
  );
};

export default AlertCenter;
