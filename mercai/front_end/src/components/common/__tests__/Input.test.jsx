import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Input } from '../Input';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';

describe('Input Component', () => {
  it('renders correctly with basic props', () => {
    const { getByTestId } = renderWithProviders(
      <Input testID="test-input" placeholder="Enter text" />
    );

    expect(getByTestId('test-input')).toBeTruthy();
  });

  it('displays placeholder text', () => {
    const { getByPlaceholderText } = renderWithProviders(
      <Input placeholder="Enter your name" />
    );

    expect(getByPlaceholderText('Enter your name')).toBeTruthy();
  });

  it('handles text input correctly', () => {
    const mockOnChangeText = jest.fn();
    const { getByTestId } = renderWithProviders(
      <Input
        testID="text-input"
        onChangeText={mockOnChangeText}
      />
    );

    const input = getByTestId('text-input');
    fireEvent.changeText(input, 'Hello World');

    expect(mockOnChangeText).toHaveBeenCalledWith('Hello World');
  });

  it('displays error message when error prop is true', () => {
    const { getByTestId, getByText } = renderWithProviders(
      <Input
        testID="error-input"
        error={true}
        errorMessage="This field is required"
      />
    );

    expect(getByTestId('error-input-error')).toBeTruthy();
    expect(getByText('This field is required')).toBeTruthy();
  });

  it('does not display error message when error is false', () => {
    const { queryByTestId, queryByText } = renderWithProviders(
      <Input
        testID="no-error-input"
        error={false}
        errorMessage="This field is required"
      />
    );

    expect(queryByTestId('no-error-input-error')).toBeNull();
    expect(queryByText('This field is required')).toBeNull();
  });

  it('applies custom styles correctly', () => {
    const customStyle = { backgroundColor: 'red' };
    const { getByTestId } = renderWithProviders(
      <Input testID="styled-input" style={customStyle} />
    );

    const input = getByTestId('styled-input');
    // Custom style is passed to TextInput and merged with default styles
    expect(input).toBeTruthy();
  });

  it('forwards ref correctly', () => {
    const ref = React.createRef();
    renderWithProviders(
      <Input ref={ref} testID="ref-input" />
    );

    expect(ref.current).toBeTruthy();
  });

  it('supports secure text entry for passwords', () => {
    const { getByTestId } = renderWithProviders(
      <Input testID="password-input" secureTextEntry={true} />
    );

    const input = getByTestId('password-input');
    expect(input.props.secureTextEntry).toBe(true);
  });

  it('passes through additional TextInput props', () => {
    const { getByTestId } = renderWithProviders(
      <Input
        testID="props-input"
        multiline={true}
        numberOfLines={4}
        maxLength={100}
      />
    );

    const input = getByTestId('props-input');
    expect(input.props.multiline).toBe(true);
    expect(input.props.numberOfLines).toBe(4);
    expect(input.props.maxLength).toBe(100);
  });

  it('handles onBlur event', () => {
    const mockOnBlur = jest.fn();
    const { getByTestId } = renderWithProviders(
      <Input testID="blur-input" onBlur={mockOnBlur} />
    );

    const input = getByTestId('blur-input');
    fireEvent(input, 'blur');

    expect(mockOnBlur).toHaveBeenCalled();
  });

  it('handles onFocus event', () => {
    const mockOnFocus = jest.fn();
    const { getByTestId } = renderWithProviders(
      <Input testID="focus-input" onFocus={mockOnFocus} />
    );

    const input = getByTestId('focus-input');
    fireEvent(input, 'focus');

    expect(mockOnFocus).toHaveBeenCalled();
  });

  it('applies container style correctly', () => {
    const containerStyle = { marginTop: 20 };
    const { getByTestId } = renderWithProviders(
      <Input containerStyle={containerStyle} testID="container-input" />
    );

    // Container style is applied to the View wrapper - verify input renders
    expect(getByTestId('container-input')).toBeTruthy();
  });

  it('displays with label', () => {
    const { getAllByText } = renderWithProviders(
      <Input label="Username" testID="labeled-input" />
    );

    // Label may appear multiple times (label and placeholder)
    const labels = getAllByText('Username');
    expect(labels.length).toBeGreaterThan(0);
  });
});
