#!/usr/bin/env bash
set -e

echo "🗑️ Uninstalling ai-usage-cli..."

# Stop & disable systemd service
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop ai-usage-tray.service 2>/dev/null || true
    systemctl --user disable ai-usage-tray.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/ai-usage-tray.service"
    systemctl --user daemon-reload 2>/dev/null || true
fi

# Kill any running tray process
pkill -f "ai-usage-tray" 2>/dev/null || true

# Remove desktop entries and icons
rm -f "$HOME/.local/share/applications/ai-usage-tray.desktop"
rm -f "$HOME/.config/autostart/ai-usage-tray.desktop"
rm -f "$HOME/.local/share/icons/ai-usage.png"

# Uninstall binary
if command -v uv >/dev/null 2>&1; then
    uv tool uninstall ai-usage-cli 2>/dev/null || true
fi

echo "✅ Uninstalled successfully."
