import React from 'react';
import { fireEvent, waitFor } from '@testing-library/react-native';
import { renderWithProviders, createMockStore } from '../../../__tests__/utils/testUtils';
import { LoginScreen } from '../LoginScreen';
import { loginUser } from '../../../store/slices/authSlice';

// Mock the authSlice actions
jest.mock('../../../store/slices/authSlice', () => ({
  loginUser: jest.fn(),
  clearError: jest.fn(() => ({ type: 'auth/clearError' })),
}));

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
  }),
}));

describe('LoginScreen', () => {
  let store;

  beforeEach(() => {
    jest.clearAllMocks();
    store = createMockStore({
      auth: {
        user: null,
        token: null,
        isLoading: false,
        error: null,
        isAuthenticated: false,
      },
    });
  });

  it('renders login form correctly', () => {
    const { getByText, getByTestId } = renderWithProviders(<LoginScreen />, { store });

    expect(getByText('Welcome Back')).toBeTruthy();
    expect(getByText('Sign in to your account')).toBeTruthy();
    expect(getByTestId('login-username-input')).toBeTruthy();
    expect(getByTestId('login-password-input')).toBeTruthy();
    expect(getByTestId('login-submit-button')).toBeTruthy();
  });

  it('validates empty username', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<LoginScreen />, { store });

    const usernameInput = getByTestId('login-username-input');
    const passwordInput = getByTestId('login-password-input');

    // Focus and blur username without entering text
    fireEvent.changeText(usernameInput, '');
    fireEvent.changeText(passwordInput, 'SomePassword123');

    // Should show validation error (may already be visible)
    await waitFor(() => {
      expect(queryByText('Username or email is required')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates empty password', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<LoginScreen />, { store });

    const usernameInput = getByTestId('login-username-input');
    const passwordInput = getByTestId('login-password-input');

    // Enter username but leave password empty
    fireEvent.changeText(usernameInput, 'testuser');
    fireEvent.changeText(passwordInput, '');

    // Should show validation error (may already be visible)
    await waitFor(() => {
      expect(queryByText('Password is required')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates minimum username length', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<LoginScreen />, { store });

    const usernameInput = getByTestId('login-username-input');

    // Enter username less than 3 characters
    fireEvent.changeText(usernameInput, 'ab');

    // Should show validation error (may already be visible)
    await waitFor(() => {
      expect(queryByText('Username must be at least 3 characters')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates minimum password length', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<LoginScreen />, { store });

    const passwordInput = getByTestId('login-password-input');

    // Enter password less than 6 characters
    fireEvent.changeText(passwordInput, '12345');

    // Should show validation error (may already be visible)
    await waitFor(() => {
      expect(queryByText('Password must be at least 6 characters')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('toggles password visibility', () => {
    const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

    const toggleButton = getByTestId('login-password-toggle');
    const passwordInput = getByTestId('login-password-input');

    // Initially password should be hidden (secureTextEntry = true)
    expect(passwordInput.props.secureTextEntry).toBe(true);

    // Click toggle to show password
    fireEvent.press(toggleButton);
    expect(passwordInput.props.secureTextEntry).toBe(false);

    // Click again to hide password
    fireEvent.press(toggleButton);
    expect(passwordInput.props.secureTextEntry).toBe(true);
  });

  it('submits login form with valid credentials', async () => {
    const mockLoginUser = loginUser.mockReturnValue({
      type: 'auth/loginUser/fulfilled',
      payload: { user: { id: 1, username: 'testuser' }, token: 'mock-token' },
    });

    const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

    const usernameInput = getByTestId('login-username-input');
    const passwordInput = getByTestId('login-password-input');
    const submitButton = getByTestId('login-submit-button');

    // Enter valid credentials
    fireEvent.changeText(usernameInput, 'testuser');
    fireEvent.changeText(passwordInput, 'password123');

    // Submit form
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(mockLoginUser).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
      });
    });
  });

  it('navigates to register screen', () => {
    const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

    const registerLink = getByTestId('login-register-link');
    fireEvent.press(registerLink);

    expect(mockNavigate).toHaveBeenCalledWith('Register');
  });

  it('navigates to forgot password screen', () => {
    const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

    const forgotPasswordLink = getByTestId('login-forgot-password-link');
    fireEvent.press(forgotPasswordLink);

    expect(mockNavigate).toHaveBeenCalledWith('ForgotPassword');
  });

  it('shows loading state during login', () => {
    const loadingStore = createMockStore({
      auth: {
        user: null,
        token: null,
        isLoading: true,
        error: null,
        isAuthenticated: false,
      },
    });

    const { getByTestId } = renderWithProviders(<LoginScreen />, { store: loadingStore });

    const submitButton = getByTestId('login-submit-button');

    // Button should show loading state
    expect(submitButton.props.accessibilityState.disabled).toBe(true);
  });

  it('displays error message when login fails', async () => {
    const errorStore = createMockStore({
      auth: {
        user: null,
        token: null,
        isLoading: false,
        error: 'Invalid credentials',
        isAuthenticated: false,
      },
    });

    renderWithProviders(<LoginScreen />, { store: errorStore });

    // Toast should be called with error message
    await waitFor(() => {
      expect(require('react-native-toast-message').show).toHaveBeenCalled();
    });
  });
});
