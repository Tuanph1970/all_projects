import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

/**
 * Client for the intel service (intel-service, /api/v1/intel).
 *
 * Read-only. Nothing here writes to the catalogue -- a seller who decides to
 * change a price does it through the normal product endpoints, so validation,
 * ownership checks and the price ledger all stay on the usual path.
 */
class IntelService {
  /**
   * Where this listing sits against comparable listings.
   *
   * `basis` says which fallback rung produced the numbers and matters for the
   * copy: 'own_category' is the seller's real market, 'parent_category' is a
   * deliberately broader benchmark, and 'none' means there was not enough to
   * compare against -- a normal state for a one-off piece, not an error.
   */
  async getPricePosition(productId) {
    return await apiClient.get(
      `${API_CONFIG.ENDPOINTS.INTEL}/products/${productId}/price-position`,
      { timeout: API_CONFIG.INTEL_TIMEOUT },
    );
  }

  /** Measured photo problems. Every finding is a measurement, not an opinion. */
  async getImageReport(productId) {
    return await apiClient.get(
      `${API_CONFIG.ENDPOINTS.INTEL}/products/${productId}/image-report`,
    );
  }

  /**
   * Whether intel features are usable right now.
   *
   * Used to hide the affordance rather than show a control that 404s. Never
   * throws.
   */
  async isPriceIntelAvailable() {
    try {
      const response = await apiClient.get(`${API_CONFIG.ENDPOINTS.INTEL}/health`);
      const data = response?.data || response || {};
      return Boolean(data.features?.price_intel);
    } catch (error) {
      return false;
    }
  }
}

export const intelService = new IntelService();
export default intelService;
