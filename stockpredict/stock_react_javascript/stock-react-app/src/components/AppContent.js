// src/components/AppContent.js
import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import LoginForm from './Auth/LoginForm';
import MainLayout from './Layout/MainLayout';

const AppContent = () => {
  const { user } = useAuth();

  if (!user) {
    return <LoginForm />;
  }

  return <MainLayout />;
};

export default AppContent;