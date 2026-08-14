#!/usr/bin/env node

// Workaround for cross-spawn global dependency issue
const path = require('path');
const { spawn } = require('child_process');

// Set up NODE_PATH to include both local node_modules and nvm global modules
const localNodeModules = path.join(__dirname, 'node_modules');
const nvmGlobalModules = '/home/tuanph/.nvm/versions/node/v20.13.1/lib/node_modules';
const existingNodePath = process.env.NODE_PATH || '';
const nodePath = [localNodeModules, nvmGlobalModules, existingNodePath].filter(Boolean).join(':');

console.log('🚀 Starting Expo with enhanced module resolution...');
console.log('📦 NODE_PATH:', nodePath);

// Start Expo with enhanced NODE_PATH
const expo = spawn('./node_modules/.bin/expo', ['start', '--clear'], {
  stdio: 'inherit',
  cwd: __dirname,
  env: {
    ...process.env,
    NODE_PATH: nodePath
  }
});

expo.on('close', (code) => {
  console.log(`\n✨ Expo exited with code ${code}`);
});

expo.on('error', (error) => {
  console.error('❌ Failed to start Expo:', error.message);
});