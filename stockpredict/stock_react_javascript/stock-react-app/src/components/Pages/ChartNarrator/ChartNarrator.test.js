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
const SECTIONS = ['data', 'trend', 'levels', 'indicators', 'patterns', 'channel', 'strategy'];
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
