#!/bin/bash
set -e

APP_NAME="Antigram"
BUILD_DIR="/Users/apple/Desktop/anto/openclaw-antigravity-bridge/build_mac"
DIST_DIR="/Users/apple/Desktop/anto/openclaw-antigravity-bridge/dist_mac"
DMG_NAME="Antigram-Installer.dmg"
DMG_PATH="/Users/apple/Desktop/anto/$DMG_NAME"

echo "⚡ Building macOS .app and .dmg for Antigram..."

rm -rf "$BUILD_DIR" "$DIST_DIR" "$DMG_PATH"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# Copy Icon
cp "/Users/apple/Desktop/anto/openclaw-antigravity-bridge/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"

# 1. Create Info.plist
cat <<EOF > "$CONTENTS_DIR/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>AntigramLauncher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.antigram.app</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 2. Create Launcher Binary Script
cat << 'EOF' > "$MACOS_DIR/AntigramLauncher"
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
/usr/local/bin/python3 "/Users/apple/Desktop/anto/openclaw-antigravity-bridge/app_gui.py"
EOF

chmod +x "$MACOS_DIR/AntigramLauncher"

# 3. Create DMG Staging folder with Applications symlink
DMG_STAGE="$BUILD_DIR/dmg_stage"
mkdir -p "$DMG_STAGE"
cp -R "$APP_BUNDLE" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

# 4. Create DMG using hdiutil
echo "📦 Packaging into DMG: $DMG_PATH"
hdiutil create -volname "Antigram" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG_PATH"

echo "✅ DMG Successfully Created at: $DMG_PATH"
