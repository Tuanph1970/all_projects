/**
 * Backlog #118 — the chart narrator screen.
 *
 * The test that matters most here is the i18n one. This page renders EVERY
 * sentence through `t(code, params)`, so a key with no translation does not
 * throw and does not look broken in development — i18next falls back to
 * echoing the key, and a reviewer skimming the page sees a dotted string that
 * is easy to mistake for a label. Earlier in this feature I shipped the whole
 * `divergence` section with no strings at all, in either locale, and only a
 * test like this caught it.
 */
import fs from 'fs';
import path from 'path';

const en = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../../../i18n/locales/en.json'), 'utf8'));
const vi = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../../../i18n/locales/vi.json'), 'utf8'));
const source = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');

const flatten = (obj, prefix = '') =>
  Object.entries(obj).reduce((acc, [k, v]) => {
    const key = `${prefix}${k}`;
    return typeof v === 'object' && v !== null
      ? { ...acc, ...flatten(v, `${key}.`) }
      : { ...acc, [key]: v };
  }, {});

const flatEn = flatten(en);
const flatVi = flatten(vi);

/** Literal t('...') keys used by the component. */
const literalKeys = [...source.matchAll(/\bt\(\s*'([^']+)'/g)].map((m) => m[1]);

/** Template t(`narrative.section.${...}`) keys, expanded from the known lists. */
const SECTIONS = ['data', 'trend', 'levels', 'indicators', 'patterns', 'chart_patterns', 'channel', 'strategy'];
const LEVEL_KINDS = ['support', 'resistance'];

describe('ChartNarrator i18n coverage', () => {
  it('uses at least a dozen translated strings (guards the guard)', () => {
    // If the extraction regex ever stops matching, every assertion below
    // becomes vacuously true. This is the canary for that.
    expect(literalKeys.length).toBeGreaterThan(12);
  });

  it.each([['en', flatEn], ['vi', flatVi]])(
    'every literal key the component renders exists in %s', (_lang, flat) => {
      const missing = literalKeys.filter((k) => !(k in flat));
      expect(missing).toEqual([]);
    });

  it.each([['en', flatEn], ['vi', flatVi]])(
    'every section heading resolves in %s', (_lang, flat) => {
      const missing = SECTIONS.filter((s) => !(`narrative.section.${s}` in flat));
      expect(missing).toEqual([]);
    });

  it.each([['en', flatEn], ['vi', flatVi]])(
    'both level labels resolve in %s', (_lang, flat) => {
      const missing = LEVEL_KINDS.filter((k) => !(`narrative.ui.level_${k}` in flat));
      expect(missing).toEqual([]);
    });

  it('the two locales carry the same narrative keys', () => {
    const narrEn = Object.keys(flatEn).filter((k) => k.startsWith('narrative.'));
    const narrVi = Object.keys(flatVi).filter((k) => k.startsWith('narrative.'));
    expect(narrEn.sort()).toEqual(narrVi.sort());
  });

  it('every {{placeholder}} in a narrative string appears in both locales', () => {
    // A Vietnamese sentence that drops {{price}} renders without the number
    // and reads as a complete sentence — the worst kind of wrong.
    const ph = (s) => [...String(s).matchAll(/{{(\w+)}}/g)].map((m) => m[1]).sort();
    const mismatched = Object.keys(flatEn)
      .filter((k) => k.startsWith('narrative.') && k in flatVi)
      .filter((k) => JSON.stringify(ph(flatEn[k])) !== JSON.stringify(ph(flatVi[k])));
    expect(mismatched).toEqual([]);
  });

  it('the Vietnamese narrative strings are not just the English copied', () => {
    const keys = Object.keys(flatEn).filter(
      (k) => k.startsWith('narrative.') && k in flatVi);
    const identical = keys.filter((k) => flatEn[k] === flatVi[k]);
    // A handful of proper nouns and short labels legitimately match (MA20,
    // Doji). A majority matching would mean the file was never translated.
    expect(identical.length).toBeLessThan(keys.length / 4);
  });
});

describe('ChartNarrator wiring', () => {
  it('reads the WATCHED list, not the watchlist-plus-portfolio union', () => {
    // The owner drew this line twice: "portfolio is the bought symbols" and
    // "watch is only watch not buy". useUserTickers unions the two, so using
    // it here would put a bought symbol in a list labelled "watched".
    expect(source).toMatch(/useWatchedTickers/);
    expect(source).not.toMatch(/useUserTickers/);
  });

  it('sends both dates to the backend rather than filtering locally', () => {
    // Filtering client-side would leave the indicators computed on bars after
    // end_date — a reading of March that knows how April turned out.
    expect(source).toMatch(/startDate:\s*startDate/);
    expect(source).toMatch(/endDate:\s*endDate/);
  });

  it('refuses an inverted range instead of silently reordering it', () => {
    expect(source).toMatch(/datesInverted/);
    expect(source).toMatch(/startDate\s*>\s*endDate/);
  });

  it('draws its reference lines from the same levels the text names', () => {
    expect(source).toMatch(/ReferenceLine/);
    expect(source).toMatch(/levels/);
  });
});

describe('ChartNarrator default date range', () => {
  // eslint-disable-next-line global-require
  const { defaultRange } = require('./index');

  it('ends on the session it is given, not on today', () => {
    // `today` is wrong on a weekend, a holiday, and before the close. A user
    // who sees "To: Saturday" reasonably concludes there is Saturday data.
    expect(defaultRange('2026-11-03').endDate).toBe('2026-11-03');
  });

  it('starts far enough back to cover MA200 in CALENDAR days, not bar counts', () => {
    // THE ARITHMETIC THIS EXISTS TO PROTECT. The longest average is MA200 =
    // 200 BARS. The VN market trades about five days in seven, so 200 bars is
    // roughly 320 calendar days. Subtracting 200 DAYS would yield only ~140
    // bars and quietly cut a quarter off the intended window.
    const { startDate, endDate } = defaultRange('2026-11-03');
    const days = (new Date(`${endDate}T00:00:00`) - new Date(`${startDate}T00:00:00`))
      / 86400000;
    expect(days).toBe(320);
    expect(days).toBeGreaterThan(200);   // the mistake, stated as a guard
  });

  it('falls back to a valid range when no session date is known', () => {
    for (const bad of [null, undefined, '', 'not-a-date', '2026-13-99', '20261103']) {
      const r = defaultRange(bad);
      expect(r.endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(r.startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(r.startDate < r.endDate).toBe(true);
    }
  });

  it('never produces an inverted range', () => {
    const r = defaultRange('2026-01-01');
    expect(r.startDate < r.endDate).toBe(true);
    expect(r.startDate).toBe('2025-02-15');   // 320 days before, across a year
  });

  it('prefills from the newest session rather than from today', () => {
    const src = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
    expect(src).toMatch(/getLatestSessionDate/);
    expect(src).toMatch(/applyDefaults/);
  });

  it('offers a way back to the defaults after the user edits them', () => {
    // Without this, a user who clears a date cannot recover the computed range.
    const src = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
    expect(src).toMatch(/narrative\.ui\.reset_dates/);
    expect(src).toMatch(/onClick=\{applyDefaults\}/);
  });

  it('does not let Analysis fire before the dates are populated', () => {
    const src = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
    expect(src).toMatch(/!datesReady/);
  });

  it('the date hint no longer tells users to leave the fields empty', () => {
    // The old string said "Leave the dates empty for the last 180 sessions",
    // which became misleading the moment the fields were prefilled.
    for (const flat of [flatten(en), flatten(vi)]) {
      expect(flat['narrative.ui.date_hint']).toBeTruthy();
      expect(flat['narrative.ui.date_hint']).not.toMatch(/empty|trống/i);
      expect(flat['narrative.ui.reset_dates']).toBeTruthy();
    }
  });
});

describe('ChartNarrator date validity', () => {
  // eslint-disable-next-line global-require
  const { defaultRange } = require('./index');

  it('rejects a shape-valid but impossible date', () => {
    // "2026-13-99" matches /^\d{4}-\d{2}-\d{2}$/ while being month 13 day 99.
    // Before the round-trip check this produced startDate "NaN-NaN-NaN", which
    // reaches an <input type="date"> as a silently blank field.
    const r = defaultRange('2026-13-99');
    expect(r.startDate).not.toMatch(/NaN/);
    expect(r.endDate).not.toBe('2026-13-99');
    expect(r.startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('rejects 30 February', () => {
    const r = defaultRange('2026-02-30');
    expect(r.endDate).not.toBe('2026-02-30');
    expect(r.startDate).not.toMatch(/NaN/);
  });

  it('accepts a real date unchanged', () => {
    // Non-vacuity: the validity check must not reject valid input, including a
    // genuine leap day.
    expect(defaultRange('2024-02-29').endDate).toBe('2024-02-29');
    expect(defaultRange('2026-11-03').endDate).toBe('2026-11-03');
  });
});
