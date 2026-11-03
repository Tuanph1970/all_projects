/**
 * Price alerts — above / below / change-percent (Backlog #117 refactor).
 *
 * Extracted from Alerts.js UNCHANGED in behaviour. The UI vocabulary stays
 * `price_above` / `price_below`; the API vocabulary is `above` / `below`, and
 * that translation lives in services/api.js transformAlertCreateRequest where
 * it already did. Nothing here alters what a price alert does — this module
 * exists so the volume type can be added beside it rather than inside it.
 */

export const PRICE_ABOVE = 'price_above';
export const PRICE_BELOW = 'price_below';
export const CHANGE_PERCENT = 'change_percent';

const base = {
  fields: ['targetPrice'],
  defaults: { targetPrice: '' },

  validate(form) {
    const n = parseFloat(form.targetPrice);
    if (!Number.isFinite(n) || n <= 0) return 'alerts.err_price_required';
    return null;
  },

  fromAlert(alert) {
    return { targetPrice: alert.targetPrice != null ? String(alert.targetPrice) : '' };
  },

  /**
   * A price alert CAN be recomputed in the browser, because the comparison is
   * against a price already on screen — which is why this behaviour is kept
   * exactly as Alerts.js had it.
   */
  status(alert) {
    if (alert.isActive === false) return 'inactive';
    if (alert.triggered) return 'triggered';
    const { alertType, targetPrice, currentPrice } = alert;
    if (alertType === PRICE_ABOVE && currentPrice >= targetPrice) return 'triggered';
    if (alertType === PRICE_BELOW && currentPrice <= targetPrice) return 'triggered';
    return 'active';
  },
};

export const priceAboveAlert = {
  ...base,
  type: PRICE_ABOVE,
  labelKey: 'alerts.type_price_above',
  toRequest(form) {
    return { alertType: PRICE_ABOVE, targetPrice: parseFloat(form.targetPrice), targetPercent: null };
  },
  describe(alert, t) {
    return t('alerts.desc_price_above', { price: alert.targetPrice });
  },
};

export const priceBelowAlert = {
  ...base,
  type: PRICE_BELOW,
  labelKey: 'alerts.type_price_below',
  toRequest(form) {
    return { alertType: PRICE_BELOW, targetPrice: parseFloat(form.targetPrice), targetPercent: null };
  },
  describe(alert, t) {
    return t('alerts.desc_price_below', { price: alert.targetPrice });
  },
};
