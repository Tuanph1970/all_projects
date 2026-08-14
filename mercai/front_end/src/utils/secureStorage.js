import * as SecureStore from 'expo-secure-store';

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  TOKEN_TYPE: 'token_type',
  EXPIRES_IN: 'expires_in',
};

class SecureStorage {
  async setTokens(tokens) {
    try {
      await Promise.all([
        SecureStore.setItemAsync(STORAGE_KEYS.ACCESS_TOKEN, tokens.accessToken),
        SecureStore.setItemAsync(STORAGE_KEYS.REFRESH_TOKEN, tokens.refreshToken),
        SecureStore.setItemAsync(STORAGE_KEYS.TOKEN_TYPE, tokens.tokenType),
        SecureStore.setItemAsync(STORAGE_KEYS.EXPIRES_IN, tokens.expiresIn.toString()),
      ]);
    } catch (error) {
      console.error('Error storing tokens:', error);
      throw error;
    }
  }

  async getTokens() {
    try {
      const [accessToken, refreshToken, tokenType, expiresIn] = await Promise.all([
        SecureStore.getItemAsync(STORAGE_KEYS.ACCESS_TOKEN),
        SecureStore.getItemAsync(STORAGE_KEYS.REFRESH_TOKEN),
        SecureStore.getItemAsync(STORAGE_KEYS.TOKEN_TYPE),
        SecureStore.getItemAsync(STORAGE_KEYS.EXPIRES_IN),
      ]);

      if (!accessToken || !refreshToken || !tokenType || !expiresIn) {
        return null;
      }

      return {
        accessToken,
        refreshToken,
        tokenType,
        expiresIn: parseInt(expiresIn, 10),
      };
    } catch (error) {
      console.error('Error retrieving tokens:', error);
      return null;
    }
  }

  async clearTokens() {
    try {
      await Promise.all([
        SecureStore.deleteItemAsync(STORAGE_KEYS.ACCESS_TOKEN),
        SecureStore.deleteItemAsync(STORAGE_KEYS.REFRESH_TOKEN),
        SecureStore.deleteItemAsync(STORAGE_KEYS.TOKEN_TYPE),
        SecureStore.deleteItemAsync(STORAGE_KEYS.EXPIRES_IN),
      ]);
    } catch (error) {
      console.error('Error clearing tokens:', error);
      // Don't throw error for cleanup operations
    }
  }

  async setItem(key, value) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch (error) {
      console.error(`Error storing ${key}:`, error);
      throw error;
    }
  }

  async getItem(key) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch (error) {
      console.error(`Error retrieving ${key}:`, error);
      return null;
    }
  }

  async removeItem(key) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch (error) {
      console.error(`Error removing ${key}:`, error);
      // Don't throw error for cleanup operations
    }
  }

  async hasTokens() {
    const tokens = await this.getTokens();
    return tokens !== null;
  }
}

export const secureStorage = new SecureStorage();