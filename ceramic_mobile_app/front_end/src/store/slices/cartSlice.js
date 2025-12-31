import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { cartService } from '../../services/cartService.js';

const initialState = {
  cart: null,
  loading: false,
  error: null,
  itemCount: 0,
  totalQuantity: 0,
};

// Async thunks
export const fetchCart = createAsyncThunk(
  'cart/fetchCart',
  async (_, { rejectWithValue }) => {
    try {
      const cart = await cartService.getCart();
      return cart;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to fetch cart');
    }
  }
);

export const addToCart = createAsyncThunk(
  'cart/addToCart',
  async (request, { rejectWithValue, dispatch }) => {
    try {
      const result = await cartService.addToCart(request);
      // Refresh cart after adding item
      dispatch(fetchCart());
      return result;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to add item to cart');
    }
  }
);

export const updateCartItem = createAsyncThunk(
  'cart/updateCartItem',
  async ({ itemId, request }, { rejectWithValue, dispatch }) => {
    try {
      const result = await cartService.updateCartItem(itemId, request);
      // Refresh cart after updating item
      dispatch(fetchCart());
      return result;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to update cart item');
    }
  }
);

export const removeFromCart = createAsyncThunk(
  'cart/removeFromCart',
  async (itemId, { rejectWithValue, dispatch }) => {
    try {
      const result = await cartService.removeFromCart(itemId);
      // Refresh cart after removing item
      dispatch(fetchCart());
      return result;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to remove item from cart');
    }
  }
);

export const clearCart = createAsyncThunk(
  'cart/clearCart',
  async (_, { rejectWithValue, dispatch }) => {
    try {
      const result = await cartService.clearCart();
      // Refresh cart after clearing
      dispatch(fetchCart());
      return result;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to clear cart');
    }
  }
);

export const fetchCartCount = createAsyncThunk(
  'cart/fetchCartCount',
  async (_, { rejectWithValue }) => {
    try {
      const count = await cartService.getCartCount();
      return count;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to fetch cart count');
    }
  }
);

export const checkout = createAsyncThunk(
  'cart/checkout',
  async (shippingAddress, { rejectWithValue, dispatch }) => {
    try {
      const order = await cartService.checkout(shippingAddress);
      // Refresh cart after successful checkout (should be empty)
      dispatch(fetchCart());
      return order;
    } catch (error) {
      return rejectWithValue(error?.response?.data?.detail || 'Failed to checkout');
    }
  }
);

const cartSlice = createSlice({
  name: 'cart',
  initialState,
  reducers: {
    clearCartState: (state) => {
      state.cart = null;
      state.error = null;
      state.itemCount = 0;
      state.totalQuantity = 0;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch cart
    builder
      .addCase(fetchCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCart.fulfilled, (state, action) => {
        state.loading = false;
        state.cart = action.payload;
        state.itemCount = action.payload?.items?.length || 0;
        state.totalQuantity = action.payload?.items?.reduce((total, item) => total + item.quantity, 0) || 0;
      })
      .addCase(fetchCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Add to cart
      .addCase(addToCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(addToCart.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(addToCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Update cart item
      .addCase(updateCartItem.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateCartItem.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(updateCartItem.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Remove from cart
      .addCase(removeFromCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(removeFromCart.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(removeFromCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Clear cart
      .addCase(clearCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(clearCart.fulfilled, (state) => {
        state.loading = false;
        state.cart = null;
        state.itemCount = 0;
        state.totalQuantity = 0;
      })
      .addCase(clearCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      // Fetch cart count
      .addCase(fetchCartCount.fulfilled, (state, action) => {
        state.itemCount = action.payload;
      })
      
      // Checkout
      .addCase(checkout.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(checkout.fulfilled, (state) => {
        state.loading = false;
        state.cart = null;
        state.itemCount = 0;
        state.totalQuantity = 0;
      })
      .addCase(checkout.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { clearCartState, clearError } = cartSlice.actions;
export default cartSlice.reducer;