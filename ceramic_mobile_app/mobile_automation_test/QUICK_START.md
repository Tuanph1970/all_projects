# Detox Quick Start Guide

## ✅ Setup Status: COMPLETE

All configuration is done. You're ready to run E2E tests!

## Running Tests (3 Simple Steps)

### 1. Start the Emulator
```bash
emulator -avd Pixel_3a_API_36_extension_level_17_x86_64 &
```

Or use Android Studio: **Tools → AVD Manager → Launch**

### 2. (Optional) Rebuild if you made code changes
```bash
npm run build:android
```

### 3. Run Tests
```bash
# Run all tests
npm run test:android

# Or run specific tests
npm run test:auth:android
```

## Available Commands

From `mobile_automation_test/` directory:

| Command | Description |
|---------|-------------|
| `./validate-setup.sh` | Check if everything is configured correctly |
| `npm run build:android` | Build Android app + test APK |
| `npm run test:android` | Run all E2E tests |
| `npm run test:auth:android` | Run authentication tests only |

## Test Files

Your test files are in `e2e/auth/`:
- `changePassword.test.js`
- `login.test.js`
- `logout.test.js`
- `register.test.js`
- `resetPassword.test.js`

## Troubleshooting

### Emulator not found?
```bash
# List available emulators
emulator -list-avds

# Use the correct one from the list
```

### Build errors?
```bash
# Clean and rebuild
cd ../front_end/android
./gradlew clean
./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug
```

### Tests failing?
```bash
# Make sure emulator is running
adb devices

# Rebuild the app
npm run build:android

# Run tests again
npm run test:android
```

## Documentation

- **DETOX_SETUP.md** - Complete setup guide and troubleshooting
- **validate-setup.sh** - Automated environment validation
- **DETOX_SETUP_SUMMARY.md** - Summary of all changes made

## Need Help?

1. Run `./validate-setup.sh` to check your setup
2. See **DETOX_SETUP.md** for detailed troubleshooting
3. Check emulator status: `adb devices`

---

**Happy Testing!** 🚀
