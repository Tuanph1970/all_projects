/**
 * Sentry error tracking initialisation.
 *
 * Only activates when EXPO_PUBLIC_SENTRY_DSN is set in the environment.
 * Safe to call unconditionally — a missing DSN is silently ignored.
 *
 * Usage:
 *   1. Set EXPO_PUBLIC_SENTRY_DSN in your .env file or CI secrets
 *   2. Call initSentry() once at app startup (before any navigation renders)
 *   3. Use captureError(error, context) anywhere in the app to report errors
 */

import * as Sentry from '@sentry/react-native';
import Constants from 'expo-constants';

let _initialised = false;

export function initSentry() {
  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN;
  if (!dsn) return; // No DSN — skip silently (development default)

  Sentry.init({
    dsn,
    environment: __DEV__ ? 'development' : 'production',
    release: Constants.expoConfig?.version ?? '1.0.0',
    debug: __DEV__,
    // Sample 20% of transactions in production to stay in free tier
    tracesSampleRate: __DEV__ ? 1.0 : 0.2,
    // Capture unhandled promise rejections automatically
    enableNative: true,
    // Don't send PII (device IDs, usernames) without explicit opt-in
    sendDefaultPii: false,
  });

  _initialised = true;
}

/**
 * Report an error to Sentry with optional extra context.
 * Falls back to console.error when Sentry is not initialised.
 *
 * @param {Error} error
 * @param {object} [context] - Extra key/value pairs attached to the event
 */
export function captureError(error, context = {}) {
  if (!_initialised) {
    console.error('[captureError]', error, context);
    return;
  }
  Sentry.withScope((scope) => {
    Object.entries(context).forEach(([key, value]) => scope.setExtra(key, value));
    Sentry.captureException(error);
  });
}

/**
 * Attach the current user identity to all subsequent Sentry events.
 * Call after successful login, clear on logout.
 *
 * @param {{ id: string, username?: string }} user
 */
export function setSentryUser(user) {
  if (!_initialised) return;
  // Only send non-PII identifiers — omit email by default
  Sentry.setUser({ id: user.id, username: user.username });
}

export function clearSentryUser() {
  if (!_initialised) return;
  Sentry.setUser(null);
}

export { Sentry };
