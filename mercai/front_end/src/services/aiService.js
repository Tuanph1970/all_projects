import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

/**
 * Client for the AI service (ai-service, /api/v1/ai).
 *
 * This service only ever *proposes*. Applying a suggestion goes through the
 * normal product endpoints, so the backend keeps its validation, ownership
 * checks and price ledger. Nothing here writes to the catalogue.
 */
class AiService {
  /**
   * Ask for listing improvements.
   *
   * Pass `{ productId }` for a saved listing, or `{ draft }` for one still
   * being typed on the create form. Exactly one of the two.
   */
  async suggestListing({ productId = null, draft = null, fields = null } = {}) {
    const payload = {};
    if (productId != null) payload.product_id = productId;
    if (draft) payload.draft = draft;
    if (fields) payload.fields = fields;

    return await apiClient.post(API_CONFIG.ENDPOINTS.AI_LISTING_SUGGEST, payload);
  }

  /**
   * Record what the seller did with a suggestion.
   *
   * This is how the feature's value is measured, so it is worth calling even
   * when the seller rejects everything -- but never at the cost of blocking
   * them, hence the swallowed error.
   */
  async resolveSuggestion(suggestionId, status, acceptedFields = null) {
    try {
      return await apiClient.post(
        `${API_CONFIG.ENDPOINTS.AI_LISTING_SUGGESTIONS}/${suggestionId}/resolve`,
        { status, accepted_fields: acceptedFields },
      );
    } catch (error) {
      console.log('Could not record suggestion outcome:', error?.message);
      return null;
    }
  }

  /**
   * Whether AI features are usable right now.
   *
   * Used to hide AI affordances entirely when the model is unreachable --
   * better than showing a button that fails when tapped. Never throws.
   */
  async getAvailability() {
    try {
      const response = await apiClient.get(`${API_CONFIG.ENDPOINTS.AI}/health`);
      const data = response?.data || response || {};
      return {
        available: data.status === 'healthy',
        features: data.features || {},
        model: data.model || null,
      };
    } catch (error) {
      return { available: false, features: {}, model: null };
    }
  }

  /** Convenience: is the listing optimizer usable? */
  async isListingOptimizerAvailable() {
    const { features } = await this.getAvailability();
    return Boolean(features.listing_optimizer);
  }
}

export const aiService = new AiService();
export default aiService;
