import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

const BOOKMARKS_STORAGE_KEY = '@mathematics:bookmarks';

// Load bookmarks from storage
const loadBookmarks = async () => {
  try {
    const storedBookmarks = await SecureStore.getItemAsync(BOOKMARKS_STORAGE_KEY);
    return storedBookmarks ? JSON.parse(storedBookmarks) : [];
  } catch (error) {
    console.error('Failed to load bookmarks:', error);
    return [];
  }
};

// Save bookmarks to storage
const saveBookmarks = async (bookmarks) => {
  try {
    await SecureStore.setItemAsync(BOOKMARKS_STORAGE_KEY, JSON.stringify(bookmarks));
  } catch (error) {
    console.error('Failed to save bookmarks:', error);
  }
};

// Async thunk to add bookmark
export const addBookmark = createAsyncThunk(
  'bookmarks/add',
  async (solution, { getState, rejectWithValue }) => {
    try {
      const { bookmarks } = getState();
      
      // Check if already bookmarked
      if (bookmarks.items.some(b => b.id === solution.id)) {
        return rejectWithValue('Already bookmarked');
      }

      const bookmark = {
        id: solution.id,
        problemId: solution.problemId,
        title: solution.title || 'Math Problem',
        category: solution.category || 'General',
        difficulty: solution.difficulty || 'Medium',
        solutionSteps: solution.steps?.length || 0,
        confidence: solution.confidence,
        bookmarkedAt: new Date().toISOString(),
        lastViewedAt: new Date().toISOString(),
        notes: '',
      };

      const updatedBookmarks = [bookmark, ...bookmarks.items];
      await saveBookmarks(updatedBookmarks);
      
      return bookmark;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

// Async thunk to remove bookmark
export const removeBookmark = createAsyncThunk(
  'bookmarks/remove',
  async (bookmarkId, { getState }) => {
    try {
      const { bookmarks } = getState();
      const updatedBookmarks = bookmarks.items.filter(b => b.id !== bookmarkId);
      await saveBookmarks(updatedBookmarks);
      
      return bookmarkId;
    } catch (error) {
      console.error('Failed to remove bookmark:', error);
      throw error;
    }
  }
);

// Async thunk to update bookmark notes
export const updateBookmarkNotes = createAsyncThunk(
  'bookmarks/updateNotes',
  async ({ bookmarkId, notes }, { getState }) => {
    try {
      const { bookmarks } = getState();
      const updatedBookmarks = bookmarks.items.map(b =>
        b.id === bookmarkId ? { ...b, notes, updatedAt: new Date().toISOString() } : b
      );
      await saveBookmarks(updatedBookmarks);
      
      return { bookmarkId, notes };
    } catch (error) {
      console.error('Failed to update bookmark notes:', error);
      throw error;
    }
  }
);

// Async thunk to update last viewed
export const updateLastViewed = createAsyncThunk(
  'bookmarks/updateLastViewed',
  async (bookmarkId, { getState }) => {
    try {
      const { bookmarks } = getState();
      const updatedBookmarks = bookmarks.items.map(b =>
        b.id === bookmarkId ? { ...b, lastViewedAt: new Date().toISOString() } : b
      );
      await saveBookmarks(updatedBookmarks);
      
      return bookmarkId;
    } catch (error) {
      console.error('Failed to update last viewed:', error);
    }
  }
);

// Async thunk to load bookmarks
export const loadBookmarksThunk = createAsyncThunk(
  'bookmarks/load',
  async () => {
    return await loadBookmarks();
  }
);

const initialState = {
  items: [],
  isLoading: false,
  error: null,
  lastUpdated: null,
};

const bookmarkSlice = createSlice({
  name: 'bookmarks',
  initialState,
  reducers: {
    clearBookmarks: (state) => {
      state.items = [];
      state.error = null;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Add bookmark
      .addCase(addBookmark.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(addBookmark.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items.unshift(action.payload);
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(addBookmark.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Remove bookmark
      .addCase(removeBookmark.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(removeBookmark.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = state.items.filter(b => b.id !== action.payload);
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(removeBookmark.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      
      // Update notes
      .addCase(updateBookmarkNotes.fulfilled, (state, action) => {
        const { bookmarkId, notes } = action.payload;
        const bookmark = state.items.find(b => b.id === bookmarkId);
        if (bookmark) {
          bookmark.notes = notes;
          bookmark.updatedAt = new Date().toISOString();
        }
        state.lastUpdated = new Date().toISOString();
      })
      
      // Update last viewed
      .addCase(updateLastViewed.fulfilled, (state, action) => {
        const bookmark = state.items.find(b => b.id === action.payload);
        if (bookmark) {
          bookmark.lastViewedAt = new Date().toISOString();
        }
        state.lastUpdated = new Date().toISOString();
      })
      
      // Load bookmarks
      .addCase(loadBookmarksThunk.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loadBookmarksThunk.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(loadBookmarksThunk.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  },
});

export const { clearBookmarks, setError } = bookmarkSlice.actions;

// Selectors
export const selectBookmarks = (state) => state.bookmarks.items;
export const selectIsBookmarked = (state, solutionId) => 
  state.bookmarks.items.some(b => b.id === solutionId);
export const selectBookmarkById = (state, solutionId) =>
  state.bookmarks.items.find(b => b.id === solutionId);
export const selectBookmarksByCategory = (state, category) =>
  state.bookmarks.items.filter(b => b.category === category);
export const selectRecentBookmarks = (state, limit = 5) =>
  state.bookmarks.items
    .sort((a, b) => new Date(b.lastViewedAt) - new Date(a.lastViewedAt))
    .slice(0, limit);
export const selectBookmarksLoading = (state) => state.bookmarks.isLoading;
export const selectBookmarksError = (state) => state.bookmarks.error;

export default bookmarkSlice.reducer;
