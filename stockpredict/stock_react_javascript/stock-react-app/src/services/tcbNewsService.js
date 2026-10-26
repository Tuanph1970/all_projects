/**
 * TCB News service — the pasted TCBS daily research email.
 *
 * Two-step by design (see news-service app/api/tcb_routes.py): `preview` parses without
 * storing anything, `save` commits the mail and pushes the confirmed recommendations to
 * the watchlist. Nothing here calls axios directly; all URLs come from constants/api.js.
 */
import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

class TcbNewsService {
  /**
   * Parse a pasted email without writing anything.
   * @param {string} content       the pasted email body
   * @param {string} [referenceDate] ISO date the mail was received; bounds the
   *                                 session-date guess. Defaults to today server-side.
   */
  async preview(content, referenceDate) {
    return httpClient.post(API_ENDPOINTS.TCB_NEWS_PREVIEW, {
      content,
      reference_date: referenceDate || undefined,
    });
  }

  /**
   * Store a previewed email and push the chosen recommendations to the watchlist.
   * @param {object}   params
   * @param {string}   params.content       the pasted email body
   * @param {string}   params.sessionDate   ISO date of the session the mail describes
   * @param {string}   [params.subject]
   * @param {string[]} [params.pushSymbols] tickers to write to the watchlist. Pass []
   *                                        to store without touching the watchlist;
   *                                        omit to push every recognised call.
   * @param {string}   [params.proposalBy]  attribution, defaults to "TCB"
   * @param {object[]}  [params.corrections] operator fixes to misparsed calls
   *                                        (Backlog #55): `{index, from_symbol,
   *                                        symbol?, action?, target_price?}`. The
   *                                        server re-parses `content`, so a preview
   *                                        edit only survives if it is sent here —
   *                                        and it records each overridden field so a
   *                                        later reparse does not revert it (EC-B2).
   */
  async save({ content, sessionDate, subject, pushSymbols, proposalBy, corrections }) {
    return httpClient.post(API_ENDPOINTS.TCB_NEWS, {
      content,
      session_date: sessionDate,
      subject: subject || undefined,
      push_symbols: pushSymbols,
      proposal_by: proposalBy || 'TCB',
      corrections: corrections?.length ? corrections : undefined,
    });
  }

  /** Stored emails, newest session first. */
  async list({ since, until, limit = 50, offset = 0 } = {}) {
    return httpClient.get(API_ENDPOINTS.TCB_NEWS, {
      params: { since, until, limit, offset },
    });
  }

  async get(id) {
    return httpClient.get(API_ENDPOINTS.TCB_NEWS_ITEM(id));
  }

  async remove(id) {
    return httpClient.delete(API_ENDPOINTS.TCB_NEWS_ITEM(id));
  }

  /** The recommendation ledger across all stored emails, with forward returns. */
  async recos({ symbol, action, limit = 100 } = {}) {
    return httpClient.get(API_ENDPOINTS.TCB_NEWS_RECOS, {
      params: { symbol, action, limit },
    });
  }

  /**
   * TCB's aggregate track record. Responds 409 until enough calls are scored —
   * that is the designed behaviour (FR-BM-RECORD), not an error to retry.
   */
  async record() {
    return httpClient.get(API_ENDPOINTS.TCB_NEWS_RECORD);
  }

  /** Run a forward-return scoring pass now, rather than waiting for the schedule. */
  async score() {
    return httpClient.post(API_ENDPOINTS.TCB_NEWS_SCORE, {});
  }
}

const tcbNewsService = new TcbNewsService();
export default tcbNewsService;
