/**
 * v0.9 — the feedback form.
 *
 * The i18n test is the important one, as it was for the Chart analyst: every
 * label renders through t(), so a missing key does not throw and does not look
 * broken — i18next echoes the key, and a dotted string on screen is easy to
 * mistake for a label. Earlier in this project a whole translation section
 * shipped missing in both locales and only a test like this caught it.
 */
import fs from 'fs';
import path from 'path';

const L = (f) => JSON.parse(fs.readFileSync(
  path.join(__dirname, '../../../i18n/locales', f), 'utf8'));
const en = L('en.json');
const vi = L('vi.json');
const source = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
const api = fs.readFileSync(path.join(__dirname, '../../../services/api.js'), 'utf8');

const flatten = (o, p = '') => Object.entries(o).reduce((a, [k, v]) => {
  const key = `${p}${k}`;
  return typeof v === 'object' && v !== null
    ? { ...a, ...flatten(v, `${key}.`) } : { ...a, [key]: v };
}, {});

const flatEn = flatten(en);
const flatVi = flatten(vi);
const literalKeys = [...source.matchAll(/\bt\(\s*'([^']+)'/g)].map((m) => m[1]);

// Template keys the component builds from its own CATEGORIES list and from
// server-supplied status values.
const CATEGORIES = ['idea', 'problem', 'confusing', 'praise', 'other'];
const STATUSES = ['new', 'triaged', 'done', 'declined'];

describe('Feedback i18n', () => {
  it('renders a meaningful number of translated strings (guards the guard)', () => {
    expect(literalKeys.length).toBeGreaterThan(10);
  });

  it.each([['en', flatEn], ['vi', flatVi]])('every literal key exists in %s', (_l, flat) => {
    expect(literalKeys.filter((k) => !(k in flat))).toEqual([]);
  });

  it.each([['en', flatEn], ['vi', flatVi]])('every category label and hint exists in %s', (_l, flat) => {
    const missing = CATEGORIES.flatMap((c) => [
      `feedback.category.${c}`, `feedback.category_hint.${c}`,
    ]).filter((k) => !(k in flat));
    expect(missing).toEqual([]);
  });

  it.each([['en', flatEn], ['vi', flatVi]])('every triage status renders in %s', (_l, flat) => {
    // The server can return any of these; an untranslated one would show the
    // user a raw dotted key where their status should be.
    expect(STATUSES.filter((s) => !(`feedback.status.${s}` in flat))).toEqual([]);
  });

  it('the two locales carry the same feedback keys', () => {
    const k = (f) => Object.keys(f).filter((x) => x.startsWith('feedback.')).sort();
    expect(k(flatEn)).toEqual(k(flatVi));
  });

  it('every {{placeholder}} matches across locales', () => {
    const ph = (s) => [...String(s).matchAll(/{{(\w+)}}/g)].map((m) => m[1]).sort();
    const bad = Object.keys(flatEn)
      .filter((k) => k.startsWith('feedback.') && k in flatVi)
      .filter((k) => JSON.stringify(ph(flatEn[k])) !== JSON.stringify(ph(flatVi[k])));
    expect(bad).toEqual([]);
  });

  it('the Vietnamese is not the English copied', () => {
    const keys = Object.keys(flatEn).filter((k) => k.startsWith('feedback.') && k in flatVi);
    const identical = keys.filter((k) => flatEn[k] === flatVi[k]);
    expect(identical.length).toBeLessThan(keys.length / 4);
  });

  it('the sidebar entry is translated in both locales', () => {
    expect(flatEn['sidebar.feedback']).toBeTruthy();
    expect(flatVi['sidebar.feedback']).toBeTruthy();
    expect(flatEn['sidebar.feedback']).not.toEqual(flatVi['sidebar.feedback']);
  });
});

describe('Feedback behaviour', () => {
  it('defaults to an idea rather than a problem', () => {
    // A form that opens on "something is wrong" invites complaints; the point
    // of this page is to collect what people want next.
    expect(source).toMatch(/useState\('idea'\)/);
  });

  it('attaches the current page automatically', () => {
    // The single most useful field, and the one a user never supplies: "the
    // numbers look wrong" means something different per screen.
    expect(api).toMatch(/window\.location\.pathname/);
    expect(source).not.toMatch(/placeholder.*which page/i);
  });

  it('refuses a too-short message in the UI, not only on the server', () => {
    expect(source).toMatch(/MIN_MESSAGE/);
    expect(source).toMatch(/trimmed\.length\s*>=\s*MIN_MESSAGE/);
  });

  it('trims before measuring, so spaces cannot pass the length check', () => {
    expect(source).toMatch(/message\.trim\(\)/);
  });

  it('keeps the rating optional', () => {
    expect(source).toMatch(/rating:\s*rating\s*\|\|\s*null/);
  });

  it('asks permission before treating the user as contactable', () => {
    expect(source).toMatch(/contact_ok/);
    expect(source).toMatch(/type="checkbox"/);
  });

  it('shows the user their own past submissions', () => {
    // A form with no receipt gets the same note sent twice, or not at all.
    expect(source).toMatch(/getMyFeedback/);
    expect(source).toMatch(/feedback\.mine_title/);
  });

  it('never blocks the form when the receipt list fails to load', () => {
    expect(source).toMatch(/setMine\(\[\]\)/);
  });
});
