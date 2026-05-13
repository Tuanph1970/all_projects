// src/context/StockContext.js
import React, { createContext, useContext, useState } from 'react';

const StockContext = createContext();

export const StockProvider = ({ children }) => {
  const [selectedStock, setSelectedStock] = useState(null);

  const selectStock = (stock) => {
    setSelectedStock(stock);
  };

  const clearStock = () => {
    setSelectedStock(null);
  };

  const value = {
    selectedStock,
    selectStock,
    clearStock
  };

  return (
    <StockContext.Provider value={value}>
      {children}
    </StockContext.Provider>
  );
};

export const useStock = () => {
  const context = useContext(StockContext);
  if (!context) {
    throw new Error('useStock must be used within a StockProvider');
  }
  return context;
};