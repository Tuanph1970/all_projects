import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import { combineReducers } from '@reduxjs/toolkit';
import * as SecureStore from 'expo-secure-store';

import authReducer from './slices/authSlice';
import problemReducer from './slices/problemSlice';
import solutionReducer from './slices/solutionSlice';
import userReducer from './slices/userSlice';
import appReducer from './slices/appSlice';
import bookmarkReducer from './slices/bookmarkSlice';

// Validate SecureStore key format
const validateSecureStoreKey = (key) => {
  if (!key || typeof key !== 'string' || key.length === 0) {
    return false;
  }
  // Keys must contain only alphanumeric characters, ".", "-", and "_"
  const validKeyPattern = /^[a-zA-Z0-9._-]+$/;
  return validKeyPattern.test(key);
};

// Sanitize key for SecureStore
const sanitizeKey = (key) => {
  if (!key || typeof key !== 'string') {
    return 'fallback_key';
  }
  // Replace invalid characters with underscores
  return key.replace(/[^a-zA-Z0-9._-]/g, '_');
};

// Custom storage implementation using Expo SecureStore
const secureStorage = {
  async getItem(key) {
    try {
      if (!validateSecureStoreKey(key)) {
        console.warn(`Invalid SecureStore key: "${key}", using sanitized version`);
        key = sanitizeKey(key);
      }
      const value = await SecureStore.getItemAsync(key);
      return value;
    } catch (error) {
      console.error('SecureStore getItem error:', error);
      return null;
    }
  },
  async setItem(key, value) {
    try {
      if (!validateSecureStoreKey(key)) {
        console.warn(`Invalid SecureStore key: "${key}", using sanitized version`);
        key = sanitizeKey(key);
      }
      await SecureStore.setItemAsync(key, value);
    } catch (error) {
      console.error('SecureStore setItem error:', error);
    }
  },
  async removeItem(key) {
    try {
      if (!validateSecureStoreKey(key)) {
        console.warn(`Invalid SecureStore key: "${key}", using sanitized version`);
        key = sanitizeKey(key);
      }
      await SecureStore.deleteItemAsync(key);
    } catch (error) {
      console.error('SecureStore removeItem error:', error);
    }
  }
};

// Root reducer
const rootReducer = combineReducers({
  auth: authReducer,
  problem: problemReducer,
  solution: solutionReducer,
  user: userReducer,
  app: appReducer,
  bookmarks: bookmarkReducer
});

// Persist configuration
const persistConfig = {
  key: 'mathematics_app_root',
  storage: secureStorage,
  whitelist: ['auth', 'user', 'app'], // Only persist these reducers
  blacklist: ['problem', 'solution'], // Don't persist temporary data
  version: 1,
  debug: __DEV__, // Enable debug in development
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

// Configure store
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          'persist/REHYDRATE',
          'persist/PAUSE',
          'persist/PURGE',
          'persist/REGISTER'
        ],
        ignoredActionsPaths: ['meta.arg', 'payload.timestamp'],
        ignoredPaths: ['items.dates']
      },
      immutableCheck: {
        ignoredPaths: ['ignoredPath', 'ignoredNested.one', 'ignoredNested.two']
      }
    }),
  devTools: __DEV__ // Enable Redux DevTools in development
});

export const persistor = persistStore(store);

// Infer the `RootState` and `AppDispatch` types from the store itself
export const selectAuth = (state) => state.auth;
export const selectProblem = (state) => state.problem;
export const selectSolution = (state) => state.solution;
export const selectUser = (state) => state.user;
export const selectApp = (state) => state.app;
export const selectBookmarks = (state) => state.bookmarks;