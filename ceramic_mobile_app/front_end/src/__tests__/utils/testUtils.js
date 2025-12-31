import React from 'react';
import { render } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { NavigationContainer } from '@react-navigation/native';
import { PaperProvider } from 'react-native-paper';
import configureStore from 'redux-mock-store';
import { thunk } from 'redux-thunk';

const middlewares = [thunk];
const mockStore = configureStore(middlewares);

/**
 * Custom render function that wraps components with necessary providers
 */
export function renderWithProviders(
  ui,
  {
    initialState = {},
    store = mockStore(initialState),
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <Provider store={store}>
        <PaperProvider>
          <NavigationContainer>
            {children}
          </NavigationContainer>
        </PaperProvider>
      </Provider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    store,
  };
}

/**
 * Create a mock Redux store with initial state
 */
export function createMockStore(initialState = {}) {
  const defaultState = {
    auth: {
      user: null,
      token: null,
      isLoading: false,
      error: null,
      isAuthenticated: false,
    },
    products: {
      items: [],
      isLoading: false,
      error: null,
    },
    cart: {
      items: [],
      total: 0,
    },
    ...initialState,
  };

  return mockStore(defaultState);
}

/**
 * Mock navigation object
 */
export function createMockNavigation() {
  return {
    navigate: jest.fn(),
    goBack: jest.fn(),
    reset: jest.fn(),
    setOptions: jest.fn(),
    dispatch: jest.fn(),
    isFocused: jest.fn(() => true),
    canGoBack: jest.fn(() => true),
    getParent: jest.fn(),
    getState: jest.fn(),
  };
}

/**
 * Mock route object
 */
export function createMockRoute(params = {}) {
  return {
    key: 'mock-route-key',
    name: 'MockRoute',
    params,
  };
}

/**
 * Wait for async operations to complete
 */
export function waitForAsync() {
  return new Promise(resolve => setImmediate(resolve));
}

/**
 * Mock API response
 */
export function mockApiResponse(data, success = true) {
  if (success) {
    return Promise.resolve({ data });
  }
  return Promise.reject(new Error('API Error'));
}

/**
 * Common test data
 */
export const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  fullName: 'Test User',
  role: 'customer',
};

export const mockProduct = {
  id: '1',
  name: 'Test Ceramic Vase',
  description: 'Beautiful handcrafted vase',
  price: 25000,
  imageUrl: 'https://example.com/image.jpg',
  sellerId: '2',
  stock: 10,
};

export const mockSeller = {
  id: '2',
  username: 'testseller',
  email: 'seller@example.com',
  fullName: 'Test Seller',
  role: 'seller',
  shopName: 'Test Ceramics Shop',
};

// Re-export everything from testing library
export * from '@testing-library/react-native';
