import { createSlice } from '@reduxjs/toolkit';

// Initial state for app-wide settings and status
const initialState = {
  // App status
  isInitialized: false,
  isOnline: true,
  networkType: null, // '2g', '3g', '4g', '5g', 'wifi', 'cellular', 'unknown'
  
  // UI state
  theme: 'light', // 'light', 'dark', 'system'
  orientation: 'portrait', // 'portrait', 'landscape'
  isKeyboardVisible: false,
  safeAreaInsets: {
    top: 0,
    bottom: 0,
    left: 0,
    right: 0
  },
  
  // Navigation state
  currentRoute: null,
  navigationHistory: [],
  
  // Loading states
  globalLoading: false,
  loadingMessage: '',
  
  // Error handling
  globalError: null,
  errorQueue: [],
  
  // Notifications
  pushToken: null,
  notificationPermission: null, // 'granted', 'denied', 'undetermined'
  unreadNotifications: 0,
  
  // Cache management
  cacheSize: 0,
  lastCacheCleanup: null,
  
  // Feature flags
  features: {
    cameraEnabled: true,
    offlineMode: false,
    betaFeatures: false,
    analytics: true
  },
  
  // App performance
  performance: {
    appStartTime: null,
    renderTime: null,
    apiResponseTimes: []
  }
};

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    // App initialization
    setInitialized: (state, action) => {
      state.isInitialized = action.payload;
      if (action.payload && !state.performance.appStartTime) {
        state.performance.appStartTime = Date.now();
      }
    },
    
    // Network status
    setNetworkStatus: (state, action) => {
      state.isOnline = action.payload.isOnline;
      state.networkType = action.payload.networkType;
    },
    
    // Theme management
    setTheme: (state, action) => {
      state.theme = action.payload;
    },
    
    // Orientation
    setOrientation: (state, action) => {
      state.orientation = action.payload;
    },
    
    // Keyboard visibility
    setKeyboardVisible: (state, action) => {
      state.isKeyboardVisible = action.payload;
    },
    
    // Safe area insets
    setSafeAreaInsets: (state, action) => {
      state.safeAreaInsets = action.payload;
    },
    
    // Navigation
    setCurrentRoute: (state, action) => {
      state.currentRoute = action.payload;
      // Add to navigation history
      if (state.navigationHistory[state.navigationHistory.length - 1] !== action.payload) {
        state.navigationHistory.push(action.payload);
        // Limit history to 50 items
        if (state.navigationHistory.length > 50) {
          state.navigationHistory = state.navigationHistory.slice(-50);
        }
      }
    },
    
    clearNavigationHistory: (state) => {
      state.navigationHistory = [];
    },
    
    // Global loading
    setGlobalLoading: (state, action) => {
      state.globalLoading = action.payload.isLoading;
      state.loadingMessage = action.payload.message || '';
    },
    
    // Error management
    setGlobalError: (state, action) => {
      state.globalError = action.payload;
    },
    
    clearGlobalError: (state) => {
      state.globalError = null;
    },
    
    addToErrorQueue: (state, action) => {
      state.errorQueue.push({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...action.payload
      });
      // Limit error queue to 20 items
      if (state.errorQueue.length > 20) {
        state.errorQueue = state.errorQueue.slice(-20);
      }
    },
    
    removeFromErrorQueue: (state, action) => {
      state.errorQueue = state.errorQueue.filter(error => error.id !== action.payload);
    },
    
    clearErrorQueue: (state) => {
      state.errorQueue = [];
    },
    
    // Notifications
    setPushToken: (state, action) => {
      state.pushToken = action.payload;
    },
    
    setNotificationPermission: (state, action) => {
      state.notificationPermission = action.payload;
    },
    
    setUnreadNotifications: (state, action) => {
      state.unreadNotifications = Math.max(0, action.payload);
    },
    
    incrementUnreadNotifications: (state) => {
      state.unreadNotifications += 1;
    },
    
    decrementUnreadNotifications: (state) => {
      state.unreadNotifications = Math.max(0, state.unreadNotifications - 1);
    },
    
    // Cache management
    setCacheSize: (state, action) => {
      state.cacheSize = action.payload;
    },
    
    setCacheCleanupTime: (state) => {
      state.lastCacheCleanup = Date.now();
    },
    
    // Feature flags
    updateFeatures: (state, action) => {
      state.features = { ...state.features, ...action.payload };
    },
    
    toggleFeature: (state, action) => {
      const { feature } = action.payload;
      if (feature in state.features) {
        state.features[feature] = !state.features[feature];
      }
    },
    
    // Performance tracking
    setRenderTime: (state, action) => {
      state.performance.renderTime = action.payload;
    },
    
    addApiResponseTime: (state, action) => {
      state.performance.apiResponseTimes.push({
        timestamp: Date.now(),
        duration: action.payload.duration,
        endpoint: action.payload.endpoint,
        status: action.payload.status
      });
      // Limit to 100 entries
      if (state.performance.apiResponseTimes.length > 100) {
        state.performance.apiResponseTimes = state.performance.apiResponseTimes.slice(-100);
      }
    },
    
    clearPerformanceData: (state) => {
      state.performance.apiResponseTimes = [];
    },
    
    // Reset app state
    resetAppState: (state) => {
      return {
        ...initialState,
        features: state.features, // Preserve feature flags
        safeAreaInsets: state.safeAreaInsets // Preserve device-specific data
      };
    }
  }
});

export const {
  setInitialized,
  setNetworkStatus,
  setTheme,
  setOrientation,
  setKeyboardVisible,
  setSafeAreaInsets,
  setCurrentRoute,
  clearNavigationHistory,
  setGlobalLoading,
  setGlobalError,
  clearGlobalError,
  addToErrorQueue,
  removeFromErrorQueue,
  clearErrorQueue,
  setPushToken,
  setNotificationPermission,
  setUnreadNotifications,
  incrementUnreadNotifications,
  decrementUnreadNotifications,
  setCacheSize,
  setCacheCleanupTime,
  updateFeatures,
  toggleFeature,
  setRenderTime,
  addApiResponseTime,
  clearPerformanceData,
  resetAppState
} = appSlice.actions;

export default appSlice.reducer;