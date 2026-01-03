# Maestro Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Install Maestro
```bash
npm run maestro:setup
source ~/.bashrc  # Linux only
```

### 2. Install Java 17 (if needed)
```bash
java -version  # Check if you have Java 17+
# If not, install it:
sudo apt install openjdk-17-jdk  # Linux
brew install openjdk@17          # macOS
```

### 3. Start Android Emulator
```bash
# Option A: Use Android Studio AVD Manager (GUI)
# Option B: Command line
emulator -list-avds              # List available emulators
emulator -avd Pixel_4_API_30     # Start specific emulator
```

### 4. Run Tests
```bash
# Quick test (emulator already running)
npm run maestro:quick

# Full test with auto-setup
npm run maestro:test
```

## 📱 Using Online Emulators

### Option 1: Android Studio Emulator (Recommended)
1. Open Android Studio
2. Tools → AVD Manager
3. Create/Start an emulator
4. Run: `npm run maestro:quick`

### Option 2: Command Line Emulator
```bash
# Check if emulator is running
adb devices

# If not, start one:
emulator -avd Pixel_4_API_30 &

# Wait for boot, then run tests
npm run maestro:quick
```

### Option 3: Genymotion (Cloud/Desktop)
1. Start Genymotion emulator
2. Verify with: `adb devices`
3. Run: `npm run maestro:quick`

## 🧪 Running Specific Tests

```bash
# Auth tests only
npm run maestro:auth

# Smoke tests only
npm run maestro:smoke

# Single test file
./scripts/maestro-quick-test.sh single maestro/tests/auth/login.yaml

# With debug output
npm run maestro:debug
```

## 🔍 Debugging Failed Tests

1. **Check screenshots**: Look in `maestro/` directory
2. **Run in debug mode**: `npm run maestro:debug`
3. **Use Maestro Studio**: `maestro studio` (interactive debugger)

## ⚠️ Common Issues & Fixes

### "No connected devices"
```bash
adb devices  # Should show your emulator
# If not, start emulator first
```

### "Element not found"
- App might not be installed
- TestID might be missing in app code
- Try using text selector instead of id

### "Java version error"
```bash
# Install Java 17
sudo apt update
sudo apt install openjdk-17-jdk
```

### "Maestro command not found"
```bash
# Add to PATH
export PATH="$HOME/.maestro/bin:$PATH"
source ~/.bashrc
```

## 📝 Writing Your First Test

Create `maestro/tests/my-test.yaml`:
```yaml
appId: com.ceramicapp
name: "My First Test"
---
- launchApp
- assertVisible: "Login"
- tapOn:
    id: "usernameInput"
- inputText: "test@example.com"
- takeScreenshot: "my-test"
```

Run it:
```bash
maestro test maestro/tests/my-test.yaml
```

## 🎯 Next Steps

1. Read full guide: [MAESTRO_GUIDE.md](./MAESTRO_GUIDE.md)
2. Explore example tests in `maestro/tests/`
3. Try Maestro Studio: `maestro studio`
4. Write your own tests!

## 💡 Pro Tips

- **Fast feedback**: Keep emulator running, use `npm run maestro:quick`
- **Debug visually**: Use `maestro studio` to find elements
- **Test locally first**: Ensure tests work before CI/CD
- **Use tags**: Organize tests with tags for easy filtering

Happy Testing! 🎉