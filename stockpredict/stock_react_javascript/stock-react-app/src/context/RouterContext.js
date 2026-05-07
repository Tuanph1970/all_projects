// src/context/RouterContext.js
//
// Thin compatibility shim over react-router-dom v6. Keeps the legacy
// {currentRoute, navigate} API the rest of the app uses, while delegating
// to react-router-dom underneath so the URL bar reflects the current
// route and browser back/forward works.
//
// Route string convention:
//   - 'dashboard' -> '/'
//   - 'company/FPT' -> '/company/FPT'
//   - everything else -> '/<route>'
//
// To migrate a callsite to native react-router, replace useRouter() with
// useNavigate() and useLocation()/useParams() — this shim exists so we
// don't have to do it all at once.
import React, { createContext, useContext, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const RouterContext = createContext();

const DEFAULT_ROUTE = 'dashboard';

const pathnameToRoute = (pathname) => {
  // Strip leading slash. BrowserRouter basename ('/stock-app') already
  // handled by react-router-dom, so pathname here is post-basename.
  const stripped = (pathname || '/').replace(/^\/+/, '');
  if (!stripped) return DEFAULT_ROUTE;
  return stripped;
};

const routeToPath = (route) => {
  if (!route || route === DEFAULT_ROUTE) return '/';
  return `/${route}`;
};

export const RouterProvider = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const currentRoute = pathnameToRoute(location.pathname);

  const navigateRoute = useCallback((route) => {
    navigate(routeToPath(route));
  }, [navigate]);

  const value = {
    currentRoute,
    navigate: navigateRoute,
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
