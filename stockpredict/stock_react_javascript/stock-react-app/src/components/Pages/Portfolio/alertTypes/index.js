/**
 * Registry of alert types, keyed by the type string (Backlog #117).
 *
 * Alerts.js asks the registry what a given alert needs — which form field,
 * which label, how to describe it, whether it has fired — instead of branching
 * on the type in five separate places. Adding a fifth alert type means adding
 * one module here, not editing handleSubmit, handleEdit, resetForm, getStatus
 * and the render and hoping none was missed.
 */
import { priceAboveAlert, priceBelowAlert } from './priceAlert';
import { volumeAlert } from './volumeAlert';

export const ALERT_TYPES = [priceAboveAlert, priceBelowAlert, volumeAlert];

const BY_TYPE = ALERT_TYPES.reduce((acc, t) => ({ ...acc, [t.type]: t }), {});

/** The price-above behaviour is the fallback, matching Alerts.js's old default. */
export const getAlertType = (type) => BY_TYPE[type] || priceAboveAlert;

/** Does this type need the target-price field, or the volume-multiple field? */
export const needsField = (type, field) => getAlertType(type).fields.includes(field);

export { priceAboveAlert, priceBelowAlert, volumeAlert };
