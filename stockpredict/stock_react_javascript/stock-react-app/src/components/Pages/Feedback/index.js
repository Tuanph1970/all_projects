import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle, CheckCircle2, HelpCircle, Lightbulb,
  MessageSquarePlus, Send, Star, ThumbsUp,
} from 'lucide-react';
import { stockAPI } from '../../../services/api';

/**
 * v0.9 — the feedback form.
 *
 * Built to collect ideas and opinions, so the DEFAULT is "idea" rather than
 * "problem": a form that opens on a bug report invites complaints, and the
 * hardest signal to collect is what people want next.
 *
 * `page` is attached automatically from the current route by the API layer.
 * That one field is most of the form's value — "the numbers look wrong" means
 * something quite different from the Chart analyst than from the Risk
 * Dashboard, and nobody ever says which.
 */

const CATEGORIES = [
  { value: 'idea', Icon: Lightbulb },
  { value: 'problem', Icon: AlertTriangle },
  { value: 'confusing', Icon: HelpCircle },
  { value: 'praise', Icon: ThumbsUp },
  { value: 'other', Icon: MessageSquarePlus },
];

const MIN_MESSAGE = 4;
const MAX_MESSAGE = 4000;

export default function Feedback() {
  const { t } = useTranslation();
  const [category, setCategory] = useState('idea');
  const [message, setMessage] = useState('');
  const [rating, setRating] = useState(0);
  const [contactOk, setContactOk] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(null);
  const [error, setError] = useState(null);
  const [mine, setMine] = useState([]);

  const loadMine = useCallback(async () => {
    try {
      setMine(await stockAPI.getMyFeedback());
    } catch (e) {
      setMine([]);   // the list is a convenience; never block the form on it
    }
  }, []);

  useEffect(() => { loadMine(); }, [loadMine]);

  const trimmed = message.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_MESSAGE;
  const canSend = trimmed.length >= MIN_MESSAGE && !sending;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSend) return;
    setSending(true);
    setError(null);
    setSent(null);
    try {
      const row = await stockAPI.submitFeedback({
        category,
        message: trimmed,
        rating: rating || null,
        contact_ok: contactOk,
      });
      setSent(row);
      setMessage('');
      setRating(0);
      await loadMine();
    } catch (err) {
      setError(err.message || 'failed');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="p-4 max-w-3xl space-y-4">
      <div>
        <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <MessageSquarePlus className="w-5 h-5 text-blue-600" />
          {t('feedback.title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('feedback.subtitle')}</p>
      </div>

      {sent && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <div className="text-sm text-emerald-900">
            <div className="font-semibold">{t('feedback.sent_title')}</div>
            <div>{t('feedback.sent_body', { id: sent.id })}</div>
          </div>
        </div>
      )}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-sm text-rose-800">
          {t('feedback.failed', { reason: error })}
        </div>
      )}

      <form onSubmit={submit}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-4">
        <fieldset>
          <legend className="text-xs font-medium text-gray-600 mb-2">
            {t('feedback.category_label')}
          </legend>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(({ value, Icon }) => {
              const active = category === value;
              return (
                <button
                  key={value} type="button" onClick={() => setCategory(value)}
                  aria-pressed={active}
                  className={`px-3 py-2 rounded-lg text-sm border flex items-center gap-2 ${
                    active
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'}`}
                >
                  <Icon className="w-4 h-4" />
                  {t(`feedback.category.${value}`)}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {t(`feedback.category_hint.${category}`)}
          </p>
        </fieldset>

        <label className="block">
          <span className="text-xs font-medium text-gray-600">
            {t('feedback.message_label')}
          </span>
          <textarea
            value={message} onChange={(e) => setMessage(e.target.value)}
            rows={6} maxLength={MAX_MESSAGE}
            placeholder={t('feedback.message_placeholder')}
            className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex justify-between mt-1">
            <span className={`text-xs ${tooShort ? 'text-rose-600' : 'text-gray-400'}`}>
              {tooShort ? t('feedback.too_short', { min: MIN_MESSAGE })
                        : t('feedback.message_hint')}
            </span>
            <span className="text-xs text-gray-400">
              {trimmed.length}/{MAX_MESSAGE}
            </span>
          </div>
        </label>

        <div>
          <span className="text-xs font-medium text-gray-600">
            {t('feedback.rating_label')}
          </span>
          <div className="flex items-center gap-1 mt-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n} type="button" onClick={() => setRating(rating === n ? 0 : n)}
                aria-label={t('feedback.rating_star', { n })}
                className="p-1"
              >
                <Star className={`w-5 h-5 ${
                  n <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-300'}`} />
              </button>
            ))}
            <span className="text-xs text-gray-400 ml-2">
              {t('feedback.rating_optional')}
            </span>
          </div>
        </div>

        <label className="flex items-start gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={contactOk} className="mt-1"
                 onChange={(e) => setContactOk(e.target.checked)} />
          <span>{t('feedback.contact_ok')}</span>
        </label>

        <div className="flex items-center gap-3">
          <button type="submit" disabled={!canSend}
            className="px-5 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2">
            <Send className="w-4 h-4" />
            {sending ? t('feedback.sending') : t('feedback.send')}
          </button>
          <span className="text-xs text-gray-400">{t('feedback.context_note')}</span>
        </div>
      </form>

      {mine.length > 0 && (
        <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <h2 className="text-sm font-bold text-gray-800 mb-3">
            {t('feedback.mine_title')}
          </h2>
          <ul className="space-y-2">
            {mine.map((f) => (
              <li key={f.id} className="border-l-4 border-slate-200 bg-slate-50 rounded px-3 py-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-slate-600">
                    {t(`feedback.category.${f.category}`)}
                    {f.page ? ` · ${f.page}` : ''}
                  </span>
                  <span className="text-xs text-slate-400">
                    {t(`feedback.status.${f.status}`)}
                    {f.created_at ? ` · ${String(f.created_at).slice(0, 10)}` : ''}
                  </span>
                </div>
                <p className="text-sm text-slate-700 mt-1 whitespace-pre-wrap">{f.message}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
