import { useEffect, useState } from 'react';
import { stockAPI } from '../services/api';

/**
 * Tickers the user actually follows: watchlist ∪ default-portfolio holdings,
 * de-duplicated, watchlist first. Drives the symbol dropdowns on analysis
 * pages (Technical Analysis, Chart Decomposition) so users pick from what
 * they own or watch instead of typing a free-text code.
 *
 * Returns { tickers: [{symbol, name}], loading }.
 */
export default function useUserTickers() {
  const [tickers, setTickers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const [watchlist, portfolio] = await Promise.all([
          stockAPI.getWatchlist().catch(() => []),
          stockAPI.getPortfolio().catch(() => [])
        ]);
        const fromWatch = (watchlist || []).map(item => ({
          symbol: item.symbol || item,
          name: item.name || item.company_name || item.symbol || String(item)
        }));
        const fromPortfolio = (portfolio || []).map(item => ({
          symbol: item.symbol,
          name: item.name || item.company_name || item.symbol
        }));
        const seen = new Set();
        const combined = [...fromWatch, ...fromPortfolio].filter(item => {
          if (!item.symbol || seen.has(item.symbol)) return false;
          seen.add(item.symbol);
          return true;
        });
        if (!cancelled) setTickers(combined);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  return { tickers, loading };
}
