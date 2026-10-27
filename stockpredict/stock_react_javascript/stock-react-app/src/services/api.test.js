import { formatApiError, stockAPI } from './api';

describe('formatApiError', () => {
  it('returns a string detail as-is', () => {
    expect(formatApiError({ detail: 'Invalid username/email or password' }, 'x'))
      .toBe('Invalid username/email or password');
  });

  it('flattens FastAPI 422 validation lists', () => {
    const body = {
      detail: [
        { type: 'missing', loc: ['body', 'email'], msg: 'Field required' },
        { type: 'missing', loc: ['body', 'password'], msg: 'Field required' },
      ],
    };
    expect(formatApiError(body, 'x')).toBe('email: Field required; password: Field required');
  });

  it('falls back to message, then the fallback', () => {
    expect(formatApiError({ message: 'Boom' }, 'x')).toBe('Boom');
    expect(formatApiError(null, 'Invalid credentials')).toBe('Invalid credentials');
    expect(formatApiError({ detail: [] }, 'Invalid credentials')).toBe('Invalid credentials');
  });
});

describe('stockAPI.removeStock — DELETE returns 204 No Content', () => {
  const PORTFOLIO = { id: 7 };

  /** A 204 as fetch actually delivers it: ok, no body, and .json() throws. */
  const noContent = () => ({
    ok: true,
    status: 204,
    json: () => Promise.reject(new SyntaxError('Unexpected end of JSON input')),
    text: () => Promise.resolve(''),
  });

  const okJson = (body) => ({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });

  beforeEach(() => {
    localStorage.setItem('token', 'test-token');
  });

  afterEach(() => {
    localStorage.removeItem('token');
    delete global.fetch;
  });

  it('resolves instead of throwing when the server sends 204', async () => {
    // The reported bug: the holding IS deleted server-side, but the UI shows
    // "Failed to remove stock" and the row only disappears after a refresh.
    // The cause was an unconditional `await response.json()` on an empty body.
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))   // GET /portfolios/default
      .mockResolvedValueOnce(noContent());        // DELETE /holdings/VNM

    await expect(stockAPI.removeStock('VNM')).resolves.toEqual({ success: true });

    const [, deleteCall] = global.fetch.mock.calls;
    expect(deleteCall[0]).toContain('/portfolios/7/holdings/VNM');
    expect(deleteCall[1].method).toBe('DELETE');
  });

  it('does not call .json() on the delete response at all', async () => {
    // Stronger than the test above: even a 204 whose .json() resolves must not
    // be parsed, so the fix cannot regress into "parse, but swallow the error".
    const del = { ok: true, status: 204, json: jest.fn(), text: jest.fn() };
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce(del);

    await stockAPI.removeStock('VNM');
    expect(del.json).not.toHaveBeenCalled();
  });

  it('surfaces the server detail when the holding is not found', async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Holding not found' })),
      });

    await expect(stockAPI.removeStock('VNM')).rejects.toThrow('Holding not found');
  });

  it('still reports a failure when the error body is empty or not JSON', async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce({
        ok: false, status: 502, text: () => Promise.resolve('<html>bad gateway</html>'),
      });

    await expect(stockAPI.removeStock('VNM')).rejects.toThrow(/bad gateway|Failed to remove stock/);
  });
});

describe('portfolio add paths send the field names the API declares', () => {
  const PORTFOLIO = { id: 7 };
  const okJson = (body, status = 200) => ({
    ok: true,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  });

  beforeEach(() => { localStorage.setItem('token', 'test-token'); });
  afterEach(() => { localStorage.removeItem('token'); delete global.fetch; });

  const bodyOf = (call) => JSON.parse(call[1].body);

  it('buyStock — the path the Holdings screen actually uses — posts quantity', async () => {
    // portfolioService.addStock() calls buyStock(), NOT stockAPI.addStock().
    // This is the live path: a BUY transaction, where TransactionCreate
    // requires `quantity` (gt=0). Verified end-to-end against the running
    // service: quantity 100 at 60.5 produced total_cost 6050.
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce(okJson({ id: 1, quantity: 100 }, 201));

    await stockAPI.buyStock('VNM', 'Vinamilk', 100, 60.5);

    const body = bodyOf(global.fetch.mock.calls[1]);
    expect(body).toMatchObject({ symbol: 'VNM', type: 'buy', quantity: 100, price: 60.5 });
    expect(body.shares).toBeUndefined();
  });

  it('sellStock posts quantity too', async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce(okJson({ id: 2 }, 201));

    await stockAPI.sellStock('VNM', 40, 61.0);

    const body = bodyOf(global.fetch.mock.calls[1]);
    expect(body).toMatchObject({ symbol: 'VNM', type: 'sell', quantity: 40 });
    expect(body.shares).toBeUndefined();
  });

  it('addStock posts quantity, not shares (latent: currently unreferenced)', async () => {
    // HoldingCreate declares `quantity: int = Field(default=0, ge=0)` and
    // pydantic drops unknown keys, so posting `shares` stored ZERO shares and
    // a zero cost basis. Nothing calls this today — the test exists so that
    // wiring it up later cannot silently reintroduce that.
    global.fetch = jest.fn()
      .mockResolvedValueOnce(okJson(PORTFOLIO))
      .mockResolvedValueOnce(okJson({ id: 3, quantity: 100 }, 201));

    await stockAPI.addStock('VNM', 'Vinamilk', 100, 60.5);

    const body = bodyOf(global.fetch.mock.calls[1]);
    expect(body.quantity).toBe(100);
    expect(body.shares).toBeUndefined();
  });
});
