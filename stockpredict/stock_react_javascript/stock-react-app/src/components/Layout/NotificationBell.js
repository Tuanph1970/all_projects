import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, Check, CheckCheck, Trash2, X } from 'lucide-react';
import notificationService from '../../services/notificationService';

/**
 * Bell-icon widget with an unread badge and a click-to-open dropdown.
 *
 * Refresh strategy: load on mount, refresh whenever the dropdown opens.
 * No interval polling — the user opening the dropdown is the natural
 * cue. If push delivery is added later, the widget can subscribe.
 */
const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await notificationService.list({ limit: 20 });
    if (res.success && res.data) {
      setItems(res.data.items || []);
      setUnread(res.data.unread ?? 0);
    } else {
      setError(res.error?.message || 'Không thể tải thông báo');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Refresh on each open so a returning user sees fresh data.
  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  // Click-outside to close.
  useEffect(() => {
    if (!open) return undefined;
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handleMarkRead = async (id) => {
    const res = await notificationService.markRead(id);
    if (res.success) {
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      setUnread((prev) => Math.max(prev - 1, 0));
    }
  };

  const handleMarkAll = async () => {
    const res = await notificationService.markAllRead();
    if (res.success) {
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    }
  };

  const handleDelete = async (id) => {
    const target = items.find((n) => n.id === id);
    const res = await notificationService.remove(id);
    if (res.success) {
      setItems((prev) => prev.filter((n) => n.id !== id));
      if (target && !target.read) {
        setUnread((prev) => Math.max(prev - 1, 0));
      }
    }
  };

  const formatRelative = (iso) => {
    if (!iso) return '';
    const dt = new Date(iso);
    const diffMs = Date.now() - dt.getTime();
    const mins = Math.round(diffMs / 60_000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        className="notification-button"
        onClick={() => setOpen((s) => !s)}
        aria-label="Thông báo"
        aria-expanded={open}
      >
        <Bell />
        {unread > 0 && (
          <span className="notification-badge" data-testid="notification-badge">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          data-testid="notification-dropdown"
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            right: 0,
            width: 360,
            maxHeight: 480,
            overflowY: 'auto',
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderBottom: '1px solid #f3f4f6',
            }}
          >
            <strong>Thông báo</strong>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleMarkAll}
                disabled={unread === 0}
                title="Đánh dấu đã đọc tất cả"
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  background: 'none', border: 'none',
                  color: unread === 0 ? '#9ca3af' : '#2563eb',
                  cursor: unread === 0 ? 'default' : 'pointer',
                  fontSize: 13,
                }}
              >
                <CheckCheck size={14} />
                Đã đọc tất cả
              </button>
              <button
                onClick={() => setOpen(false)}
                aria-label="Đóng"
                style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {loading && items.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: '#6b7280' }}>
              Đang tải…
            </div>
          ) : error ? (
            <div style={{ padding: 16, color: '#b91c1c', fontSize: 13 }}>{error}</div>
          ) : items.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>
              <Bell size={32} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
              <div>Không có thông báo nào</div>
            </div>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {items.map((n) => (
                <li
                  key={n.id}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid #f3f4f6',
                    background: n.read ? '#fff' : '#eff6ff',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: n.read ? 400 : 600, fontSize: 14 }}>{n.title}</div>
                      {n.body && (
                        <div style={{ fontSize: 13, color: '#4b5563', marginTop: 2 }}>{n.body}</div>
                      )}
                      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                        {formatRelative(n.created_at)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                      {!n.read && (
                        <button
                          onClick={() => handleMarkRead(n.id)}
                          title="Đã đọc"
                          aria-label="Đánh dấu đã đọc"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#2563eb' }}
                        >
                          <Check size={14} />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(n.id)}
                        title="Xóa"
                        aria-label="Xóa thông báo"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
