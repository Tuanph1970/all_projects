import React from 'react';
import { fireEvent, waitFor, act } from '@testing-library/react-native';
import { renderWithProviders, createMockStore } from '../../../__tests__/utils/testUtils';
import { ProductManagementScreen } from '../ProductManagementScreen';
import sellerService from '../../../services/sellerService';

// Mock services
jest.mock('../../../services/sellerService', () => ({
  getProductsForManagement: jest.fn(),
  bulkUpdateStatus: jest.fn(),
  bulkUpdateFeatured: jest.fn(),
  deleteProduct: jest.fn(),
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

const mockProducts = [
  {
    id: '1',
    name: 'Ceramic Vase',
    sku: 'VASE001',
    price: 45.99,
    is_active: true,
    is_featured: true,
    stock_status: 'in_stock',
    quantity_available: 25,
    sales: {
      orders: 15,
      revenue: 689.85
    },
    reviews: {
      avg_rating: 4.5,
      count: 8
    }
  },
  {
    id: '2',
    name: 'Ceramic Bowl Set',
    sku: 'BOWL002',
    price: 89.99,
    is_active: true,
    is_featured: false,
    stock_status: 'low_stock',
    quantity_available: 3,
    sales: {
      orders: 8,
      revenue: 719.92
    },
    reviews: {
      avg_rating: 4.8,
      count: 12
    }
  },
  {
    id: '3',
    name: 'Decorative Plate',
    sku: null,
    price: 25.50,
    is_active: false,
    is_featured: false,
    stock_status: 'out_of_stock',
    quantity_available: 0,
    sales: {
      orders: 3,
      revenue: 76.50
    },
    reviews: {
      avg_rating: 3.5,
      count: 2
    }
  }
];

describe('ProductManagementScreen', () => {
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

    // Mock successful API response by default
    sellerService.getProductsForManagement.mockResolvedValue({
      products: mockProducts,
      pagination: {
        has_next: false,
        page: 1,
        per_page: 20,
        total: 3
      }
    });
  });

  describe('Basic Rendering', () => {
    it('renders product management screen correctly', async () => {
      const { getByText, getByPlaceholderText } = renderWithProviders(<ProductManagementScreen />, { store });

      expect(getByText('Product Management')).toBeTruthy();
      expect(getByPlaceholderText('Search products...')).toBeTruthy();
    });

    it('loads products on mount', async () => {
      renderWithProviders(<ProductManagementScreen />, { store });
      
      await waitFor(() => {
        expect(sellerService.getProductsForManagement).toHaveBeenCalledWith({
          page: 1,
          per_page: 20,
          search: '',
          status: 'active',
          stock_status: 'all',
          sort_by: 'created_at',
          sort_order: 'desc',
          low_stock_threshold: 10
        });
      });
    });

    it('displays products after loading', async () => {
      const { getByText } = renderWithProviders(<ProductManagementScreen />, { store });

      await waitFor(() => {
        expect(getByText('Ceramic Vase')).toBeTruthy();
        expect(getByText('Ceramic Bowl Set')).toBeTruthy();
        expect(getByText('Decorative Plate')).toBeTruthy();
      });
    });
  });

  describe('Search Functionality', () => {
    it('handles search input', async () => {
      const { getByPlaceholderText } = renderWithProviders(<ProductManagementScreen />, { store });

      const searchInput = getByPlaceholderText('Search products...');
      
      await act(async () => {
        fireEvent.changeText(searchInput, 'vase');
      });

      await waitFor(() => {
        expect(sellerService.getProductsForManagement).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'vase'
          })
        );
      });
    });
  });

  describe('Product Display', () => {
    it('displays product information correctly', async () => {
      const { getByText } = renderWithProviders(<ProductManagementScreen />, { store });

      await waitFor(() => {
        // Product names
        expect(getByText('Ceramic Vase')).toBeTruthy();
        expect(getByText('Ceramic Bowl Set')).toBeTruthy();
        
        // Prices
        expect(getByText('$45.99')).toBeTruthy();
        expect(getByText('$89.99')).toBeTruthy();
        
        // SKUs
        expect(getByText('SKU: VASE001')).toBeTruthy();
        expect(getByText('SKU: BOWL002')).toBeTruthy();
        expect(getByText('SKU: N/A')).toBeTruthy(); // For product without SKU
      });
    });

    it('displays featured badge for featured products', async () => {
      const { getByText } = renderWithProviders(<ProductManagementScreen />, { store });

      await waitFor(() => {
        expect(getByText('Featured')).toBeTruthy();
      });
    });
  });

  describe('Navigation', () => {
    it('navigates to add product screen when FAB is pressed', async () => {
      const { getByTestId } = renderWithProviders(<ProductManagementScreen />, { store });

      await waitFor(() => {
        const fab = getByTestId('fab');
        fireEvent.press(fab);
      });

      expect(mockNavigate).toHaveBeenCalledWith('AddProduct');
    });
  });

  describe('Empty States', () => {
    it('displays empty state when no products found', async () => {
      sellerService.getProductsForManagement.mockResolvedValue({
        products: [],
        pagination: { has_next: false, page: 1, total: 0 }
      });

      const { getByText } = renderWithProviders(<ProductManagementScreen />, { store });

      await waitFor(() => {
        expect(getByText('No products found')).toBeTruthy();
        expect(getByText('Add your first product to get started')).toBeTruthy();
      });
    });

    it('displays search-specific empty state', async () => {
      sellerService.getProductsForManagement.mockResolvedValue({
        products: [],
        pagination: { has_next: false, page: 1, total: 0 }
      });

      const { getByText, getByPlaceholderText } = renderWithProviders(<ProductManagementScreen />, { store });

      // Search for something
      const searchInput = getByPlaceholderText('Search products...');
      await act(async () => {
        fireEvent.changeText(searchInput, 'nonexistent');
      });

      await waitFor(() => {
        expect(getByText('No products found')).toBeTruthy();
        expect(getByText('Try adjusting your search terms')).toBeTruthy();
      });
    });
  });
});