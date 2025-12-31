import React from 'react';
import { fireEvent, waitFor } from '@testing-library/react-native';
import { renderWithProviders, createMockStore } from '../utils/testUtils';
import { LoginScreen } from '../../screens/auth/LoginScreen';
import { loginUser } from '../../store/slices/authSlice';
import apiClient from '../../services/apiClient';

// Mock API client
jest.mock('../../services/apiClient');

// Mock authSlice
jest.mock('../../store/slices/authSlice', () => ({
  loginUser: jest.fn(),
  clearError: jest.fn(() => ({ type: 'auth/clearError' })),
}));

describe('Authentication Flow Integration Tests', () => {
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

  describe('Successful Login Flow', () => {
    it('should complete full login flow successfully', async () => {
      // Mock successful API response
      const mockUser = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        fullName: 'Test User',
        role: 'customer',
      };

      const mockToken = 'mock-jwt-token';

      loginUser.mockReturnValue(async (dispatch) => {
        dispatch({
          type: 'auth/loginUser/fulfilled',
          payload: { user: mockUser, token: mockToken },
        });
        return { payload: { user: mockUser, token: mockToken } };
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

      // Step 1: User enters credentials
      const usernameInput = getByTestId('login-username-input');
      const passwordInput = getByTestId('login-password-input');

      fireEvent.changeText(usernameInput, 'testuser');
      fireEvent.changeText(passwordInput, 'password123');

      // Step 2: User submits form
      const submitButton = getByTestId('login-submit-button');
      fireEvent.press(submitButton);

      // Step 3: Verify API was called
      await waitFor(() => {
        expect(loginUser).toHaveBeenCalled();
      });

      // Step 4: Verify success toast is shown
      await waitFor(() => {
        expect(require('react-native-toast-message').show).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'success',
            text1: 'Login Successful',
          })
        );
      });
    });

    it('should handle login with email instead of username', async () => {
      const mockUser = {
        id: 1,
        email: 'test@example.com',
        fullName: 'Test User',
      };

      loginUser.mockReturnValue(async (dispatch) => {
        dispatch({
          type: 'auth/loginUser/fulfilled',
          payload: { user: mockUser, token: 'token' },
        });
        return { payload: { user: mockUser, token: 'token' } };
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

      const usernameInput = getByTestId('login-username-input');
      const passwordInput = getByTestId('login-password-input');

      // Enter email instead of username
      fireEvent.changeText(usernameInput, 'test@example.com');
      fireEvent.changeText(passwordInput, 'password123');

      const submitButton = getByTestId('login-submit-button');
      fireEvent.press(submitButton);

      await waitFor(() => {
        expect(loginUser).toHaveBeenCalledWith(
          expect.objectContaining({
            username: 'test@example.com',
          })
        );
      });
    });
  });

  describe('Failed Login Flow', () => {
    it('should handle invalid credentials error', async () => {
      loginUser.mockReturnValue(async (dispatch) => {
        dispatch({
          type: 'auth/loginUser/rejected',
          error: { message: 'Invalid username or password' },
        });
        throw new Error('Invalid username or password');
      });

      const errorStore = createMockStore({
        auth: {
          user: null,
          token: null,
          isLoading: false,
          error: 'Invalid username or password',
          isAuthenticated: false,
        },
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store: errorStore });

      const usernameInput = getByTestId('login-username-input');
      const passwordInput = getByTestId('login-password-input');

      fireEvent.changeText(usernameInput, 'wronguser');
      fireEvent.changeText(passwordInput, 'wrongpass');

      const submitButton = getByTestId('login-submit-button');
      fireEvent.press(submitButton);

      // Verify error toast is shown
      await waitFor(() => {
        expect(require('react-native-toast-message').show).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'error',
            text1: 'Login Failed',
          })
        );
      });
    });

    it('should handle network error gracefully', async () => {
      loginUser.mockReturnValue(async () => {
        throw new Error('Network request failed');
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

      const usernameInput = getByTestId('login-username-input');
      const passwordInput = getByTestId('login-password-input');

      fireEvent.changeText(usernameInput, 'testuser');
      fireEvent.changeText(passwordInput, 'password123');

      const submitButton = getByTestId('login-submit-button');
      fireEvent.press(submitButton);

      await waitFor(() => {
        expect(loginUser).toHaveBeenCalled();
      });
    });
  });

  describe('Form Validation Flow', () => {
    it('should prevent submission with empty fields', async () => {
      const { getByTestId, findByText } = renderWithProviders(<LoginScreen />, { store });

      const submitButton = getByTestId('login-submit-button');

      // Try to submit with empty fields
      fireEvent.press(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(findByText('Username or email is required')).toBeTruthy();
        expect(findByText('Password is required')).toBeTruthy();
      });

      // Login should not be called
      expect(loginUser).not.toHaveBeenCalled();
    });

    it('should validate field lengths before submission', async () => {
      const { getByTestId, findByText } = renderWithProviders(<LoginScreen />, { store });

      const usernameInput = getByTestId('login-username-input');
      const passwordInput = getByTestId('login-password-input');

      // Enter values that are too short
      fireEvent.changeText(usernameInput, 'ab');
      fireEvent.changeText(passwordInput, '123');

      const submitButton = getByTestId('login-submit-button');
      fireEvent.press(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(findByText('Username must be at least 3 characters')).toBeTruthy();
        expect(findByText('Password must be at least 6 characters')).toBeTruthy();
      });

      // Login should not be called
      expect(loginUser).not.toHaveBeenCalled();
    });
  });

  describe('Navigation Flow', () => {
    it('should navigate to register screen when link is clicked', () => {
      const mockNavigate = jest.fn();
      jest.spyOn(require('@react-navigation/native'), 'useNavigation').mockReturnValue({
        navigate: mockNavigate,
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

      const registerLink = getByTestId('login-register-link');
      fireEvent.press(registerLink);

      expect(mockNavigate).toHaveBeenCalledWith('Register');
    });

    it('should navigate to forgot password screen when link is clicked', () => {
      const mockNavigate = jest.fn();
      jest.spyOn(require('@react-navigation/native'), 'useNavigation').mockReturnValue({
        navigate: mockNavigate,
      });

      const { getByTestId } = renderWithProviders(<LoginScreen />, { store });

      const forgotPasswordLink = getByTestId('login-forgot-password-link');
      fireEvent.press(forgotPasswordLink);

      expect(mockNavigate).toHaveBeenCalledWith('ForgotPassword');
    });
  });
});
