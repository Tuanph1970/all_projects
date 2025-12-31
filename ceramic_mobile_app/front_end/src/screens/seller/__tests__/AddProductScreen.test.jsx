import React from 'react';
import { fireEvent, waitFor, act } from '@testing-library/react-native';
import { renderWithProviders, createMockStore } from '../../../__tests__/utils/testUtils';
import { AddProductScreen } from '../AddProductScreen';
import productService from '../../../services/productService';
import * as ImagePicker from 'expo-image-picker';

// Mock services
jest.mock('../../../services/productService', () => ({
  createProduct: jest.fn(),
  uploadProductImages: jest.fn(),
  getCategories: jest.fn(),
}));

// Mock ImagePicker
jest.mock('expo-image-picker', () => ({
  requestMediaLibraryPermissionsAsync: jest.fn(),
  launchImageLibraryAsync: jest.fn(),
  MediaTypeOptions: {
    Images: 'Images',
  },
}));

// Mock navigation
const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
    goBack: mockGoBack,
  }),
}));

// Mock Alert
const mockAlert = jest.fn();

// Add Alert mock to global object
global.Alert = {
  alert: mockAlert,
};

const mockImageResult = {
  canceled: false,
  assets: [
    {
      uri: 'file://mock-image.jpg',
      width: 800,
      height: 600,
      type: 'image/jpeg',
    }
  ]
};

describe('AddProductScreen', () => {
  let store;

  beforeEach(() => {
    jest.clearAllMocks();
    store = createMockStore({
      auth: {
        user: { id: '1', role: 'seller' },
        token: 'mock-token',
        isAuthenticated: true,
      },
    });

    // Mock successful permission request
    ImagePicker.requestMediaLibraryPermissionsAsync.mockResolvedValue({
      status: 'granted'
    });

    // Mock successful image picker
    ImagePicker.launchImageLibraryAsync.mockResolvedValue(mockImageResult);

    // Mock successful product creation
    productService.createProduct.mockResolvedValue({
      id: '1',
      success: true,
    });

    // Mock successful image upload
    productService.uploadProductImages.mockResolvedValue({
      success: true,
      images: ['image1.jpg', 'image2.jpg']
    });
  });

  describe('Basic Rendering', () => {
    it('renders add product screen correctly', () => {
      const { getByText } = renderWithProviders(<AddProductScreen />, { store });

      expect(getByText('Add Product')).toBeTruthy();
      expect(getByText('Product Images')).toBeTruthy();
      expect(getByText('Product Details')).toBeTruthy();
      expect(getByText('Create Product')).toBeTruthy();
    });

    it('requests media library permissions on mount', async () => {
      renderWithProviders(<AddProductScreen />, { store });

      await waitFor(() => {
        expect(ImagePicker.requestMediaLibraryPermissionsAsync).toHaveBeenCalled();
      });
    });
  });

  describe('Form Input Handling', () => {
    it('handles form inputs by using testID', async () => {
      const { getAllByTestId } = renderWithProviders(<AddProductScreen />, { store });

      await waitFor(() => {
        const textInputs = getAllByTestId('text-input-outlined');
        expect(textInputs.length).toBeGreaterThan(0);
      });

      const textInputs = getAllByTestId('text-input-outlined');
      const titleInput = textInputs[0]; // First input (title)
      
      await act(async () => {
        fireEvent.changeText(titleInput, 'Ceramic Vase');
      });

      expect(titleInput.props.value).toBe('Ceramic Vase');
    });

    it('handles tags input with placeholder', async () => {
      const { getByPlaceholderText } = renderWithProviders(<AddProductScreen />, { store });

      const tagsInput = getByPlaceholderText('ceramic, handmade, pottery');
      
      await act(async () => {
        fireEvent.changeText(tagsInput, 'ceramic, handmade, decorative');
      });

      expect(tagsInput.props.value).toBe('ceramic, handmade, decorative');
    });
  });

  describe('Image Management', () => {
    it('allows adding images via add button', async () => {
      const { getByText } = renderWithProviders(<AddProductScreen />, { store });

      const addImageButton = getByText('+');
      
      await act(async () => {
        fireEvent.press(addImageButton);
      });

      await waitFor(() => {
        // Should show image picker alert
        expect(mockAlert).toHaveBeenCalledWith(
          'Add Image',
          'Choose an option',
          expect.arrayContaining([
            expect.objectContaining({ text: 'Camera' }),
            expect.objectContaining({ text: 'Gallery' }),
            expect.objectContaining({ text: 'Cancel' })
          ])
        );
      });
    });
  });

  describe('Form Submission', () => {
    const fillValidForm = async (component) => {
      const { getAllByTestId } = component;

      await waitFor(() => {
        const textInputs = getAllByTestId('text-input-outlined');
        expect(textInputs.length).toBeGreaterThan(0);
      });

      const textInputs = getAllByTestId('text-input-outlined');
      
      await act(async () => {
        fireEvent.changeText(textInputs[0], 'Ceramic Vase'); // Title
        fireEvent.changeText(textInputs[1], 'Beautiful handcrafted ceramic vase'); // Description
        fireEvent.changeText(textInputs[2], '45.99'); // Price
        fireEvent.changeText(textInputs[3], 'Dinnerware'); // Category
        fireEvent.changeText(textInputs[4], '25'); // Stock quantity
      });
    };

    it('successfully creates product with valid data', async () => {
      const component = renderWithProviders(<AddProductScreen />, { store });
      const { getByText } = component;

      await fillValidForm(component);

      const createButton = getByText('Create Product');
      await act(async () => {
        fireEvent.press(createButton);
      });

      await waitFor(() => {
        expect(productService.createProduct).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Ceramic Vase',
            description: 'Beautiful handcrafted ceramic vase',
            price: 45.99,
            category: 'Dinnerware',
            stock_quantity: 25,
          })
        );
      });
    });

    it('shows loading state during submission', async () => {
      // Mock slow API response
      productService.createProduct.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ id: '1', success: true }), 1000))
      );

      const component = renderWithProviders(<AddProductScreen />, { store });
      const { getByText } = component;

      await fillValidForm(component);

      const createButton = getByText('Create Product');
      await act(async () => {
        fireEvent.press(createButton);
      });

      // Should show loading state
      expect(getByText('Creating Product...')).toBeTruthy();
    });

    it('handles product creation errors', async () => {
      productService.createProduct.mockRejectedValue(new Error('Server error'));

      const component = renderWithProviders(<AddProductScreen />, { store });
      const { getByText } = component;

      await fillValidForm(component);

      const createButton = getByText('Create Product');
      await act(async () => {
        fireEvent.press(createButton);
      });

      await waitFor(() => {
        expect(mockAlert).toHaveBeenCalledWith(
          'Error', 
          expect.stringMatching(/Failed to create product|Server error/)
        );
      });

      // Should not navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('Navigation', () => {
    it('navigates back when back button is pressed', () => {
      const { getByTestId } = renderWithProviders(<AddProductScreen />, { store });

      const backButton = getByTestId('icon-button');
      fireEvent.press(backButton);

      expect(mockGoBack).toHaveBeenCalled();
    });
  });
});