import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NotificationBell from './NotificationBell';
import notificationService from '../../services/notificationService';
import pushService from '../../services/pushService';

jest.mock('../../services/notificationService');
jest.mock('../../services/pushService');

const ok = (data) => ({ success: true, data });
const fail = (msg = 'boom') => ({ success: false, error: { message: msg } });

const sampleItem = (id, overrides = {}) => ({
  id,
  type: 'alert.triggered',
  title: `Notif ${id}`,
  body: 'body',
  metadata: { symbol: 'FPT' },
  read: false,
  created_at: new Date(Date.now() - 3 * 60_000).toISOString(),
  read_at: null,
  ...overrides,
});

beforeEach(() => {
  jest.resetAllMocks();
  // Default to no-data; tests override per-case
  notificationService.list = jest.fn().mockResolvedValue(ok({ items: [], total: 0, unread: 0 }));
  notificationService.markRead = jest.fn().mockResolvedValue(ok({}));
  notificationService.markAllRead = jest.fn().mockResolvedValue(ok({ updated: 0 }));
  notificationService.remove = jest.fn().mockResolvedValue(ok({}));
  // Default: browser doesn't support push (toggle hidden). Push-tests
  // override per-case via mockResolvedValueOnce.
  pushService.getStatus = jest.fn().mockResolvedValue('unsupported');
  pushService.subscribe = jest.fn().mockResolvedValue(ok({}));
  pushService.unsubscribe = jest.fn().mockResolvedValue(ok({}));
});

describe('NotificationBell', () => {
  test('hides badge when there are no unread notifications', async () => {
    render(<NotificationBell />);
    await waitFor(() => expect(notificationService.list).toHaveBeenCalled());
    expect(screen.queryByTestId('notification-badge')).toBeNull();
  });

  test('shows unread count in the badge', async () => {
    notificationService.list.mockResolvedValueOnce(
      ok({ items: [sampleItem(1)], total: 1, unread: 1 })
    );
    render(<NotificationBell />);
    const badge = await screen.findByTestId('notification-badge');
    expect(badge.textContent).toBe('1');
  });

  test('caps badge at 99+ for large counts', async () => {
    notificationService.list.mockResolvedValueOnce(
      ok({ items: [], total: 999, unread: 250 })
    );
    render(<NotificationBell />);
    const badge = await screen.findByTestId('notification-badge');
    expect(badge.textContent).toBe('99+');
  });

  test('opens the dropdown on bell click and refreshes', async () => {
    notificationService.list.mockResolvedValue(
      ok({ items: [sampleItem(1)], total: 1, unread: 1 })
    );
    render(<NotificationBell />);
    await waitFor(() => expect(notificationService.list).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByLabelText('Thông báo'));
    expect(screen.getByTestId('notification-dropdown')).toBeInTheDocument();
    // Open triggers a fresh refresh.
    await waitFor(() => expect(notificationService.list).toHaveBeenCalledTimes(2));
    expect(screen.getByText('Notif 1')).toBeInTheDocument();
  });

  test('renders a news.company notification with sentiment badge, symbol and link', async () => {
    const newsItem = sampleItem(7, {
      type: 'news.company',
      title: 'Good news for FPT',
      body: 'FPT launches a new AI product',
      metadata: {
        symbol: 'FPT', sentiment: 'good', category: 'new_product',
        url: 'https://example.com/fpt-ai',
      },
    });
    notificationService.list.mockResolvedValue(ok({ items: [newsItem], total: 1, unread: 1 }));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));

    expect(await screen.findByText('Good news for FPT')).toBeInTheDocument();
    expect(screen.getByTestId('news-sentiment').textContent).toBe('Good');
    expect(screen.getByText('FPT')).toBeInTheDocument();
    const link = screen.getByTestId('news-link');
    expect(link.getAttribute('href')).toBe('https://example.com/fpt-ai');
    expect(link.getAttribute('target')).toBe('_blank');
  });

  test('bad news.company renders a Bad badge', async () => {
    const newsItem = sampleItem(8, {
      type: 'news.company', title: 'Bad news for ACB', body: 'Regulatory fine',
      metadata: { symbol: 'ACB', sentiment: 'bad', category: 'regulatory' },
    });
    notificationService.list.mockResolvedValue(ok({ items: [newsItem], total: 1, unread: 1 }));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    expect((await screen.findByTestId('news-sentiment')).textContent).toBe('Bad');
    // No url -> no read-more link.
    expect(screen.queryByTestId('news-link')).toBeNull();
  });

  test('renders empty state when there are no notifications', async () => {
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText(/Không có thông báo/i);
  });

  test('renders error message when list fails', async () => {
    notificationService.list.mockResolvedValue(fail('network down'));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText(/network down/i);
  });

  test('mark-read decrements the unread badge optimistically', async () => {
    notificationService.list.mockResolvedValue(
      ok({ items: [sampleItem(1), sampleItem(2)], total: 2, unread: 2 })
    );
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText('Notif 1');

    // Each unread item has a mark-read button; click the first.
    const markBtns = screen.getAllByLabelText('Đánh dấu đã đọc');
    fireEvent.click(markBtns[0]);

    await waitFor(() => expect(notificationService.markRead).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.getByTestId('notification-badge').textContent).toBe('1')
    );
  });

  test('mark-all-read clears the badge', async () => {
    notificationService.list.mockResolvedValue(
      ok({ items: [sampleItem(1), sampleItem(2)], total: 2, unread: 2 })
    );
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText('Notif 1');

    fireEvent.click(screen.getByText(/Đã đọc tất cả/i));
    await waitFor(() => expect(notificationService.markAllRead).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByTestId('notification-badge')).toBeNull()
    );
  });

  test('delete removes an item; unread count drops if it was unread', async () => {
    notificationService.list.mockResolvedValue(
      ok({ items: [sampleItem(1)], total: 1, unread: 1 })
    );
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText('Notif 1');

    fireEvent.click(screen.getByLabelText('Xóa thông báo'));
    await waitFor(() => expect(notificationService.remove).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.queryByText('Notif 1')).toBeNull()
    );
    expect(screen.queryByTestId('notification-badge')).toBeNull();
  });

  test('push toggle is hidden when the browser does not support push', async () => {
    pushService.getStatus.mockResolvedValueOnce('unsupported');
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByTestId('notification-dropdown');
    expect(screen.queryByTestId('push-toggle')).toBeNull();
  });

  test('push toggle subscribes when clicked from idle', async () => {
    pushService.getStatus.mockResolvedValueOnce('idle');
    pushService.subscribe.mockResolvedValueOnce(ok({}));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    const toggle = await screen.findByTestId('push-toggle');

    fireEvent.click(toggle);
    await waitFor(() => expect(pushService.subscribe).toHaveBeenCalled());
    // After success, the toggle aria-label flips to "tắt" (disable).
    await waitFor(() =>
      expect(screen.getByTestId('push-toggle').getAttribute('aria-label')).toMatch(/tắt/i)
    );
  });

  test('push toggle shows error when subscribe fails', async () => {
    pushService.getStatus.mockResolvedValueOnce('idle');
    pushService.subscribe.mockResolvedValueOnce(fail('permission denied'));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    const toggle = await screen.findByTestId('push-toggle');

    fireEvent.click(toggle);
    await waitFor(() =>
      expect(screen.getByTestId('push-error').textContent).toMatch(/permission denied/i)
    );
  });

  test('push toggle unsubscribes when clicked from subscribed', async () => {
    pushService.getStatus.mockResolvedValueOnce('subscribed');
    pushService.unsubscribe.mockResolvedValueOnce(ok({}));
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    const toggle = await screen.findByTestId('push-toggle');

    fireEvent.click(toggle);
    await waitFor(() => expect(pushService.unsubscribe).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByTestId('push-toggle').getAttribute('aria-label')).toMatch(/bật/i)
    );
  });

  test('delete on a read notification does not change the badge', async () => {
    notificationService.list.mockResolvedValue(
      ok({
        items: [sampleItem(1, { read: true, read_at: new Date().toISOString() })],
        total: 1,
        unread: 0,
      })
    );
    render(<NotificationBell />);
    fireEvent.click(screen.getByLabelText('Thông báo'));
    await screen.findByText('Notif 1');

    fireEvent.click(screen.getByLabelText('Xóa thông báo'));
    await waitFor(() => expect(notificationService.remove).toHaveBeenCalledWith(1));
    // Badge was already absent; still absent.
    expect(screen.queryByTestId('notification-badge')).toBeNull();
  });
});
