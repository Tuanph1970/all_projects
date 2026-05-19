// src/App.js
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StyleSheetManager } from 'styled-components';
import { AuthProvider } from './context/AuthContext';
import { StockProvider } from './context/StockContext';
import { DecisionProvider } from './context/DecisionContext';
import { useAuth } from './context/AuthContext';
import LoginForm from './components/Auth/LoginForm';
import ResetPasswordConfirm from './components/Auth/ResetPasswordConfirm';
import MainLayout from './components/Layout/MainLayout';
import shouldForwardProp from './utils/shouldForwardProp';

import './styles/index.css';
import './styles/auth.css';
import './styles/layout.css';
import './styles/dashboard.css';
import './styles/component.css';
import './styles/tab_styles.css';
import './styles/table_style.css';
import './styles/performance.css';
import './styles/knowledge-qa.css';

// homepage in package.json — BrowserRouter strips this prefix from routes.
const BASENAME = '/stock-app';

const AppShell = () => {
  const { user, isInitializing } = useAuth();

  if (isInitializing) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Validating session...
      </div>
    );
  }

  return user ? <MainLayout /> : <LoginForm />;
};

const App = () => {
  return (
    <StyleSheetManager shouldForwardProp={shouldForwardProp}>
      <BrowserRouter basename={BASENAME}>
        <AuthProvider>
          <Routes>
            {/* Reset-password is the one route that intentionally bypasses
                auth — users arrive here via an emailed token. */}
            <Route path="/reset-password" element={<ResetPasswordConfirm />} />

            {/* Everything else is gated by auth. MainLayout handles its
                own <Routes> for in-app navigation. The wildcard captures
                any path so back/forward keep working. */}
            <Route
              path="/*"
              element={
                <StockProvider>
                  <DecisionProvider>
                    <AppShell />
                  </DecisionProvider>
                </StockProvider>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </StyleSheetManager>
  );
};

export default App;
