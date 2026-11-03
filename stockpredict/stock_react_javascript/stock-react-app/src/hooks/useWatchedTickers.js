import { useEffect, useState } from 'react';
import { stockAPI } from '../services/api';

/**
 * Symbols the user WATCHES — and only those.
 *
 * Deliberately NOT `useUserTickers`, which returns watchlist ∪ default-portfolio
 * holdings. That union is right for the pages that already use it, but it would
 * put a BOUGHT symbol into a list labelled "watched". The owner draws that line
 * explicitly: the portfolio is what was bought, the watchlist is what is only
 * being watched, and #118's selector asks for the latter.
 *
 * Returns { tickers: [{symbol, name}], loading, error }.
 */
export default function useWatchedTickers() {
  const [tickers, setTickers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const watchlist = await stockAPI.getWatchlist();
        const seen = new Set();
        const rows = (watchlist || [])
          .map((item) => ({
            symbol: item.symbol || item,
            name: item.name || item.company_name || item.symbol || String(item),
          }))
          .filter((item) => {
            if (!item.symbol || seen.has(item.symbol)) return false;
            seen.add(item.symbol);
            return true;
          })
          .sort((a, b) => a.symbol.localeCompare(b.symbol));
        if (!cancelled) { setTickers(rows); setError(null); }
      } catch (e) {
        // An empty list and a failed request are different states: the first
        // means "watch something first", the second means "try again". The UI
        // says different things for each, so they must not collapse here.
        if (!cancelled) { setTickers([]); setError(e.message || 'failed'); }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return { tickers, loading, error };
}
