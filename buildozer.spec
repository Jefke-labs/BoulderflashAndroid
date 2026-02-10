[app]

# (str) Title of your application
title = CyberHacker

# (str) Package name
package.name = boulderflash

# (str) Package domain (usually com.yourname.project)
package.domain = org.cyberhacker

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,json,wav,mp3

# (list) Source files to exclude
source.exclude_exts = spec

# (list) List of directory to exclude
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# Use pygame recipe (not pygame-ce pip package) to build from SDL2 for Android
requirements = python3,pygame,sdl2,sdl2_image,sdl2_mixer,sdl2_ttf,android

# (list) Supported orientations
orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (bool) If True, then automatically accept SDK license agreements.
android.accept_sdk_license = True

# (str) The Android arch to build for
# Only arm64-v8a for modern phones (no x86/x86_64!)
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (OS >= 6.0)
android.allow_backup = True

# (str) python-for-android branch to use
# 'master' is stable and well-tested with pygame-ce
p4a.branch = master

# (str) Bootstrap to use for the build
p4a.bootstrap = sdl2

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = off, 1 = on)
warn_on_root = 1
