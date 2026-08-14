const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Add resolver configuration for path aliases
config.resolver.alias = {
  '@': path.resolve(__dirname, './src'),
  '@components': path.resolve(__dirname, './src/components'),
  '@screens': path.resolve(__dirname, './src/screens'),
  '@navigation': path.resolve(__dirname, './src/navigation'),
  '@services': path.resolve(__dirname, './src/services'),
  '@store': path.resolve(__dirname, './src/store'),
  '@utils': path.resolve(__dirname, './src/utils'),
  '@constants': path.resolve(__dirname, './src/constants'),
  '@types': path.resolve(__dirname, './src/types'),
  '@assets': path.resolve(__dirname, './assets'),
};

module.exports = config;