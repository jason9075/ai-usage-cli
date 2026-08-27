# AI Usage CLI & Ubuntu Tray Monitor 🤖📊

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Linux](https://img.shields.io/badge/OS-Linux%20%2F%20Ubuntu-orange.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A unified CLI and Linux / Ubuntu Top Bar system tray monitor for tracking your AI coding assistant usage quotas in real-time.

Supports **Google Antigravity (AGY)**, **Claude Code**, **OpenAI Codex**, **Gemini Code Assist**, **GitHub Copilot**, and **z.ai (GLM)**.

---

## ✨ Features

- 🖥️ **Ubuntu Top Bar Tray Monitor**: Native AppIndicator / StatusNotifierItem on Ubuntu GNOME top panel.
- 🖱️ **Mouse Hover Tooltip**: Move your mouse over the top panel icon for an instant multi-line quota summary.
- 🔋 **Proportional Progress Bars**: Visual bars where filled blocks represent remaining quota percentage (`% left`).
- 🤖 **Multi-Provider Support**:
  - **Google Antigravity (AGY)**: Automatic credential discovery from Linux SecretStorage / macOS Keychain, model tier separation (`Flash` vs `Claude & Pro`), and 5h rolling session turn tracking.
  - **Claude Code**: OAuth token inspection, Session (5h) & Weekly (7d) rate limits, Linux identity parsing (`[Team]` / `[Pro]`), and monthly extra cost tracking.
  - **OpenAI Codex**: OAuth token refresh, 5h & 7d window limits.
  - **Gemini Code Assist**: Token refresh & rate limits.
  - **GitHub Copilot & z.ai**: Quota and API status.
- ⚡ **Auto-start & Systemd Integration**: Includes `systemd --user` unit and `.desktop` autostart launcher.
- 📋 **Click Actions**: Instant refresh, one-click copy summary with desktop notifications, and direct config editing.

---

## 📸 CLI Output Preview

```text
$ ai-usage

  Antigravity (AGY)  (oauth)  [Standard]  jason9075@gmail.com
    Flash (Gemini 3.7 Flash (High))   94.0% left  [███████████████████░]  resets in 4h44m
    Claude & Pro models              100.0% left  [████████████████████]

  Claude  (oauth)  [Team]
    Session (5h)                      64.0% left  [█████████████░░░░░░░]  resets in 3h43m
    Weekly (7d)                       65.0% left  [█████████████░░░░░░░]  resets in 4d5h13m
    cost: $50.28 / $51.00 (monthly)

  Codex  (oauth)  [plus]  ajle2721@gmail.com
    Session (5h)                      46.0% left  [█████████░░░░░░░░░░░]  resets in 4h35m
    Weekly (7d)                       77.0% left  [███████████████░░░░░]  resets in 5d4h42m
```

---

## 🖱️ Ubuntu Top Bar Hover Tooltip Preview

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Activities          Aug 27 17:51          [🤖] [📶] [🔋] [⚙️]  │
└────────────────────────────────────────────────────────────────────────┘
                                              │
                      ┌───────────────────────┴─────────────────────────┐
                      │ 🤖 AI Usage Quotas                              │
                      │ ──────────────────────────                      │
                      │ Antigravity (AGY) [Standard]                    │
                      │   • Flash (Gemini 3.7 Flash): 94% left (4h44m)  │
                      │   • Claude & Pro models: 100% left              │
                      │ Claude [Team]                                   │
                      │   • Session (5h): 64% left (3h43m)              │
                      │   • Weekly (7d): 65% left (4d5h)                │
                      │   • Cost: $50.28 / $51.00                       │
                      │ Codex [plus]                                    │
                      │   • Session (5h): 46% left (4h35m)              │
                      │   • Weekly (7d): 77% left (5d4h)                │
                      │ 🕒 Updated: 17:51:22                            │
                      └─────────────────────────────────────────────────┘
```

---

## 🚀 Installation & Quick Start

### 1. One-Command Setup

```bash
cd /home/jason9075/projects/ai-usage-cli
./install.sh
```

`install.sh` will:
1. Install `ai-usage` and `ai-usage-tray` globally using `uv tool install`.
2. Install high-res app icon to `~/.local/share/icons/ai-usage.png`.
3. Register application launcher and auto-start entries.
4. Enable and launch the `systemd --user` background tray monitor.

### 2. Manual Installation via `uv`

```bash
uv tool install --editable /home/jason9075/projects/ai-usage-cli --force
```

---

## 📖 Usage

### CLI Commands

```bash
# Check all enabled providers
ai-usage

# Query specific providers
ai-usage -p agy claude
ai-usage -p codex

# Include disabled providers
ai-usage -a

# Output as JSON (useful for scripts & statusbars)
ai-usage --json

# Plain text output (no colors / unicode)
ai-usage --plain

# Start system tray monitor directly in foreground
ai-usage --tray
# or
ai-usage-tray -i 300
```

### Systemd Service Management

```bash
# Check tray monitor status
systemctl --user status ai-usage-tray

# Restart tray monitor
systemctl --user restart ai-usage-tray

# View live tray logs
journalctl --user -u ai-usage-tray -f

# Stop tray monitor
systemctl --user stop ai-usage-tray
```

---

## ⚙️ Configuration

Settings are stored in `~/.codexbar/config.json`:

```json
{
  "providers": {
    "agy": {
      "enabled": true
    },
    "claude": {
      "enabled": true
    },
    "codex": {
      "enabled": true
    },
    "gemini": {
      "enabled": true
    },
    "copilot": {
      "enabled": false
    },
    "zai": {
      "enabled": false,
      "apiKey": "YOUR_Z_AI_KEY"
    }
  }
}
```

---

## 🏗️ Project Architecture

```text
ai-usage-cli/
├── ai_usage/
│   ├── __init__.py
│   ├── main.py              # CLI parser and runner
│   ├── tray.py              # Native DBus StatusNotifierItem & DBusMenu daemon
│   ├── display.py           # Rich terminal renderer & progress bars
│   ├── config.py            # CodexBar config loader
│   └── providers/
│       ├── __init__.py      # Provider registry
│       ├── base.py          # Abstract provider base class
│       ├── agy.py           # Antigravity (Keyring, Model tiers, Session stats)
│       ├── claude.py        # Claude Code OAuth & Linux credentials
│       ├── codex.py         # OpenAI Codex OAuth & token refresh
│       ├── gemini.py        # Gemini Code Assist OAuth
│       ├── copilot.py       # GitHub Copilot
│       └── zai.py           # z.ai GLM API
├── assets/
│   ├── ai-usage.png         # 512x512 App icon
│   ├── ai-usage-tray.desktop# Desktop launcher
│   └── ai-usage-tray.service# Systemd user unit
├── install.sh               # One-click installation script
├── uninstall.sh             # Uninstallation script
├── Makefile                 # Common build/dev targets
├── pyproject.toml           # Project dependencies & tool scripts
└── README.md                # Documentation
```

---

## 📄 License

MIT License. Copyright (c) 2026.
