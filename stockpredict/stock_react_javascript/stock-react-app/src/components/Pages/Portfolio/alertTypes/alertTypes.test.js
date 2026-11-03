/**
 * Backlog #117 — the alert-type registry.
 *
 * These are the tests Alerts.js never had. The point of the registry is that a
 * new alert kind is ONE module rather than five conditionals threaded through a
 * 518-line component, so what is tested here is that each type answers for
 * itself and that the price types behave exactly as they did before.
 */
import {
  ALERT_TYPES,
  getAlertType,
  needsField,
  priceAboveAlert,
  priceBelowAlert,
  volumeAlert,
} from './index';
import { DEFAULT_MULTIPLE, VOLUME_ALERT_TYPE } from './volumeAlert';

const t = (key, vars) =>
  vars ? `${key}:${JSON.stringify(vars)}` : key;

describe('the registry', () => {
  it('offers every type the UI should list', () => {
    expect(ALERT_TYPES.map((s) => s.type)).toEqual([
      'price_above', 'price_below', 'volume_unusual',
    ]);
  });

  it('falls back to price-above for an unknown type, as Alerts.js did', () => {
    expect(getAlertType('something_new').type).toBe('price_above');
    expect(getAlertType(undefined).type).toBe('price_above');
  });

  it('routes each type to the field it actually needs', () => {
    expect(needsField('price_above', 'targetPrice')).toBe(true);
    expect(needsField('price_above', 'multiple')).toBe(false);
    expect(needsField(VOLUME_ALERT_TYPE, 'multiple')).toBe(true);
    expect(needsField(VOLUME_ALERT_TYPE, 'targetPrice')).toBe(false);
  });
});

describe('volume alert', () => {
  it('sends the multiple and no target price', () => {
    expect(volumeAlert.toRequest({ multiple: '4.5' })).toEqual({
      alertType: 'volume_unusual', targetPercent: 4.5, targetPrice: null,
    });
  });

  it('falls back to the measured default rather than sending nothing', () => {
    expect(DEFAULT_MULTIPLE).toBe(3.0);
    expect(volumeAlert.toRequest({ multiple: '' }).targetPercent).toBe(3.0);
  });

  it('refuses a multiple that would fire on an ordinary day', () => {
    // Rejected, not clamped: silently changing what the user asked for is
    // worse than refusing, and below ~1 a "spike" alert is simply broken.
    expect(volumeAlert.validate({ multiple: '0.9' })).toBe('alerts.err_multiple_too_small');
    expect(volumeAlert.validate({ multiple: '1' })).toBe('alerts.err_multiple_too_small');
    expect(volumeAlert.validate({ multiple: '3' })).toBeNull();
  });

  it('refuses a multiple that would never fire', () => {
    expect(volumeAlert.validate({ multiple: '500' })).toBe('alerts.err_multiple_too_large');
  });

  it('refuses a non-number instead of defaulting silently', () => {
    expect(volumeAlert.validate({ multiple: 'abc' })).toBe('alerts.err_multiple_required');
    expect(volumeAlert.validate({ multiple: '' })).toBe('alerts.err_multiple_required');
  });

  it('round-trips through the edit form', () => {
    const form = volumeAlert.fromAlert({ targetPercent: 4 });
    expect(form.multiple).toBe('4');
    expect(volumeAlert.toRequest(form).targetPercent).toBe(4);
  });

  it('trusts the backend flag rather than inventing a status from a price', () => {
    // The multiple is measured against history the browser does not hold, so
    // any locally-computed status would be a guess dressed as a measurement.
    expect(volumeAlert.status({ isActive: true, triggered: true, currentPrice: 1 })).toBe('triggered');
    expect(volumeAlert.status({ isActive: true, triggered: false, currentPrice: 999999 })).toBe('active');
    expect(volumeAlert.status({ isActive: false, triggered: true })).toBe('inactive');
  });

  it('describes itself as a multiple, never as a price', () => {
    const text = volumeAlert.describe({ targetPercent: 3 }, t);
    expect(text).toContain('desc_volume_unusual');
    expect(text).toContain('"multiple":3');
  });
});

describe('price alerts are unchanged', () => {
  it('still compare against the price on screen', () => {
    expect(priceAboveAlert.status({ isActive: true, alertType: 'price_above', targetPrice: 100, currentPrice: 101 })).toBe('triggered');
    expect(priceAboveAlert.status({ isActive: true, alertType: 'price_above', targetPrice: 100, currentPrice: 99 })).toBe('active');
    expect(priceBelowAlert.status({ isActive: true, alertType: 'price_below', targetPrice: 100, currentPrice: 99 })).toBe('triggered');
    expect(priceBelowAlert.status({ isActive: true, alertType: 'price_below', targetPrice: 100, currentPrice: 101 })).toBe('active');
  });

  it('still send a target price and no percent', () => {
    expect(priceAboveAlert.toRequest({ targetPrice: '25000' })).toEqual({
      alertType: 'price_above', targetPrice: 25000, targetPercent: null,
    });
  });

  it('still refuse a missing or zero price', () => {
    expect(priceAboveAlert.validate({ targetPrice: '' })).toBe('alerts.err_price_required');
    expect(priceAboveAlert.validate({ targetPrice: '0' })).toBe('alerts.err_price_required');
    expect(priceAboveAlert.validate({ targetPrice: '100' })).toBeNull();
  });

  it('still mark an inactive alert inactive', () => {
    expect(priceAboveAlert.status({ isActive: false })).toBe('inactive');
  });
});

describe('the wire transform (services/api.js)', () => {
  // target_percent was NOT sent at all before #117, so a volume alert's
  // multiple was silently dropped en route to an API that accepts it: the alert
  // would have been created at the backend default rather than the number
  // typed, with nothing reporting the difference. The transform is
  // module-private, so this reads the source — which is what is actually being
  // checked, rather than pretending to exercise it through a fetch mock.
  const fs = require('fs');
  const path = require('path');
  const src = fs.readFileSync(
    path.join(__dirname, '..', '..', '..', '..', 'services', 'api.js'), 'utf8');

  // Each window is bounded to its OWN function. An earlier version sliced 600
  // characters from the create function, which spilled into the update function
  // nine lines below it — so deleting target_percent from the create transform
  // left the test green, reading a match that belonged to its neighbour. The
  // mutation caught that, not the test.
  // COMMENTS ARE STRIPPED, and that is not fussiness. The first version of
  // this searched the raw window for "target_percent" — which also appears in
  // the explanatory COMMENT above that field, so deleting the field itself left
  // the test green, matching documentation instead of code. Two mutations were
  // needed to notice.
  const bodyOf = (name) => {
    const start = src.indexOf(`const ${name} = `);
    expect(start).toBeGreaterThan(-1);
    const end = src.indexOf('});', start);
    expect(end).toBeGreaterThan(start);
    return src
      .slice(start, end)
      .split('\n')
      .filter((line) => !line.trim().startsWith('//'))
      .join('\n');
  };

  it('sends target_percent on create', () => {
    expect(bodyOf('transformAlertCreateRequest')).toMatch(/target_percent:\s*alertData/);
  });

  it('sends target_percent on update, so a multiple can be edited', () => {
    expect(bodyOf('transformAlertUpdateRequest')).toMatch(/target_percent:\s*alertData/);
  });

  it('the two windows really are different functions', () => {
    // Guards the guard: if bodyOf returned the same slice twice, the two tests
    // above would pass together or fail together for the wrong reason.
    expect(bodyOf('transformAlertCreateRequest')).not.toEqual(
      bodyOf('transformAlertUpdateRequest'));
    expect(bodyOf('transformAlertCreateRequest')).toContain('symbol');
    expect(bodyOf('transformAlertUpdateRequest')).not.toContain('symbol');
  });

  it('still maps the UI vocabulary onto the API vocabulary', () => {
    expect(src).toContain("'price_above' ? 'above'");
    expect(src).toContain("'price_below' ? 'below'");
  });
});

describe('a volume alert re-arms daily (#117)', () => {
  const { firedToday } = require('./volumeAlert');
  // Mid-session on 2026-11-03 ICT: 05:00 UTC = 12:00 ICT.
  const now = new Date('2026-11-03T05:00:00Z');

  it('reads as triggered when it fired earlier the same market day', () => {
    const alert = { isActive: true, triggered: true, triggeredAt: '2026-11-03T02:30:00Z' };
    expect(firedToday(alert.triggeredAt, now)).toBe(true);
  });

  it('reads as ARMED again when it fired on a previous day', () => {
    // The whole point: a one-shot volume alert goes quiet forever after its
    // first spike. Showing "triggered" would say it is spent when it is not.
    expect(firedToday('2026-11-02T02:30:00Z', now)).toBe(false);
  });

  it('treats an absent or unparseable timestamp as armed', () => {
    expect(firedToday(null, now)).toBe(false);
    expect(firedToday(undefined, now)).toBe(false);
    expect(firedToday('not-a-date', now)).toBe(false);
  });

  it('uses the MARKET day, so a late-UTC firing is still today in ICT', () => {
    // 2026-11-02 19:00 UTC is 2026-11-03 02:00 ICT — the same market day as
    // `now`. Judged in UTC this would look like yesterday and the alert would
    // wrongly re-arm mid-session.
    expect(firedToday('2026-11-02T19:00:00Z', now)).toBe(true);
  });

  it('status follows it: fired yesterday means active, fired today means triggered', () => {
    const { volumeAlert } = require('./volumeAlert');
    const base = { isActive: true, triggered: true };
    // Uses the real clock, so build the timestamps relative to it.
    const todayIso = new Date().toISOString();
    const longAgoIso = new Date(Date.now() - 5 * 24 * 3600 * 1000).toISOString();
    expect(volumeAlert.status({ ...base, triggeredAt: todayIso })).toBe('triggered');
    expect(volumeAlert.status({ ...base, triggeredAt: longAgoIso })).toBe('active');
    expect(volumeAlert.status({ isActive: false, triggered: true, triggeredAt: todayIso })).toBe('inactive');
  });

  it('a price alert stays one-shot', () => {
    const { priceAboveAlert } = require('./priceAlert');
    const longAgoIso = new Date(Date.now() - 5 * 24 * 3600 * 1000).toISOString();
    expect(priceAboveAlert.status({
      isActive: true, triggered: true, triggeredAt: longAgoIso,
      alertType: 'price_above', targetPrice: 100, currentPrice: 1,
    })).toBe('triggered');
  });
});

describe('a set flag with no timestamp (#117)', () => {
  it('is reported as triggered, not silently downgraded to armed', () => {
    // The backend writes is_triggered and triggered_at together, so this should
    // not arise — but reading a SET flag as "not fired" would understate it,
    // and that is the wrong direction to be wrong about an alert.
    const { volumeAlert } = require('./volumeAlert');
    expect(volumeAlert.status({ isActive: true, triggered: true })).toBe('triggered');
    expect(volumeAlert.status({ isActive: true, triggered: true, triggeredAt: null })).toBe('triggered');
  });
});
