// src/App.js
import React from 'react';
import { StyleSheetManager } from 'styled-components';
import { AuthProvider } from './context/AuthContext';
import { RouterProvider } from './context/RouterContext';
import { StockProvider } from './context/StockContext';
import { useAuth } from './context/AuthContext';
import LoginForm from './components/Auth/LoginForm';
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


const AppContent = () => {
  const { user, loading, isInitializing } = useAuth();

  // Only show loading state during initial token validation, not during login/register
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

  if (!user) {
    return <LoginForm />;
  }

  return <MainLayout />;
};

const App = () => {
  return (
    <StyleSheetManager shouldForwardProp={shouldForwardProp}>
      <AuthProvider>
        <RouterProvider>
          <StockProvider>
            <AppContent />
          </StockProvider>
        </RouterProvider>
      </AuthProvider>
    </StyleSheetManager>
  );
};

export default App;