import React from 'react';
import { waitFor, act } from '@testing-library/react-native';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';
import { PricePositionScreen } from '../PricePositionScreen';
import intelService from '../../../services/intelService';

jest.mock('../../../services/intelService', () => ({
  getPricePosition: jest.fn(),
  listComparables: jest.fn(),
  addComparable: jest.fn(),
  removeComparable: jest.fn(),
  refreshComparable: jest.fn(),
}));

const navigation = { navigate: jest.fn(), goBack: jest.fn() };
const route = { params: { productId: 2 } };

const WITH_MARKET = {
  product_id: 2,
  product_name: 'Bát tô gốm Bát Tràng men rạn 20cm',
  own_price: 185000,
  currency: 'VND',
  basis: 'own_category',
  basis_label: 'Bát đĩa',
  position: 'in_range',
  comparable_count: 6,
  external_count: 1,
  min_comparable_n: 5,
  p25: 178750, median: 245000, p75: 277500, min: 120000, max: 450000,
  comparables: [
    { product_id: 4, name: 'Bát ăn cơm men xanh ngọc', price: 120000, source: 'mercai' },
    { product_id: null, name: 'Bát hâm nóng đồ ăn gốm sứ', price: 270000, source: 'external' },
  ],
  trend: [
    { at: '2026-08-01T00:00:00', price: 165000, reason: 'initial' },
    { at: '2026-08-20T00:00:00', price: 185000, reason: 'seller_update' },
  ],
  benchmark: {
    source: 'tiki',
    label: 'Bát, đĩa & bộ đồ ăn trên Tiki',
    sample_size: 120, catalogue_total: 767,
    p25: 69922, median: 218000, p75: 845625, min: 18000, max: 12900000,
    computed_at: '2026-08-27T09:00:00', stale: false,
    caveat: 'Dominated by tableware sets; not directly comparable to a single piece.',
  },
};

const NO_MARKET = {
  ...WITH_MARKET,
  basis: 'none', basis_label: null, position: null,
  comparable_count: 2, external_count: 0,
  p25: null, median: null, p75: null, min: null, max: null,
  comparables: [],
};

beforeEach(() => {
  jest.clearAllMocks();
  intelService.listComparables.mockResolvedValue({ comparables: [], supported_hosts: ['tiki.vn'] });
});

const render = async () => {
  const utils = renderWithProviders(
    <PricePositionScreen route={route} navigation={navigation} />,
  );
  await act(async () => {});
  return utils;
};

describe('PricePositionScreen', () => {
  it('renders the position and the market range', async () => {
    intelService.getPricePosition.mockResolvedValue(WITH_MARKET);
    const { getByText, getAllByText, getByTestId } = await render();

    await waitFor(() => expect(getByTestId('price-position-label')).toBeTruthy());
    expect(getByText('In range')).toBeTruthy();
    // Vietnamese grouping, not raw digits. It appears more than once -- as the
    // headline and again in the price history -- which is correct.
    expect(getAllByText('185.000₫').length).toBeGreaterThan(0);
    expect(getByText('245.000₫')).toBeTruthy();   // the median
    // External comparables are labelled as such, never blended in silently.
    expect(getByText('Bát hâm nóng đồ ăn gốm sứ')).toBeTruthy();
  });

  it('treats "no market view" as a state with content, not an error', async () => {
    // A genuine one-off has no comparable. A blank screen would teach that
    // seller the feature is broken.
    intelService.getPricePosition.mockResolvedValue(NO_MARKET);
    const { getByTestId, queryByTestId } = await render();

    await waitFor(() => expect(getByTestId('price-position-no-market')).toBeTruthy());
    expect(queryByTestId('price-position-error')).toBeNull();
    expect(getByTestId('price-position-screen')).toBeTruthy();
  });

  it('names the broader category when it fell back', async () => {
    intelService.getPricePosition.mockResolvedValue({
      ...WITH_MARKET, basis: 'parent_category', basis_label: 'Gốm sứ',
    });
    const { getByText } = await render();
    await waitFor(() =>
      expect(getByText(/the broader category/)).toBeTruthy(),
    );
  });

  it('shows a real error state when the request fails', async () => {
    intelService.getPricePosition.mockRejectedValue({ response: { status: 500 } });
    const { getByTestId } = await render();
    await waitFor(() => expect(getByTestId('price-position-error')).toBeTruthy());
  });

  it('tells the seller when the feature is not switched on for them', async () => {
    intelService.getPricePosition.mockRejectedValue({ response: { status: 404 } });
    const { getByText } = await render();
    await waitFor(() =>
      expect(getByText(/not switched on/)).toBeTruthy(),
    );
  });

  it('lists tracked comparables with the sites we can read', async () => {
    intelService.getPricePosition.mockResolvedValue(WITH_MARKET);
    intelService.listComparables.mockResolvedValue({
      supported_hosts: ['fptshop.com.vn', 'tiki.vn'],
      comparables: [{
        id: 1, product_id: 2, url: 'https://tiki.vn/x', source_host: 'tiki.vn',
        label: null, is_active: true, consecutive_failures: 0,
        last_fetched_at: '2026-08-27T08:00:00',
        latest: {
          observed_at: '2026-08-27T08:00:00', status: 'ok',
          message: 'Price read successfully.', price: 270000,
          confidence: 99, trusted: true, stale: false, is_range: false,
        },
      }],
    });
    const { getByText } = await render();
    await waitFor(() => expect(getByText('tiki.vn')).toBeTruthy());
    expect(getByText(/Sites we can read so far/)).toBeTruthy();
  });

  it('shows the wider-market benchmark with its caveat attached', async () => {
    // The benchmark p75 (845,625) is three times Mercai's (277,500). Blending
    // them would silently triple the top of the range, which is why it is a
    // separate block that says so.
    intelService.getPricePosition.mockResolvedValue(WITH_MARKET);
    const { getByText, getByTestId } = await render();

    await waitFor(() => expect(getByText('The wider market')).toBeTruthy());
    expect(getByTestId('benchmark-caveat')).toBeTruthy();
    expect(getByText(/isn’t counted in your position/)).toBeTruthy();
    expect(getByText('218.000₫')).toBeTruthy();
  });

  it('omits the benchmark block entirely when there is none', async () => {
    intelService.getPricePosition.mockResolvedValue({ ...WITH_MARKET, benchmark: null });
    const { queryByText } = await render();
    await waitFor(() => expect(queryByText('The wider market')).toBeNull());
  });

  it('marks a low-confidence reading as not counted', async () => {
    intelService.getPricePosition.mockResolvedValue(WITH_MARKET);
    intelService.listComparables.mockResolvedValue({
      supported_hosts: ['tiki.vn'],
      comparables: [{
        id: 2, product_id: 2, url: 'https://tiki.vn/y', source_host: 'tiki.vn',
        label: null, is_active: true, consecutive_failures: 0,
        last_fetched_at: '2026-08-27T08:00:00',
        latest: {
          observed_at: '2026-08-27T08:00:00', status: 'ok',
          message: 'Price read successfully.', price: 99000,
          confidence: 55, trusted: false, stale: false, is_range: false,
        },
      }],
    });
    const { getByText } = await render();
    await waitFor(() =>
      expect(getByText(/not confident enough to count/)).toBeTruthy(),
    );
  });
});
