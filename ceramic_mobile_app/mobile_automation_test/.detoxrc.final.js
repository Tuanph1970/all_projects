/** @type {Detox.DetoxConfig} */
module.exports = {
  testRunner: {
    args: {
      '$0': 'jest',
      config: 'e2e/jest.config.js'
    },
    jest: {
      setupTimeout: 120000
    }
  },
  behavior: {
    init: {
      exposeGlobals: true,
      reinstallApp: false // Faster - don't reinstall between tests
    },
    launchApp: 'manual', // We'll control app launch manually in tests
    cleanup: {
      shutdownDevice: false
    }
  },
  apps: {
    'android.debug': {
      type: 'android.apk',
      binaryPath: '../front_end/android/app/build/outputs/apk/debug/app-debug.apk',
      build: 'cd ../front_end && cd android && ./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug',
      reversePorts: [8002] // For API server access
    }
  },
  devices: {
    emulator: {
      type: 'android.emulator',
      device: {
        avdName: 'Pixel_3a_API_36_extension_level_17_x86_64'
      },
      headless: false, // Show the emulator
      gpuMode: 'auto'
    },
    attached: {
      type: 'android.attached',
      device: {
        adbName: '.*' // Any attached device/emulator
      }
    }
  },
  configurations: {
    'android.emu.debug': {
      device: 'attached', // Use currently running emulator
      app: 'android.debug',
      timeout: 120000
    }
  },
  artifacts: {
    rootDir: './artifacts',
    plugins: {
      screenshot: {
        shouldTakeAutomaticSnapshots: true,
        keepOnlyFailedTestsArtifacts: false,
        takeWhen: {
          testStart: false,
          testDone: true,
          appNotReady: true
        }
      },
      video: {
        enabled: false // Disable for speed
      },
      log: 'failing'
    }
  }
};
