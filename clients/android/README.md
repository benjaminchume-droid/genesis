# Android client boundary

The shared runtime is currently Python and does not yet produce an APK. A native Android client must implement the same contribution/release schema, use app-private storage, expose per-item export consent, and respect Android background execution limits. It must not silently sync local observations.
