# Cyber-Hacker: Boulderflash (Android)

A cyberpunk-themed puzzle game for Android, built with Pygame-CE.

## Build

The APK is built automatically via GitHub Actions on every push to `main`.

### Manual build (Linux only)
```bash
pip install buildozer
buildozer android debug
```

## Install on device
```bash
adb install -r bin/*.apk
```

## Debug
```bash
adb logcat -s python:D
```
