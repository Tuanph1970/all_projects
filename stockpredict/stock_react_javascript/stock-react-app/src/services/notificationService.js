// Notification Service - thin wrapper around the portfolio-service
// notifications API. Mirrors the singleton pattern used by the other
// services in src/services/.
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class NotificationService {
  /**
   * List notifications for the current user.
   * @param {Object} opts
   * @param {boolean} [opts.unreadOnly=false]
   * @param {number} [opts.limit=50]
   * @param {number} [opts.offset=0]
   * @returns {Promise<{success:boolean, data?:{items:Array, total:number, unread:number}, error?:any}>}
   */
  async list({ unreadOnly = false, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (unreadOnly) params.append('unread_only', 'true');
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    const url = `${API_ENDPOINTS.NOTIFICATIONS_LIST}?${params.toString()}`;
    return httpClient.get(url);
  }

  /** Mark a single notification as read. Idempotent. */
  async markRead(id) {
    return httpClient.post(API_ENDPOINTS.NOTIFICATION_MARK_READ(id));
  }

  /** Mark every unread notification for the current user. */
  async markAllRead() {
    return httpClient.post(API_ENDPOINTS.NOTIFICATIONS_READ_ALL);
  }

  /** Delete a notification. */
  async remove(id) {
    return httpClient.delete(API_ENDPOINTS.NOTIFICATION_DELETE(id));
  }
}

const notificationServiceInstance = new NotificationService();
export default notificationServiceInstance;
