#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Installing ai-usage-cli from: $DIR"

# 1. Check Python tool manager
if command -v uv >/dev/null 2>&1; then
    echo "📦 Installing global binaries via uv tool..."
    uv tool install --editable "$DIR" --force
else
    echo "📦 Installing global binaries via pip..."
    pip install -e "$DIR"
fi

# 2. Install Icon
mkdir -p "$HOME/.local/share/icons"
cp "$DIR/assets/ai-usage.png" "$HOME/.local/share/icons/ai-usage.png"
echo "🎨 Icon installed to ~/.local/share/icons/ai-usage.png"

# 3. Install Desktop Launcher
mkdir -p "$HOME/.local/share/applications" "$HOME/.config/autostart"
cp "$DIR/assets/ai-usage-tray.desktop" "$HOME/.local/share/applications/ai-usage-tray.desktop"
cp "$DIR/assets/ai-usage-tray.desktop" "$HOME/.config/autostart/ai-usage-tray.desktop"
echo "🖥️ Desktop entry installed to applications & autostart"

# 4. Install & Start Systemd User Service
if command -v systemctl >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/systemd/user"
    cp "$DIR/assets/ai-usage-tray.service" "$HOME/.config/systemd/user/ai-usage-tray.service"
    systemctl --user daemon-reload
    systemctl --user enable ai-usage-tray.service
    systemctl --user restart ai-usage-tray.service
    echo "⚡ Systemd user service enabled and started!"
fi

echo ""
echo "🎉 Installation complete!"
echo "• Run CLI: ai-usage"
echo "• Tray Status: systemctl --user status ai-usage-tray"
echo "• Tray Logs: journalctl --user -u ai-usage-tray -f"
