// F-030 — Decision context: shares the latest recommendation across pages
import React, { createContext, useContext, useState, useCallback } from 'react';
import helperService from '../services/helperService';

const DecisionContext = createContext(null);

export const DecisionProvider = ({ children }) => {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ticker, setTicker] = useState('');

  const runRecommend = useCallback(async (tickerSymbol, barDate) => {
    setLoading(true);
    setError(null);
    setTicker(tickerSymbol);
    try {
      const data = await helperService.recommend({ ticker: tickerSymbol, barDate });
      setRecommendation(data);
      return data;
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Recommendation failed';
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearRecommendation = useCallback(() => {
    setRecommendation(null);
    setError(null);
  }, []);

  return (
    <DecisionContext.Provider value={{
      recommendation, loading, error, ticker,
      runRecommend, clearRecommendation,
    }}>
      {children}
    </DecisionContext.Provider>
  );
};

export const useDecision = () => {
  const ctx = useContext(DecisionContext);
  if (!ctx) throw new Error('useDecision must be used inside DecisionProvider');
  return ctx;
};
