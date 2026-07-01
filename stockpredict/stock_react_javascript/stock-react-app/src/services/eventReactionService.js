// Event-Reaction Service API client
// Measures how asset prices react to the SURPRISE of discrete events.
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class EventReactionService {
  // Measure one event's reaction: surprise + market-model abnormal returns + jump test.
  async measure({ symbol, market_symbol, event, method = 'consensus', jump_n_null = 0 }) {
    return httpClient.post(API_ENDPOINTS.EVENT_REACTION_MEASURE, {
      symbol,
      market_symbol,
      event,
      method,
      jump_n_null,
    });
  }

  // Cross-sectional exposure: regress CAR on surprise across events (clustering-robust).
  async crossSection({ rows, cluster = 'event_date' }) {
    return httpClient.post(API_ENDPOINTS.EVENT_REACTION_CROSS_SECTION, { rows, cluster });
  }

  // Persist events into the event store.
  async ingestEvents({ events }) {
    return httpClient.post(API_ENDPOINTS.EVENT_REACTION_EVENTS, { events });
  }

  async listEvents({ kind } = {}) {
    const query = kind ? `?kind=${encodeURIComponent(kind)}` : '';
    return httpClient.get(`${API_ENDPOINTS.EVENT_REACTION_EVENTS}${query}`);
  }
}

const eventReactionService = new EventReactionService();
export default eventReactionService;
