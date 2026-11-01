/**
 * PriceBoard — the VN30 board's layout and colour rules.
 *
 * Written before react-table was removed from this page (Tech Debt: two table
 * libraries shipped), and run green against the react-table version first, so
 * what it pins is the board as users already see it:
 *
 *   * a two-row header: Bid / Matched / Ask spanning their price/qty columns;
 *   * one cell per leaf column, in order;
 *   * a price is coloured by where it sits against ceiling / reference / floor,
 *     and its quantity takes the price's colour;
 *   * a missing value reads N/A rather than blank;
 *   * clicking a symbol opens its company page.
 *
 * Asserts real copy through the shared i18n instance (see TcbNews.test.js, #71).
 */
import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import PriceBoard from './PriceBoard';
import httpClient from '../../services/httpClient';
import i18n from '../../i18n';

jest.mock('../../services/httpClient');

const ROW = {
  symbol: 'ACB',
  ceiling: 26.75,
  floor: 23.25,
  refPrice: 25.0,
  buyPrice3: 24.9, buyQty3: 300,
  buyPrice2: 24.95, buyQty2: 200,
  buyPrice1: 25.0, buyQty1: 100,
  matchPrice: 26.75, matchQty: 50,
  change: 1.75, changePercent: 7.0,
  sellPrice1: 23.25, sellQty1: 10,
  sellPrice2: 25.5, sellQty2: 20,
  sellPrice3: null, sellQty3: 30,
  totalQty: 1234,
  openPrice: 25.1, highest: 26.75, lowest: 24.8,
};

const LEAF_COUNT = 24; // 4 + 6 bid + 4 matched + 6 ask + 4

async function renderBoard(rows = [ROW]) {
  httpClient.get.mockResolvedValue({ success: true, data: rows });
  const utils = render(
    <MemoryRouter initialEntries={['/priceboard']}>
      <Routes>
        <Route path="/priceboard" element={<PriceBoard />} />
        <Route path="/company/:symbol" element={<div>company page</div>} />
      </Routes>
    </MemoryRouter>
  );
  await screen.findByText('ACB');
  return utils;
}

const colourOf = (el) => el.closest('span')?.style.color;

beforeAll(() => i18n.changeLanguage('en'));
afterEach(() => jest.clearAllMocks());

test('header is two rows with the three groups spanning their columns', async () => {
  const { container } = await renderBoard();
  const headerRows = container.querySelectorAll('thead tr');
  expect(headerRows).toHaveLength(2);

  const span = (text) => {
    const th = within(headerRows[0]).getByText(text).closest('th');
    return Number(th.getAttribute('colspan') || 1);
  };
  expect(span('Bid')).toBe(6);
  expect(span('Matched')).toBe(4);
  expect(span('Ask')).toBe(6);

  // Every leaf column has exactly one header cell somewhere.
  const leafHeaders = Array.from(headerRows[1].children);
  const total = Array.from(headerRows[0].children)
    .reduce((n, th) => n + Number(th.getAttribute('colspan') || 1), 0);
  expect(total).toBe(LEAF_COUNT);
  expect(leafHeaders.length).toBe(LEAF_COUNT);
});

test('each row has one cell per leaf column, in order', async () => {
  const { container } = await renderBoard();
  const cells = container.querySelectorAll('tbody tr:first-child td');
  expect(cells).toHaveLength(LEAF_COUNT);
  expect(cells[0]).toHaveTextContent('ACB');
  expect(cells[10]).toHaveTextContent('26.75'); // matchPrice
  expect(cells[20]).toHaveTextContent('1234');  // totalQty
});

test('prices are coloured by ceiling, reference and floor; qty follows its price', async () => {
  const { container } = await renderBoard();
  const cells = container.querySelectorAll('tbody tr:first-child td');
  expect(colourOf(within(cells[10]).getByText('26.75'))).toBe('magenta'); // match = ceiling
  expect(colourOf(within(cells[11]).getByText('50'))).toBe('magenta');    // its qty
  expect(colourOf(within(cells[8]).getByText('25'))).toBe('yellow');      // bid1 = reference
  expect(colourOf(within(cells[14]).getByText('23.25'))).toBe('rgb(0, 255, 0)'); // ask1 = floor
  expect(colourOf(within(cells[16]).getByText('25.5'))).toBe('rgb(0, 191, 255)'); // ref < p < ceiling
  expect(colourOf(within(cells[4]).getByText('24.9'))).toBe('red');       // floor < p < ref
});

test('a missing price reads N/A', async () => {
  const { container } = await renderBoard();
  const cells = container.querySelectorAll('tbody tr:first-child td');
  expect(cells[18]).toHaveTextContent('N/A'); // sellPrice3 = null
});

test('clicking a symbol opens its company page', async () => {
  await renderBoard();
  fireEvent.click(screen.getByText('ACB'));
  expect(await screen.findByText('company page')).toBeInTheDocument();
});

test('clicking any other cell does not navigate', async () => {
  const { container } = await renderBoard();
  fireEvent.click(container.querySelectorAll('tbody tr:first-child td')[10]);
  expect(screen.queryByText('company page')).not.toBeInTheDocument();
});
