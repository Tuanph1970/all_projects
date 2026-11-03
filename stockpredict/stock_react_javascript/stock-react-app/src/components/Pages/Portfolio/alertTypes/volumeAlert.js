/**
 * Unusual-volume alert — Backlog #117.
 *
 * Its own module rather than another branch inside Alerts.js, because a volume
 * alert shares almost nothing with a price alert: it carries a MULTIPLE of the
 * symbol's own median volume, not a target price, so its form field, its
 * display, its validation and its "has it fired" logic all differ. Folding that
 * into the 518-line price-centric component would mean conditionals threaded
 * through handleSubmit, handleEdit, resetForm, getStatus and the render — five
 * places, each a chance to leave one branch price-shaped. That is the same
 * mixing that let VOLUME_UNUSUAL reach the domain enum and not the API one.
 *
 * WHAT THE READING MEANS. The backend publishes `rel_volume`: today's volume
 * over the MEDIAN of that symbol's own trailing history. Per-symbol by
 * construction — "high" means high for that stock, so HPG's ordinary 17.6M
 * shares and VCB's ordinary 3.6M both read 1.0.
 *
 * THE DEFAULT IS 3.0x AND IT WAS MEASURED, not chosen: across 42,674 real
 * readings on 32 symbols, 3.0x fires on 4.55% of bars — about monthly per
 * symbol — where 1.5x fires on 23.95%, roughly eight a day across a watchlist.
 *
 * WHAT IT MUST NOT SAY: nothing here claims good or bad news. A volume spike is
 * ATTENTION, not direction.
 */

export const VOLUME_ALERT_TYPE = 'volume_unusual';

/** Measured default; see the module docstring. */
export const DEFAULT_MULTIPLE = 3.0;

/** Below 1.0 a "spike" alert would fire on ordinary or quiet days. */
export const MIN_MULTIPLE = 1.1;
export const MAX_MULTIPLE = 50;

export const volumeAlert = {
  type: VOLUME_ALERT_TYPE,
  labelKey: 'alerts.type_volume_unusual',

  /** The field this type needs: a multiple, not a price. */
  fields: ['multiple'],

  defaults: { multiple: String(DEFAULT_MULTIPLE) },

  /**
   * Validate the operator's input. Returns an i18n key, or null when valid.
   * A multiple at or below 1.0 is rejected rather than clamped: it would make
   * the alert fire on a normal day, which is not a tighter alert but a broken
   * one, and silently changing what the user asked for is worse than refusing.
   */
  validate(form) {
    const n = parseFloat(form.multiple);
    if (!Number.isFinite(n)) return 'alerts.err_multiple_required';
    if (n < MIN_MULTIPLE) return 'alerts.err_multiple_too_small';
    if (n > MAX_MULTIPLE) return 'alerts.err_multiple_too_large';
    return null;
  },

  /** Map the form onto the API request. `targetPrice` is deliberately absent. */
  toRequest(form) {
    return {
      alertType: VOLUME_ALERT_TYPE,
      targetPercent: parseFloat(form.multiple) || DEFAULT_MULTIPLE,
      targetPrice: null,
    };
  },

  /** Populate the edit form from a stored alert. */
  fromAlert(alert) {
    const stored = alert.targetPercent != null ? alert.targetPercent : DEFAULT_MULTIPLE;
    return { multiple: String(stored) };
  },

  /** One-line summary for the list. */
  describe(alert, t) {
    const multiple = alert.targetPercent != null ? alert.targetPercent : DEFAULT_MULTIPLE;
    return t('alerts.desc_volume_unusual', { multiple });
  },

  /**
   * Has it fired? Unlike a price alert this cannot be recomputed in the
   * browser: the multiple is measured against history the UI does not hold, so
   * the only truthful answer is the backend's own flag. Guessing from whatever
   * price happens to be on screen would invent a status.
   */
  status(alert) {
    if (alert.isActive === false) return 'inactive';
    return alert.triggered ? 'triggered' : 'active';
  },
};

export default volumeAlert;
