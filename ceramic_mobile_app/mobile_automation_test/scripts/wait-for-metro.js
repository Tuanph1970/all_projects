#!/usr/bin/env node

/**
 * Wait for Metro bundler to be ready before running E2E tests
 * This script polls the Metro status endpoint until it's running
 */

const http = require('http');

const METRO_URL = 'http://localhost:8081/status';
const MAX_RETRIES = 60; // Maximum retries (60 * 2s = 120s timeout)
const RETRY_INTERVAL = 2000; // 2 seconds between retries

function checkMetroStatus() {
  return new Promise((resolve) => {
    const req = http.get(METRO_URL, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        resolve(data.includes('packager-status:running'));
      });
    });

    req.on('error', () => {
      resolve(false);
    });

    req.setTimeout(5000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForMetro() {
  console.log('⏳ Waiting for Metro bundler to start...');

  for (let i = 0; i < MAX_RETRIES; i++) {
    const isRunning = await checkMetroStatus();

    if (isRunning) {
      console.log('✅ Metro bundler is ready!');
      process.exit(0);
    }

    if (i % 5 === 0 && i > 0) {
      console.log(`   Still waiting... (${i * 2}s elapsed)`);
    }

    await new Promise((resolve) => setTimeout(resolve, RETRY_INTERVAL));
  }

  console.error('❌ Metro bundler failed to start within timeout');
  process.exit(1);
}

waitForMetro();
