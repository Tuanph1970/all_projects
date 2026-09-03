/**
 * API E2E Tests for the Intel Service (price intelligence)
 * Runs against the live mercai-intel-service.
 *
 *   API_BASE_URL=https://mercai.tuan1970.com npm run test:api
 *
 * NOTE (2026-09-03): intel-service is NOT deployed on the machine now serving
 * that hostname -- /api/v1/intel/health 404s there, while it answers 200 on a
 * local stack. Until intel is brought up on that machine these tests only
 * mean anything against localhost:8002.
 *
 * Depends on the seeded catalogue from
 * back_end/scripts/seed_catalogue.py -- the seller logins and the SEED-* SKUs
 * below come from there. On an unseeded database these skip rather than fail,
 * because "no data" is not the same as "broken".
 */

const axios = require('axios');

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8002';
const API_TIMEOUT = 30000;

const SELLER = { username: 'gomthuha', password: 'MercaiTest@2026' };
const RIVAL = { username: 'gomviet', password: 'MercaiTest@2026' };

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
  validateStatus: () => true,
});

const authed = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

/** Make a skip visible in the output rather than a green that asserts nothing. */
const pending = (reason) => {
  console.warn(`  ⏭  skipped: ${reason}`);
};

let sellerToken = null;
let rivalToken = null;
let sellerUserId = null;
let productId = null;
let featureOn = false;
// Why the fixtures are unusable, if they are. Kept so the reason surfaces in
// the report instead of eight tests quietly passing in 0ms.
let skipReason = null;

async function login({ username, password }) {
  const res = await api.post('/api/v1/auth/login', { username, password });
  return res.status === 200 ? res.data.access_token : null;
}

describe('Intel Service API E2E Tests', () => {
  beforeAll(async () => {
    const health = await api.get('/api/v1/intel/health');
    expect(health.status).toBe(200);
    featureOn = Boolean(health.data?.features?.price_intel);
    console.log(`ℹ️  intel-service reachable at ${API_BASE_URL}, ` +
                `price_intel=${featureOn}`);

    sellerToken = await login(SELLER);
    rivalToken = await login(RIVAL);
    if (!sellerToken) {
      skipReason = `seeded seller "${SELLER.username}" cannot log in — ` +
                   'run back_end/scripts/seed_catalogue.py';
      return;
    }

    const me = await api.get('/api/v1/auth/me', authed(sellerToken));
    sellerUserId = me.data?.id ?? null;

    // There is no seller-scoped product list endpoint (/api/v1/seller/products
    // 404s), so find one this seller owns in the public catalogue.
    const products = await api.get('/api/v1/products/?limit=100');
    const list = Array.isArray(products.data)
      ? products.data
      : products.data?.items || products.data?.products || [];
    const mine = list.find((p) => p.seller_id === sellerUserId);
    productId = mine ? mine.id : null;

    if (!productId) skipReason = `no product owned by ${SELLER.username} in the catalogue`;
    else if (!featureOn) skipReason = 'price_intel is switched off on this deployment';
  });

  // Runs first and states the preconditions out loud. Without it, a missing
  // seed or a disabled flag turns every guarded test below into a silent pass
  // -- fifteen greens that assert nothing, which is worse than a red.
  describe('Preconditions', () => {
    it('has the seeded fixtures and the feature enabled', () => {
      if (skipReason) {
        throw new Error(
          `Intel API tests cannot run meaningfully: ${skipReason}. ` +
          'Everything below this point is skipped, not passing.');
      }
      expect(productId).toBeGreaterThan(0);
      expect(featureOn).toBe(true);
    });
  });

  describe('GET /api/v1/intel/health', () => {
    it('reports the service and its feature flags', async () => {
      const res = await api.get('/api/v1/intel/health');
      expect(res.status).toBe(200);
      expect(res.data).toHaveProperty('service', 'intel-service');
      expect(res.data).toHaveProperty('database', 'connected');
      expect(res.data.features).toHaveProperty('price_intel');
    });

    it('no longer advertises a model', async () => {
      // Ollama was removed on 2026-08-27. A lingering `ollama` or `model` key
      // would mean an old build is deployed.
      const res = await api.get('/api/v1/intel/health');
      expect(res.data).not.toHaveProperty('ollama');
      expect(res.data).not.toHaveProperty('model');
    });

    it('does not expose the retired listing-optimizer route', async () => {
      const res = await api.get('/api/v1/ai/health');
      expect(res.status).toBe(404);
    });
  });

  describe('GET /products/{id}/price-position', () => {
    it('requires authentication', async () => {
      const res = await api.get('/api/v1/intel/products/1/price-position');
      expect([401, 403]).toContain(res.status);
    });

    it('returns a coherent position for the seller', async () => {
      if (skipReason) return pending(skipReason);
      const res = await api.get(
        `/api/v1/intel/products/${productId}/price-position`, authed(sellerToken));
      expect(res.status).toBe(200);

      const body = res.data;
      expect(body).toHaveProperty('own_price');
      expect(body).toHaveProperty('basis');
      expect(['own_category', 'parent_category', 'none']).toContain(body.basis);
      expect(body).toHaveProperty('min_comparable_n');

      if (body.basis !== 'none') {
        // Quartiles must be ordered, or the scale on the screen is nonsense.
        expect(body.p25).toBeLessThanOrEqual(body.median);
        expect(body.median).toBeLessThanOrEqual(body.p75);
        expect(body.comparable_count).toBeGreaterThanOrEqual(body.min_comparable_n);
        expect(['below_market', 'in_range', 'above_market']).toContain(body.position);
      }
    });

    it('never reveals which seller a comparable belongs to', async () => {
      // A market summary, not a ranked list of who to undercut.
      if (skipReason) return pending(skipReason);
      const res = await api.get(
        `/api/v1/intel/products/${productId}/price-position`, authed(sellerToken));
      for (const row of res.data.comparables || []) {
        expect(Object.keys(row).sort())
          .toEqual(['name', 'price', 'product_id', 'source']);
      }
      expect(JSON.stringify(res.data)).not.toContain('seller_id');
    });

    it('refuses another seller asking about this product', async () => {
      if (skipReason || !rivalToken) return pending(skipReason || 'rival seller missing');
      const res = await api.get(
        `/api/v1/intel/products/${productId}/price-position`, authed(rivalToken));
      expect(res.status).toBe(403);
    });

    it('404s for a product that does not exist', async () => {
      if (skipReason) return pending(skipReason);
      const res = await api.get(
        '/api/v1/intel/products/99999999/price-position', authed(sellerToken));
      expect(res.status).toBe(404);
    });
  });

  describe('POST /api/v1/intel/comparables - the SSRF surface', () => {
    // Sellers supply these URLs. Each case below is a way an unguarded fetcher
    // gets used to read the internal network and hand it back.
    const payloads = [
      ['cloud metadata', 'http://169.254.169.254/latest/meta-data/'],
      ['internal service', 'http://db:3306/'],
      ['loopback', 'http://127.0.0.1:8080/dashboard/'],
      ['file scheme', 'file:///etc/passwd'],
      ['unsupported host', 'https://shopee.vn/product/1/2'],
    ];

    it.each(payloads)('refuses %s', async (_label, url) => {
      if (skipReason) return pending(skipReason);
      const res = await api.post('/api/v1/intel/comparables',
        { product_id: productId, url }, authed(sellerToken));
      expect(res.status).toBe(422);
      // And says something the seller can act on, not a stack trace.
      expect(typeof res.data.detail).toBe('string');
      expect(res.data.detail.length).toBeGreaterThan(10);
    });

    it('lists the hosts it can actually read', async () => {
      if (skipReason) return pending(skipReason);
      const res = await api.get(
        `/api/v1/intel/comparables?product_id=${productId}`, authed(sellerToken));
      expect(res.status).toBe(200);
      expect(Array.isArray(res.data.supported_hosts)).toBe(true);
      expect(res.data.supported_hosts.length).toBeGreaterThan(0);
    });
  });

  describe('Gateway hygiene', () => {
    it('does not expose the Traefik dashboard', async () => {
      for (const path of ['/dashboard/', '/api/rawdata', '/api/overview']) {
        const res = await api.get(path);
        expect(res.status).toBe(404);
      }
    });
  });
});
