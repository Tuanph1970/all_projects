// src/contexts/RouterContext.js
import React, { createContext, useContext, useState } from 'react';

const RouterContext = createContext();

export const RouterProvider = ({ children }) => {
  const [currentRoute, setCurrentRoute] = useState('dashboard');

  const navigate = (route) => {
    setCurrentRoute(route);
  };

  const value = {
    currentRoute,
    navigate
  };

  return (
    <RouterContext.Provider value={value}>
      {children}
    </RouterContext.Provider>
  );
};

export const useRouter = () => {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return context;
};