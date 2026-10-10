# Windows client boundary

The shared runtime/trainer contract currently runs through the Python package and CLI. A Windows installer and native UI are not yet implemented. The future client should preserve local state under the user's application data directory and install verified versioned packages without overwriting prior versions.
