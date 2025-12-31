# Assets Directory

This directory contains the app's assets including icons, splash screens, and other static files.

## Required Files

For a complete Expo setup, you should add:

- `icon.png` - App icon (1024x1024 px)
- `splash.png` - Splash screen image (1284x2778 px for iPhone 12 Pro Max)
- `adaptive-icon.png` - Android adaptive icon (1024x1024 px)
- `favicon.png` - Web favicon (48x48 px)

## Generating Assets

You can generate all required assets from a single high-resolution icon using:

```bash
npx expo install @expo/configure-splash-screen
npx configure-splash-screen
```

## File Specifications

### Icon (icon.png)
- Size: 1024x1024 pixels
- Format: PNG
- Background: Opaque (no transparency for iOS)

### Splash Screen (splash.png)
- Size: 1284x2778 pixels (iPhone 12 Pro Max)
- Format: PNG
- The splash screen will be automatically resized for different devices

### Adaptive Icon (adaptive-icon.png)
- Size: 1024x1024 pixels
- Format: PNG
- For Android adaptive icons
- Make sure important content is within the safe zone (center circle)

### Favicon (favicon.png)
- Size: 48x48 pixels
- Format: PNG
- For web builds