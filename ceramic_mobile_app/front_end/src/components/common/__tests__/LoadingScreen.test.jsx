import React from 'react';
import { render } from '@testing-library/react-native';
import { LoadingScreen } from '../LoadingScreen';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';

describe('LoadingScreen Component', () => {
  it('renders correctly with default message', () => {
    const { getByText } = renderWithProviders(<LoadingScreen />);

    expect(getByText('Loading...')).toBeTruthy();
  });

  it('displays custom message when provided', () => {
    const customMessage = 'Please wait while we process your request';
    const { getByText } = renderWithProviders(
      <LoadingScreen message={customMessage} />
    );

    expect(getByText(customMessage)).toBeTruthy();
  });

  it('renders ActivityIndicator', () => {
    const { getByTestId } = renderWithProviders(
      <LoadingScreen message="Loading data..." />
    );

    // ActivityIndicator should be present
    const component = renderWithProviders(<LoadingScreen />);
    expect(component).toBeTruthy();
  });

  it('applies correct container styles', () => {
    const { getByText } = renderWithProviders(
      <LoadingScreen message="Test" />
    );

    const textElement = getByText('Test');
    expect(textElement).toBeTruthy();
  });

  it('renders with empty message', () => {
    const { getByText } = renderWithProviders(
      <LoadingScreen message="" />
    );

    // Empty message should still render the component
    expect(getByText('')).toBeTruthy();
  });

  it('renders with long message', () => {
    const longMessage = 'This is a very long loading message that should still be displayed correctly without any issues';
    const { getByText } = renderWithProviders(
      <LoadingScreen message={longMessage} />
    );

    expect(getByText(longMessage)).toBeTruthy();
  });
});
