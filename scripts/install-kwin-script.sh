#!/bin/bash
#
# Installation script for Shortcut Sage KWin Event Monitor
#
# This script installs the KWin script that monitors desktop events
# and sends them to the Shortcut Sage daemon via DBus.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KWIN_DIR="$PROJECT_ROOT/kwin"

# KWin scripts directory
KWIN_SCRIPTS_DIR="$HOME/.local/share/kwin/scripts"
SCRIPT_NAME="shortcut-sage-event-monitor"
INSTALL_DIR="$KWIN_SCRIPTS_DIR/$SCRIPT_NAME"

echo "=== Shortcut Sage KWin Script Installer ==="
echo ""

# Check if KDE Plasma is running
if [ -z "$KDE_SESSION_VERSION" ]; then
    echo -e "${YELLOW}Warning: KDE Plasma not detected. This script is designed for KDE Plasma.${NC}"
    echo "Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 1
    fi
fi

# Check if source files exist
if [ ! -f "$KWIN_DIR/event-monitor.js" ]; then
    echo -e "${RED}Error: event-monitor.js not found in $KWIN_DIR${NC}"
    exit 1
fi

if [ ! -f "$KWIN_DIR/metadata.json" ]; then
    echo -e "${RED}Error: metadata.json not found in $KWIN_DIR${NC}"
    exit 1
fi

# Create KWin scripts directory if it doesn't exist
echo "Creating KWin scripts directory..."
mkdir -p "$KWIN_SCRIPTS_DIR"

# Create installation directory
echo "Installing KWin script to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copy files
cp "$KWIN_DIR/event-monitor.js" "$INSTALL_DIR/"
cp "$KWIN_DIR/metadata.json" "$INSTALL_DIR/"

# Check if script is already enabled
if kreadconfig5 --file kwinrc --group Plugins --key "$SCRIPT_NAME"Enabled 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}Script is already enabled${NC}"
else
    # Enable the script
    echo "Enabling KWin script..."
    kwriteconfig5 --file kwinrc --group Plugins --key "${SCRIPT_NAME}Enabled" true
fi

# Reload KWin scripts
echo "Reloading KWin scripts..."
if command -v qdbus &> /dev/null; then
    qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true
elif command -v qdbus-qt5 &> /dev/null; then
    qdbus-qt5 org.kde.KWin /KWin reconfigure 2>/dev/null || true
else
    echo -e "${YELLOW}Warning: qdbus not found. Please restart KWin manually or log out/in.${NC}"
fi

echo ""
echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""
echo "The KWin event monitor is now installed and enabled."
echo ""
echo "To verify installation:"
echo "  1. Open KDE System Settings → Window Management → KWin Scripts"
echo "  2. Look for 'Shortcut Sage Event Monitor' in the list"
echo ""
echo "To test the script:"
echo "  1. Start the daemon: shortcut-sage daemon ~/.config/shortcut-sage"
echo "  2. Press Meta+Shift+S to send a test event"
echo "  3. Check daemon logs for the test event"
echo ""
echo "To uninstall:"
echo "  rm -rf $INSTALL_DIR"
echo "  kwriteconfig5 --file kwinrc --group Plugins --key ${SCRIPT_NAME}Enabled false"
echo ""
