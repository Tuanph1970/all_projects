import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true); // Only for initial token validation

  useEffect(() => {
    const validateStoredToken = async () => {
      const token = localStorage.getItem('token');

      if (!token) {
        setIsInitializing(false);
        return;
      }

      // Validate the token with the server
      const validation = await authAPI.validateToken();

      if (validation.valid && validation.user) {
        setUser(validation.user);
      } else {
        // Token is invalid, ensure clean state
        setUser(null);
      }

      setIsInitializing(false);
    };

    validateStoredToken();
  }, []);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const response = await authAPI.login(username, password);
      localStorage.setItem('token', response.token);
      setUser(response.user);
      return response;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    // Clear all authentication data
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    localStorage.removeItem('userId');
    setUser(null);
  };

  const register = async (username, email, password) => {
    setLoading(true);
    try {
      const result = await authAPI.register(username, email, password);
      return result;
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (email) => {
    setLoading(true);
    try {
      return await authAPI.resetPassword(email);
    } finally {
      setLoading(false);
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    setLoading(true);
    try {
      return await authAPI.changePassword(currentPassword, newPassword);
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    login,
    logout,
    register,
    resetPassword,
    changePassword,
    loading,
    isInitializing
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};