/* eslint-disable no-restricted-globals */
// Service worker for the Stock Helper PWA.
//
// Single purpose for now: receive web-push payloads from the
// portfolio-service push consumer and show a system notification.
//
// The push payload is the JSON produced by push_service.format_alert_push:
//   { title, body, tag, data: { alert_id, symbol, trigger_price } }
//
// Tag is alert-{alert_id} so duplicate notifications for the same alert
// (a retry or a redeliver) collapse at the OS level.

const APP_BASENAME = '/stock-app';

self.addEventListener('install', () => {
  // Activate immediately on first install — there's nothing to migrate.
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Take control of any tabs that were already open when we installed.
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (err) {
    // If the server sent something non-JSON, fall back to text.
    payload = { title: 'Stock Helper', body: event.data ? event.data.text() : '' };
  }

  const title = payload.title || 'Stock Helper';
  const options = {
    body: payload.body || '',
    tag: payload.tag,
    data: payload.data || {},
    icon: `${APP_BASENAME}/logo192.png`,
    badge: `${APP_BASENAME}/logo192.png`,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  // Focus an existing app tab if there is one, otherwise open the
  // bell-icon dropdown view. (Routing to a per-alert page can come
  // later if we add an alert detail screen.)
  const target = `${APP_BASENAME}/`;
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes(APP_BASENAME) && 'focus' in client) {
            return client.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(target);
        }
        return undefined;
      })
  );
});
