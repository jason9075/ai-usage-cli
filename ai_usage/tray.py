from __future__ import annotations

import argparse
import asyncio
import os
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    from dbus_fast.aio import MessageBus
    from dbus_fast.service import ServiceInterface, dbus_property, method, signal, PropertyAccess
    from dbus_fast import Variant, Message, MessageType
except ImportError:
    print(
        "Error: dbus-fast is required for the Linux system tray feature.\n"
        "Please run: pip install dbus-fast (or uv add dbus-fast)",
        file=sys.stderr,
    )
    sys.exit(1)

from .main import fetch_all
from .providers.base import UsageResult


def format_tooltip(results: list[UsageResult], updated_at: str) -> str:
    """Format a clean, readable multi-line tooltip for mouse hover."""
    lines = ["🤖 AI Usage Quotas", "──────────────────────────"]
    has_active_data = False

    for r in results:
        if r.error and not r.windows:
            continue

        header_parts = [r.provider]
        if r.plan:
            header_parts.append(f"[{r.plan}]")
        if r.email:
            header_parts.append(f"({r.email})")
        lines.append(" ".join(header_parts))

        for w in r.windows:
            has_active_data = True
            rem_pct = max(0.0, 100.0 - w.used_percent)
            line = f"  • {w.label}: {rem_pct:.1f}% left"
            if w.resets_at:
                if w.resets_at.lower().startswith(("active", "token", "resets")):
                    line += f" ({w.resets_at})"
                else:
                    line += f" (resets in {w.resets_at})"
            lines.append(line)

        if r.cost:
            has_active_data = True
            cost_str = f"  • Cost: ${r.cost.used:.2f}"
            if r.cost.limit:
                cost_str += f" / ${r.cost.limit:.2f}"
            if r.cost.period:
                cost_str += f" ({r.cost.period})"
            lines.append(cost_str)

        lines.append("")

    if not has_active_data:
        lines.append("No active quota data found.")
        lines.append("Check ~/.codexbar/config.json")
        lines.append("")

    lines.append(f"🕒 Updated: {updated_at}")
    return "\n".join(lines).strip()


def generate_argb_icon(color_hex: str = "#22C55E", size: int = 32) -> bytes:
    """Generate raw 32x32 ARGB byte array for DBus IconPixmap."""
    h = color_hex.lstrip("#")
    r_dot, g_dot, b_dot = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    pixels = bytearray()
    center_dot_x = size - 6
    center_dot_y = size - 6
    dot_rad_sq = 4.5 * 4.5

    for y in range(size):
        for x in range(size):
            in_rect = (2 <= x < size - 2) and (2 <= y < size - 2)
            dx = x - center_dot_x
            dy = y - center_dot_y
            dist_sq = dx * dx + dy * dy

            if dist_sq <= dot_rad_sq:
                a, r, g, b = 255, r_dot, g_dot, b_dot
            elif dist_sq <= dot_rad_sq + 4.0:
                a, r, g, b = 255, 15, 23, 42
            elif in_rect:
                a, r, g, b = 240, 30, 41, 59
            else:
                a, r, g, b = 0, 0, 0, 0

            pixels.extend(struct.pack(">BBBB", a, r, g, b))

    return bytes(pixels)


class DBusMenuInterface(ServiceInterface):
    def __init__(self, daemon: AITrayDaemon):
        super().__init__("com.canonical.dbusmenu")
        self.daemon = daemon
        self.revision = 1

    @dbus_property(PropertyAccess.READ)
    def Version(self) -> "u":
        return 3

    @dbus_property(PropertyAccess.READ)
    def Status(self) -> "s":
        return "normal"

    @method()
    def GetLayout(self, parentId: "i", recursionDepth: "i", propertyNames: "as") -> "u(ia{sv}av)":
        raw_items = []
        item_id = 1

        # Header item
        raw_items.append([
            item_id,
            {"label": Variant("s", "🤖 AI Usage Quotas"), "enabled": Variant("b", False), "visible": Variant("b", True)},
            [],
        ])
        item_id += 1
        raw_items.append([
            item_id,
            {"label": Variant("s", f"🕒 Updated: {self.daemon.last_updated_str}"), "enabled": Variant("b", False), "visible": Variant("b", True)},
            [],
        ])
        item_id += 1
        raw_items.append([
            item_id,
            {"type": Variant("s", "separator"), "visible": Variant("b", True)},
            [],
        ])
        item_id += 1

        # Quota entries
        if self.daemon.latest_results:
            for r in self.daemon.latest_results:
                if r.windows:
                    w = r.windows[0]
                    rem = 100.0 - w.used_percent
                    label = f"{r.provider}: {rem:.0f}% left"
                    if len(r.windows) > 1:
                        w2 = r.windows[1]
                        rem2 = 100.0 - w2.used_percent
                        label += f" | {rem2:.0f}% left"
                    if w.resets_at and not w.resets_at.lower().startswith("active"):
                        label += f" ({w.resets_at})"
                    raw_items.append([
                        item_id,
                        {"label": Variant("s", f"  • {label}"), "enabled": Variant("b", True), "visible": Variant("b", True)},
                        [],
                    ])
                    item_id += 1
            raw_items.append([
                item_id,
                {"type": Variant("s", "separator"), "visible": Variant("b", True)},
                [],
            ])
            item_id += 1

        # Action items
        raw_items.append([101, {"label": Variant("s", "🔄 Refresh Now"), "visible": Variant("b", True)}, []])
        raw_items.append([102, {"label": Variant("s", "📋 Copy Summary to Clipboard"), "visible": Variant("b", True)}, []])
        raw_items.append([103, {"label": Variant("s", "⚙️ Open Config File"), "visible": Variant("b", True)}, []])
        raw_items.append([104, {"type": Variant("s", "separator"), "visible": Variant("b", True)}, []])
        raw_items.append([105, {"label": Variant("s", "❌ Quit"), "visible": Variant("b", True)}, []])

        items = [Variant("(ia{sv}av)", it) for it in raw_items]
        root = [0, {"children-display": Variant("s", "submenu")}, items]
        return [self.revision, root]

    @method()
    def AboutToShow(self, id: "i") -> "b":
        return False

    @method()
    def GetGroupProperties(self, ids: "ai", propertyNames: "as") -> "a(ia{sv})":
        return []

    @method()
    def Event(self, id: "i", eventId: "s", data: "v", timestamp: "u"):
        if eventId == "clicked":
            if id == 101:
                asyncio.create_task(self.daemon.refresh())
            elif id == 102:
                self.daemon.copy_summary()
            elif id == 103:
                self.daemon.open_config()
            elif id == 105:
                self.daemon.quit()

    @signal()
    def LayoutUpdated(self, revision: "u", parent: "i") -> "ui":
        return [revision, parent]


class StatusNotifierItemInterface(ServiceInterface):
    def __init__(self, daemon: AITrayDaemon):
        super().__init__("org.kde.StatusNotifierItem")
        self.daemon = daemon

    @dbus_property(PropertyAccess.READ)
    def Category(self) -> "s":
        return "ApplicationStatus"

    @dbus_property(PropertyAccess.READ)
    def Id(self) -> "s":
        return "ai-usage"

    @dbus_property(PropertyAccess.READ)
    def Title(self) -> "s":
        return "AI Usage"

    @dbus_property(PropertyAccess.READ)
    def Status(self) -> "s":
        return "Active"

    @dbus_property(PropertyAccess.READ)
    def WindowId(self) -> "i":
        return 0

    @dbus_property(PropertyAccess.READ)
    def IconName(self) -> "s":
        return "ai-usage"

    @dbus_property(PropertyAccess.READ)
    def IconThemePath(self) -> "s":
        return os.path.expanduser("~/.local/share/icons")

    @dbus_property(PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        return [[32, 32, generate_argb_icon(self.daemon.status_color, 32)]]

    @dbus_property(PropertyAccess.READ)
    def OverlayIconName(self) -> "s":
        return ""

    @dbus_property(PropertyAccess.READ)
    def OverlayIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(PropertyAccess.READ)
    def AttentionIconName(self) -> "s":
        return ""

    @dbus_property(PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(PropertyAccess.READ)
    def AttentionMovieName(self) -> "s":
        return ""

    @dbus_property(PropertyAccess.READ)
    def Menu(self) -> "o":
        return "/MenuBar"

    @dbus_property(PropertyAccess.READ)
    def ToolTip(self) -> "(sa(iiay)ss)":
        tooltip_text = format_tooltip(self.daemon.latest_results, self.daemon.last_updated_str)
        return ["ai-usage", [], "🤖 AI Usage Quotas", tooltip_text]

    @dbus_property(PropertyAccess.READ)
    def ItemIsMenu(self) -> "b":
        return False

    @method()
    def Activate(self, x: "i", y: "i"):
        asyncio.create_task(self.daemon.refresh())

    @method()
    def SecondaryActivate(self, x: "i", y: "i"):
        pass

    @method()
    def ContextMenu(self, x: "i", y: "i"):
        pass

    @method()
    def Scroll(self, delta: "i", orientation: "s"):
        pass

    @signal()
    def NewToolTip(self) -> "":
        return None

    @signal()
    def NewIcon(self) -> "":
        return None


class AITrayDaemon:
    def __init__(
        self,
        provider_names: Optional[list[str]] = None,
        enabled_only: bool = True,
        interval_seconds: int = 300,
    ):
        self.provider_names = provider_names
        self.enabled_only = enabled_only
        self.interval_seconds = interval_seconds
        self.latest_results: list[UsageResult] = []
        self.last_updated_str = "Initializing..."
        self.status_color = "#22C55E"
        self.bus: Optional[MessageBus] = None
        self.sni_iface: Optional[StatusNotifierItemInterface] = None
        self.menu_iface: Optional[DBusMenuInterface] = None
        self.running = True

    async def start(self):
        self.bus = await MessageBus().connect()

        self.sni_iface = StatusNotifierItemInterface(self)
        self.menu_iface = DBusMenuInterface(self)

        self.bus.export("/StatusNotifierItem", self.sni_iface)
        self.bus.export("/MenuBar", self.menu_iface)

        # Request unique well-known name
        await self.bus.request_name("org.kde.StatusNotifierItem-ai-usage")

        # Register with Ubuntu StatusNotifierWatcher
        try:
            await self.bus.call(
                Message(
                    destination="org.kde.StatusNotifierWatcher",
                    path="/StatusNotifierWatcher",
                    interface="org.kde.StatusNotifierWatcher",
                    member="RegisterStatusNotifierItem",
                    signature="s",
                    body=["/StatusNotifierItem"],
                )
            )
            print("Successfully registered AI Usage Monitor with Ubuntu GNOME top bar.")
        except Exception as e:
            print("Notice: RegisterStatusNotifierItem:", e)

        # Initial fetch
        await self.refresh()

        # Background polling loop
        while self.running:
            await asyncio.sleep(self.interval_seconds)
            if self.running:
                await self.refresh()

    async def refresh(self):
        try:
            results = await fetch_all(self.provider_names, self.enabled_only)
            self.latest_results = results
            self.last_updated_str = datetime.now().strftime("%H:%M:%S")

            # Determine lowest remaining % for color
            min_remaining = 100.0
            has_any = False
            for r in results:
                for w in r.windows:
                    has_any = True
                    rem = 100.0 - w.used_percent
                    if rem < min_remaining:
                        min_remaining = rem

            if not has_any:
                self.status_color = "#3B82F6"
            elif min_remaining > 50.0:
                self.status_color = "#22C55E"
            elif min_remaining > 20.0:
                self.status_color = "#EAB308"
            else:
                self.status_color = "#EF4444"

            # Emit update signals
            if self.sni_iface:
                self.sni_iface.NewToolTip()
                self.sni_iface.NewIcon()
            if self.menu_iface:
                self.menu_iface.revision += 1
                self.menu_iface.LayoutUpdated(self.menu_iface.revision, 0)

        except Exception as e:
            self.last_updated_str = f"Error ({datetime.now().strftime('%H:%M:%S')})"
            self.status_color = "#94A3B8"
            if self.sni_iface:
                self.sni_iface.NewToolTip()
                self.sni_iface.NewIcon()

    def copy_summary(self):
        summary = format_tooltip(self.latest_results, self.last_updated_str)
        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(summary.encode("utf-8"))
        except Exception:
            pass

        try:
            subprocess.Popen([
                "notify-send",
                "AI Usage Quotas",
                "Usage summary copied to clipboard!",
                "-i", os.path.expanduser("~/.local/share/icons/ai-usage.png"),
            ])
        except Exception:
            pass

    def open_config(self):
        config_path = Path.home() / ".codexbar" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            config_path.write_text("{\n  \"providers\": {}\n}\n")
        try:
            subprocess.Popen(["xdg-open", str(config_path)])
        except Exception:
            pass

    def quit(self):
        self.running = False
        sys.exit(0)


def run_tray(
    provider_names: Optional[list[str]] = None,
    enabled_only: bool = True,
    interval_seconds: int = 300,
) -> None:
    daemon = AITrayDaemon(
        provider_names=provider_names,
        enabled_only=enabled_only,
        interval_seconds=interval_seconds,
    )
    try:
        asyncio.run(daemon.start())
    except (KeyboardInterrupt, SystemExit):
        pass


def main():
    parser = argparse.ArgumentParser(
        prog="ai-usage-tray",
        description="System Tray Monitor for AI Coding Quotas (Antigravity, Claude, Codex, Gemini, etc.)",
    )
    parser.add_argument(
        "-p", "--provider",
        nargs="*",
        metavar="NAME",
        help="provider(s) to query (e.g. agy claude codex gemini)",
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="query all providers (including disabled ones)",
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=300,
        help="refresh interval in seconds (default: 300 = 5 min)",
    )
    args = parser.parse_args()

    provider_names = [n.lower() for n in args.provider] if args.provider else None
    enabled_only = not args.all and provider_names is None

    run_tray(
        provider_names=provider_names,
        enabled_only=enabled_only,
        interval_seconds=args.interval,
    )


if __name__ == "__main__":
    main()
