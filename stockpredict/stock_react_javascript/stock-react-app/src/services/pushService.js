// Push Notification Service
//
// Encapsulates the browser-side subscription lifecycle for web push:
//   isSupported() → caller decides whether to render the toggle
//   getStatus()   → 'unsupported' | 'denied' | 'subscribed' | 'idle'
//   subscribe()   → requests permission, registers SW, calls PushManager,
//                   POSTs subscription to backend
//   unsubscribe() → unsubscribe locally + DELETE on backend
//
// The actual push handling lives in public/service-worker.js. This file
// is the bridge between the UI and that worker.

import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

const SERVICE_WORKER_URL = '/stock-app/service-worker.js';
const SERVICE_WORKER_SCOPE = '/stock-app/';

/** Convert a base64url-encoded VAPID public key to the Uint8Array the
 *  PushManager API requires.
 *  See https://developer.mozilla.org/en-US/docs/Web/API/PushManager/subscribe
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

class PushService {
  /** Quick capability gate the UI uses to decide whether to render the
   *  push toggle at all. Returns false on insecure contexts (push
   *  requires HTTPS or localhost) and on browsers without SW + Push. */
  isSupported() {
    return (
      typeof window !== 'undefined' &&
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  /** Inspect current state without prompting the user.
   *  Returns one of:
   *    'unsupported' – browser can't do push
   *    'denied'      – user explicitly blocked notifications
   *    'subscribed'  – we already have an active PushSubscription
   *    'idle'        – supported but not subscribed yet
   */
  async getStatus() {
    if (!this.isSupported()) return 'unsupported';
    if (Notification.permission === 'denied') return 'denied';
    try {
      const reg = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE);
      if (!reg) return 'idle';
      const sub = await reg.pushManager.getSubscription();
      return sub ? 'subscribed' : 'idle';
    } catch (e) {
      // If the SW lookup fails, treat as idle — the user can still try
      // to subscribe (which will re-register).
      return 'idle';
    }
  }

  async _registerWorker() {
    return navigator.serviceWorker.register(SERVICE_WORKER_URL, {
      scope: SERVICE_WORKER_SCOPE,
    });
  }

  async _fetchVapidPublicKey() {
    const res = await httpClient.get(API_ENDPOINTS.PUSH_VAPID_PUBLIC_KEY);
    if (!res.success || !res.data?.public_key) {
      // Surface the backend's 503 ("not configured") as a clear error
      // the toggle UI can show — not all environments have VAPID keys.
      const detail = res.error?.message || res.error?.detail || 'not configured';
      throw new Error(`VAPID public key unavailable: ${detail}`);
    }
    return res.data.public_key;
  }

  /** Full subscribe flow:
   *  1. Request notification permission (must be invoked from a click).
   *  2. Register the service worker.
   *  3. Fetch VAPID public key.
   *  4. PushManager.subscribe.
   *  5. POST the subscription JSON to the backend.
   *
   *  Returns { success: true } on completion or
   *  { success: false, error } on any step that fails.
   */
  async subscribe() {
    if (!this.isSupported()) {
      return { success: false, error: { message: 'Trình duyệt không hỗ trợ thông báo đẩy' } };
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        return { success: false, error: { message: 'Bạn cần cho phép thông báo trong trình duyệt' } };
      }

      const registration = await this._registerWorker();
      // Wait until the worker is active — subscribe() can race with
      // installation on a brand-new SW.
      if (!registration.active) {
        await navigator.serviceWorker.ready;
      }

      const publicKey = await this._fetchVapidPublicKey();
      const applicationServerKey = urlBase64ToUint8Array(publicKey);

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey,
      });

      const json = subscription.toJSON();
      const res = await httpClient.post(API_ENDPOINTS.PUSH_SUBSCRIBE, {
        endpoint: json.endpoint,
        keys: json.keys,
        user_agent: navigator.userAgent || undefined,
      });
      if (!res.success) {
        // Roll back the browser subscription so the user can retry —
        // otherwise getStatus() reports 'subscribed' but the server
        // doesn't know about us.
        try { await subscription.unsubscribe(); } catch (_) { /* best-effort */ }
        return { success: false, error: res.error || { message: 'Đăng ký thất bại' } };
      }
      return { success: true };
    } catch (e) {
      return { success: false, error: { message: e.message || 'Đăng ký thất bại' } };
    }
  }

  /** Tear down the local subscription and tell the backend to drop the row.
   *  Idempotent — calling on an unsubscribed browser is a noop. */
  async unsubscribe() {
    if (!this.isSupported()) {
      return { success: true };
    }
    try {
      const reg = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE);
      if (!reg) return { success: true };
      const sub = await reg.pushManager.getSubscription();
      if (!sub) return { success: true };

      const endpoint = sub.endpoint;
      await sub.unsubscribe();
      // Backend delete is best-effort — if it fails, the next push will
      // 410 and the consumer will prune the row server-side anyway.
      await httpClient.delete(API_ENDPOINTS.PUSH_UNSUBSCRIBE(endpoint));
      return { success: true };
    } catch (e) {
      return { success: false, error: { message: e.message || 'Hủy đăng ký thất bại' } };
    }
  }
}

const pushServiceInstance = new PushService();
export default pushServiceInstance;
