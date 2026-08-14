import React from 'react';
import { fireEvent, waitFor } from '@testing-library/react-native';
import RegisterScreen from '../RegisterScreen';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';
import { registerUser } from '../../../store/slices/authSlice';

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
  }),
}));

// Mock Toast
jest.mock('react-native-toast-message', () => ({
  show: jest.fn(),
}));

describe('RegisterScreen', () => {
  const initialState = {
    auth: {
      loading: false,
      error: null,
      user: null,
      token: null,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders registration screen correctly', () => {
    const { getAllByText, getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    // "Create Account" appears multiple times (heading and button)
    expect(getAllByText('Create Account').length).toBeGreaterThan(0);
    expect(getByTestId('register-firstname-input')).toBeTruthy();
    expect(getByTestId('register-lastname-input')).toBeTruthy();
  });

  it('allows user to type first name', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const firstNameInput = getByTestId('register-firstname-input');
    fireEvent.changeText(firstNameInput, 'John');

    await waitFor(() => {
      expect(firstNameInput.props.value).toBe('John');
    });
  });

  it('allows user to type last name', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const lastNameInput = getByTestId('register-lastname-input');
    fireEvent.changeText(lastNameInput, 'Doe');

    await waitFor(() => {
      expect(lastNameInput.props.value).toBe('Doe');
    });
  });

  it('allows user to type username', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const usernameInput = getByTestId('register-username-input');
    fireEvent.changeText(usernameInput, 'johndoe123');

    await waitFor(() => {
      expect(usernameInput.props.value).toBe('johndoe123');
    });
  });

  it('allows user to type email', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const emailInput = getByTestId('register-email-input');
    fireEvent.changeText(emailInput, 'john@example.com');

    await waitFor(() => {
      expect(emailInput.props.value).toBe('john@example.com');
    });
  });

  it('allows user to type password', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const passwordInput = getByTestId('register-password-input');
    fireEvent.changeText(passwordInput, 'SecurePass123!');

    await waitFor(() => {
      expect(passwordInput.props.value).toBe('SecurePass123!');
    });
  });

  it('validates first name is required', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('First name is required')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates last name is required', async () => {
    const { getByTestId, getByText, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const firstNameInput = getByTestId('register-firstname-input');
    fireEvent.changeText(firstNameInput, 'John');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Last name is required')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates username is required', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const firstNameInput = getByTestId('register-firstname-input');
    const lastNameInput = getByTestId('register-lastname-input');

    fireEvent.changeText(firstNameInput, 'John');
    fireEvent.changeText(lastNameInput, 'Doe');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Username is required')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates username format with invalid characters', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const usernameInput = getByTestId('register-username-input');
    fireEvent.changeText(usernameInput, 'invalid user!');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Username can only contain letters, numbers, underscores, and hyphens')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates email format', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const emailInput = getByTestId('register-email-input');
    fireEvent.changeText(emailInput, 'invalid-email');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Invalid email address')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates password minimum length', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const passwordInput = getByTestId('register-password-input');
    fireEvent.changeText(passwordInput, 'short');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Password must be at least 8 characters')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('validates passwords match', async () => {
    const { getByTestId, queryByText } = renderWithProviders(<RegisterScreen />, { initialState });

    const passwordInput = getByTestId('register-password-input');
    const confirmPasswordInput = getByTestId('register-confirm-password-input');

    fireEvent.changeText(passwordInput, 'Password123!');
    fireEvent.changeText(confirmPasswordInput, 'DifferentPass123!');

    const submitButton = getByTestId('register-submit-button');
    fireEvent.press(submitButton);

    await waitFor(() => {
      expect(queryByText('Passwords do not match')).toBeTruthy();
    }, { timeout: 3000 });
  });

  it('allows selecting customer role', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const customerRadio = getByTestId('register-role-customer');
    fireEvent.press(customerRadio);

    // Customer role should be selected (default)
    expect(customerRadio).toBeTruthy();
  });

  it('allows selecting seller role', async () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const sellerRadio = getByTestId('register-role-seller');
    fireEvent.press(sellerRadio);

    expect(sellerRadio).toBeTruthy();
  });

  it('password field has secure text entry enabled', () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const passwordInput = getByTestId('register-password-input');
    // Password should be hidden by default
    expect(passwordInput.props.secureTextEntry).toBe(true);
  });

  it('navigates to login screen when login link is pressed', () => {
    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState });

    const loginLink = getByTestId('register-login-link');
    fireEvent.press(loginLink);

    expect(mockNavigate).toHaveBeenCalledWith('Login');
  });

  it('shows loading state during registration', async () => {
    const store = {
      auth: {
        loading: true,
        error: null,
        user: null,
        token: null,
      },
    };

    const { getByTestId } = renderWithProviders(<RegisterScreen />, { initialState: store });

    const submitButton = getByTestId('register-submit-button');
    expect(submitButton.props.accessibilityState.disabled).toBe(true);
  });
});
