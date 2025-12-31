import React from 'react';
import { fireEvent } from '@testing-library/react-native';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';
import { Button } from '../Button';

describe('Button Component', () => {
  it('renders correctly with text', () => {
    const { getByText } = renderWithProviders(
      <Button>Click Me</Button>
    );

    expect(getByText('Click Me')).toBeTruthy();
  });

  it('calls onPress when clicked', () => {
    const onPressMock = jest.fn();
    const { getByText } = renderWithProviders(
      <Button onPress={onPressMock}>Click Me</Button>
    );

    const button = getByText('Click Me');
    fireEvent.press(button);

    expect(onPressMock).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    const onPressMock = jest.fn();
    const { getByText } = renderWithProviders(
      <Button disabled onPress={onPressMock}>
        Disabled Button
      </Button>
    );

    const button = getByText('Disabled Button');
    fireEvent.press(button);

    // Should not call onPress when disabled
    expect(onPressMock).not.toHaveBeenCalled();
  });

  it('shows loading state', () => {
    const { getByTestId } = renderWithProviders(
      <Button loading testID="loading-button">
        Loading
      </Button>
    );

    // Paper Button shows ActivityIndicator when loading
    expect(getByTestId('loading-button')).toBeTruthy();
  });

  it('renders with different modes', () => {
    const { rerender, getByText } = renderWithProviders(
      <Button mode="contained">Contained</Button>
    );

    expect(getByText('Contained')).toBeTruthy();

    rerender(
      <Button mode="outlined">Outlined</Button>
    );

    expect(getByText('Outlined')).toBeTruthy();

    rerender(
      <Button mode="text">Text</Button>
    );

    expect(getByText('Text')).toBeTruthy();
  });

  it('renders with icon', () => {
    const { getByText } = renderWithProviders(
      <Button icon="login">Login</Button>
    );

    expect(getByText('Login')).toBeTruthy();
  });

  it('applies custom styles', () => {
    const customStyle = { marginTop: 20 };
    const { getByTestId } = renderWithProviders(
      <Button style={customStyle} testID="custom-button">
        Custom
      </Button>
    );

    const button = getByTestId('custom-button');
    expect(button).toBeTruthy();
  });
});
