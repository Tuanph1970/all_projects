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
      // Reinstall app before all tests (clean state)
      reinstallApp: true
    },
    launchApp: 'auto',
    // Improved synchronization settings
    synchronization: {
      enabled: true,
      // Only disable for specific operations when needed
      intervalInMs: 500,
      maxAttempts: 10,
    }
  },
  apps: {
    'ios.debug': {
      type: 'ios.app',
      binaryPath: '../front_end/ios/build/Build/Products/Debug-iphonesimulator/CeramicMarketplace.app',
      build: 'cd ../front_end && xcodebuild -workspace ios/CeramicMarketplace.xcworkspace -scheme CeramicMarketplace -configuration Debug -sdk iphonesimulator -derivedDataPath ios/build'
    },
    'ios.release': {
      type: 'ios.app',
      binaryPath: '../front_end/ios/build/Build/Products/Release-iphonesimulator/CeramicMarketplace.app',
      build: 'cd ../front_end && xcodebuild -workspace ios/CeramicMarketplace.xcworkspace -scheme CeramicMarketplace -configuration Release -sdk iphonesimulator -derivedDataPath ios/build'
    },
    'android.debug': {
      type: 'android.apk',
      binaryPath: '../front_end/android/app/build/outputs/apk/debug/app-debug.apk',
      build: 'cd ../front_end && cd android && ./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug',
      // Improved Android settings
      reversePorts: [8002] // Reverse port for API server access
    },
    'android.release': {
      type: 'android.apk',
      binaryPath: '../front_end/android/app/build/outputs/apk/release/app-release.apk',
      build: 'cd ../front_end && cd android && ./gradlew assembleRelease assembleAndroidTest -DtestBuildType=release',
      reversePorts: [8002]
    }
  },
  devices: {
    simulator: {
      type: 'ios.simulator',
      device: {
        type: 'iPhone 14'
      }
    },
    emulator: {
      type: 'android.emulator',
      device: {
        avdName: 'Pixel_3a_API_36_extension_level_17_x86_64'
      },
      // Improved Android emulator settings
      gpuMode: 'auto',
      headless: false,
      readonly: false
    },
    // Real device configurations
    'ios.device': {
      type: 'ios.device',
      device: {
        name: 'iPhone' // Will use any connected iPhone
      }
    },
    'android.device': {
      type: 'android.attached',
      device: {
        adbName: '.*' // Will use any connected Android device
      }
    }
  },
  configurations: {
    'ios.sim.debug': {
      device: 'simulator',
      app: 'ios.debug'
    },
    'ios.sim.release': {
      device: 'simulator',
      app: 'ios.release'
    },
    'android.emu.debug': {
      device: 'emulator',
      app: 'android.debug',
      timeout: 120000
    },
    'android.emu.release': {
      device: 'emulator',
      app: 'android.release',
      timeout: 120000
    },
    // Real device configurations
    'ios.device.debug': {
      device: 'ios.device',
      app: 'ios.debug',
      artifacts: {
        rootDir: './artifacts/ios-device',
        plugins: {
          screenshot: 'failing',
          video: 'failing',
          log: 'failing'
        }
      }
    },
    'android.device.debug': {
      device: 'android.device',
      app: 'android.debug',
      timeout: 120000,
      artifacts: {
        rootDir: './artifacts/android-device',
        plugins: {
          screenshot: 'failing',
          video: 'failing',
          log: 'failing'
        }
      }
    }
  },
  // Artifact configuration for debugging
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
        enabled: false, // Enable for debugging, disable for speed
        keepOnlyFailedTestsArtifacts: true
      },
      log: 'failing'
    }
  }
};
