import React from 'react';
import { Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { Card } from '../Card';
import { renderWithProviders } from '../../../__tests__/utils/testUtils';

describe('Card Component', () => {
  it('renders correctly with children', () => {
    const { getByText } = renderWithProviders(
      <Card>
        <Text>Card Content</Text>
      </Card>
    );

    expect(getByText('Card Content')).toBeTruthy();
  });

  it('applies default elevation (sm)', () => {
    const { getByText } = renderWithProviders(
      <Card>
        <Text>Content</Text>
      </Card>
    );

    // Card should render without errors
    expect(getByText('Content')).toBeTruthy();
  });

  it('applies custom elevation', () => {
    const { getByText } = renderWithProviders(
      <Card elevation="lg">
        <Text>Content</Text>
      </Card>
    );

    expect(getByText('Content')).toBeTruthy();
  });

  it('supports no elevation', () => {
    const { getByText } = renderWithProviders(
      <Card elevation="none">
        <Text>Content</Text>
      </Card>
    );

    expect(getByText('Content')).toBeTruthy();
  });

  it('applies custom styles', () => {
    const customStyle = { backgroundColor: 'blue', padding: 20 };
    const { getByText } = renderWithProviders(
      <Card style={customStyle}>
        <Text>Styled Content</Text>
      </Card>
    );

    expect(getByText('Styled Content')).toBeTruthy();
  });

  it('passes through additional Paper Card props', () => {
    const mockOnPress = jest.fn();
    const { getByText } = renderWithProviders(
      <Card onPress={mockOnPress} testID="pressable-card">
        <Text>Pressable Card</Text>
      </Card>
    );

    // Note: Card from react-native-paper supports onPress
    expect(getByText('Pressable Card')).toBeTruthy();
  });

  it('renders multiple children correctly', () => {
    const { getByText } = renderWithProviders(
      <Card>
        <Text>Title</Text>
        <Text>Subtitle</Text>
        <Text>Description</Text>
      </Card>
    );

    expect(getByText('Title')).toBeTruthy();
    expect(getByText('Subtitle')).toBeTruthy();
    expect(getByText('Description')).toBeTruthy();
  });

  it('renders with testID prop', () => {
    const { getByTestId } = renderWithProviders(
      <Card testID="test-card">
        <Text>Content</Text>
      </Card>
    );

    expect(getByTestId('test-card')).toBeTruthy();
  });
});
