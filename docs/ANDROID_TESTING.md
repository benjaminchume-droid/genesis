# Install Genesis on Android

This Android client embeds the actual Genesis Python runtime and starts it inside the app process. SQLite databases and research records live in the application's private files directory. The existing Genesis web UI is served only on device loopback at `127.0.0.1:8765`; the app does not expose the local server to the LAN.

## Download and install the test APK

Matching pushes build a debug APK in GitHub Actions.

1. Open the repository's Actions page: https://github.com/benjaminchume-droid/genesis/actions
2. Open the latest **Android APK** workflow run and wait for it to finish successfully.
3. Under **Artifacts**, download `genesis-android-debug`.
4. Extract the ZIP to obtain `app-debug.apk`.
5. Transfer the APK to the Android phone if needed.
6. Open the APK on the phone. If prompted, allow your file manager or browser to install unknown apps, then confirm installation.
7. Launch **Genesis** and wait for the embedded Python runtime and local server to start.

This is a debug build for controlled testing, not a Play Store release. Workflow artifacts are retained for 14 days. A signed release build and durable distribution process are not configured.

## Phone test checklist

- Confirm the home screen loads and status panels populate.
- Record an observation and verify it persists after force-closing and reopening the app.
- Add explicitly labelled learning examples, fit rules, and inspect prediction evidence.
- Create and search concepts and relations; inspect composed paths and conflicts.
- Search a public topic, open a result, inspect the source, and ingest it for review.
- Confirm candidate claims remain pending until explicitly reviewed.
- Enable airplane mode and confirm local features continue while web research fails gracefully.
- Force-stop and reopen the app; confirm the local database persists.
- Check battery/background behavior. The runtime is intended to run while the app is open, not as an always-on background service.

## Boundaries and known limitations

- Web browsing requires network connectivity but no paid user-supplied search API key. Keyless providers may rate-limit or change.
- The browser retrieves text and HTML; it is not a full Chromium automation engine and does not execute arbitrary webpage JavaScript.
- The APK is unsigned beyond the normal debug signing configuration. It is not prepared for Play Store or public production distribution.
- Do not change the local server bind address away from loopback.
- Treat the APK as testable only after the Android APK workflow succeeds. A green Python test suite does not validate Android packaging or runtime startup.

## Local build

Prerequisites: JDK 17, Android SDK Platform 35, Gradle 8.9, and the Chaquopy Android build dependencies. From the repository root:

```bash
mkdir -p clients/android/app/src/main/python
cp -R src/genesis clients/android/app/src/main/python/genesis
cd clients/android
gradle --no-daemon :app:assembleDebug
```

The APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Reporting a failure

Include Android version, device architecture (most current phones use `arm64-v8a`), workflow run URL, and the exact error. Do not attach private research databases or user data unless inspected and intentionally sanitized.
