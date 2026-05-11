/**
 * Tests for pushService.
 *
 * The browser APIs (Notification, navigator.serviceWorker, PushManager)
 * aren't provided by jsdom, so each test installs lightweight stubs on
 * the globals it cares about. httpClient is mocked at the module level
 * since pushService only uses get/post/delete from it.
 */
import pushService from './pushService';
import httpClient from './httpClient';

jest.mock('./httpClient');

const ok = (data) => ({ success: true, data });
const fail = (msg = 'boom') => ({ success: false, error: { message: msg } });

const installBrowserStubs = ({
  supported = true,
  permission = 'default',
  existingSubscription = null,
  subscribeResult = null,
  subscribeError = null,
  requestPermissionResult = 'granted',
} = {}) => {
  if (!supported) {
    // Strip the capabilities so isSupported() returns false.
    delete global.navigator.serviceWorker;
    delete global.window.PushManager;
    delete global.Notification;
    return {};
  }

  const subscription = subscribeResult || {
    endpoint: 'https://push.example/abc',
    toJSON: () => ({
      endpoint: 'https://push.example/abc',
      keys: { p256dh: 'p', auth: 'a' },
    }),
    unsubscribe: jest.fn().mockResolvedValue(true),
  };

  const pushManager = {
    getSubscription: jest.fn().mockResolvedValue(existingSubscription),
    subscribe: jest.fn().mockImplementation(() =>
      subscribeError ? Promise.reject(subscribeError) : Promise.resolve(subscription)
    ),
  };

  const registration = {
    active: { state: 'activated' },
    pushManager,
  };

  global.navigator.serviceWorker = {
    register: jest.fn().mockResolvedValue(registration),
    getRegistration: jest.fn().mockResolvedValue(registration),
    ready: Promise.resolve(registration),
  };
  global.window.PushManager = function PushManager() {};
  global.Notification = {
    permission,
    requestPermission: jest.fn().mockResolvedValue(requestPermissionResult),
  };

  return { registration, subscription, pushManager };
};

beforeEach(() => {
  jest.resetAllMocks();
});

afterEach(() => {
  delete global.navigator.serviceWorker;
  delete global.window.PushManager;
  delete global.Notification;
});

describe('PushService.isSupported', () => {
  test('returns true when SW + PushManager + Notification all exist', () => {
    installBrowserStubs();
    expect(pushService.isSupported()).toBe(true);
  });

  test('returns false when any capability is missing', () => {
    installBrowserStubs({ supported: false });
    expect(pushService.isSupported()).toBe(false);
  });
});

describe('PushService.getStatus', () => {
  test('returns "unsupported" on browsers without the APIs', async () => {
    installBrowserStubs({ supported: false });
    expect(await pushService.getStatus()).toBe('unsupported');
  });

  test('returns "denied" when notification permission was blocked', async () => {
    installBrowserStubs({ permission: 'denied' });
    expect(await pushService.getStatus()).toBe('denied');
  });

  test('returns "subscribed" when a PushSubscription already exists', async () => {
    installBrowserStubs({
      existingSubscription: { endpoint: 'https://push.example/x' },
    });
    expect(await pushService.getStatus()).toBe('subscribed');
  });

  test('returns "idle" when supported but no subscription yet', async () => {
    installBrowserStubs();
    expect(await pushService.getStatus()).toBe('idle');
  });
});

describe('PushService.subscribe', () => {
  test('returns error on unsupported browser', async () => {
    installBrowserStubs({ supported: false });
    const res = await pushService.subscribe();
    expect(res.success).toBe(false);
    expect(res.error.message).toMatch(/không hỗ trợ|not supported/i);
  });

  test('returns error when the user denies permission', async () => {
    installBrowserStubs({ requestPermissionResult: 'denied' });
    httpClient.get.mockResolvedValue(ok({ public_key: 'BNc' }));

    const res = await pushService.subscribe();
    expect(res.success).toBe(false);
    expect(res.error.message).toMatch(/cho phép|permission/i);
  });

  test('returns error when backend has no VAPID key configured', async () => {
    installBrowserStubs();
    httpClient.get.mockResolvedValue(fail('not configured'));

    const res = await pushService.subscribe();
    expect(res.success).toBe(false);
    expect(res.error.message).toMatch(/VAPID|not configured/i);
  });

  test('happy path: registers SW, subscribes, POSTs subscription', async () => {
    const { registration, subscription, pushManager } = installBrowserStubs();
    // Real base64url-ish string (just used as raw bytes by urlBase64ToUint8Array).
    httpClient.get.mockResolvedValue(ok({ public_key: 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0' }));
    httpClient.post.mockResolvedValue(ok({ id: 11 }));

    const res = await pushService.subscribe();
    expect(res.success).toBe(true);
    expect(navigator.serviceWorker.register).toHaveBeenCalled();
    expect(pushManager.subscribe).toHaveBeenCalledWith(
      expect.objectContaining({ userVisibleOnly: true })
    );
    expect(httpClient.post).toHaveBeenCalledWith(
      expect.stringContaining('/push/subscribe'),
      expect.objectContaining({
        endpoint: 'https://push.example/abc',
        keys: { p256dh: 'p', auth: 'a' },
      })
    );
    // Avoid unused-variable lint
    expect(registration).toBeTruthy();
    expect(subscription).toBeTruthy();
  });

  test('rolls back browser subscription if backend POST fails', async () => {
    const { subscription } = installBrowserStubs();
    httpClient.get.mockResolvedValue(ok({ public_key: 'BNcRdreA' }));
    httpClient.post.mockResolvedValue(fail('server down'));

    const res = await pushService.subscribe();
    expect(res.success).toBe(false);
    // Local subscription torn down so getStatus() doesn't lie.
    expect(subscription.unsubscribe).toHaveBeenCalled();
  });
});

describe('PushService.unsubscribe', () => {
  test('noop when there is no existing subscription', async () => {
    installBrowserStubs({ existingSubscription: null });
    const res = await pushService.unsubscribe();
    expect(res.success).toBe(true);
    expect(httpClient.delete).not.toHaveBeenCalled();
  });

  test('unsubscribes locally + DELETEs on the backend', async () => {
    const sub = {
      endpoint: 'https://push.example/known',
      unsubscribe: jest.fn().mockResolvedValue(true),
    };
    installBrowserStubs({ existingSubscription: sub });
    httpClient.delete.mockResolvedValue(ok({}));

    const res = await pushService.unsubscribe();
    expect(res.success).toBe(true);
    expect(sub.unsubscribe).toHaveBeenCalled();
    expect(httpClient.delete).toHaveBeenCalledWith(
      expect.stringContaining(encodeURIComponent('https://push.example/known'))
    );
  });

  test('returns success even on unsupported browser', async () => {
    installBrowserStubs({ supported: false });
    const res = await pushService.unsubscribe();
    expect(res.success).toBe(true);
  });
});
