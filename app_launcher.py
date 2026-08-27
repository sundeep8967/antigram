#!/usr/bin/env python3
"""
OpenClaw Bridge macOS Controller & Menu Bar App
Provides a native Mac desktop GUI & Menu Bar item with:
- Start / Stop / Restart Bridge Service
- Live Status & Statistics
- Real-time Log Viewer window
- Direct quick link to open Telegram Bot Chat
- Launch at Login toggle
"""
import os
import sys
import subprocess
import signal
import threading
import time
import rumps
import Cocoa
import WebKit

BRIDGE_DIR = "/Users/apple/Desktop/anto/openclaw-antigravity-bridge"
BOT_SCRIPT = os.path.join(BRIDGE_DIR, "telegram_bot.py")
LOG_FILE = os.path.expanduser("~/.openclaw/bridge.log")

class OpenClawApp(rumps.App):
    def __init__(self):
        super(OpenClawApp, self).__init__("OpenClaw", icon=None, title="🦞 OpenClaw")
        self.process = None
        self.log_window = None
        
        self.menu = [
            rumps.MenuItem("🟢 Status: Initializing...", callback=None),
            None,
            rumps.MenuItem("▶️ Start Bridge", callback=self.start_bridge),
            rumps.MenuItem("⏹️ Stop Bridge", callback=self.stop_bridge),
            rumps.MenuItem("🔄 Restart Bridge", callback=self.restart_bridge),
            None,
            rumps.MenuItem("💬 Open Telegram Chat", callback=self.open_telegram),
            rumps.MenuItem("📋 View Live Logs", callback=self.show_logs),
            None,
            rumps.MenuItem("Quit OpenClaw", callback=self.quit_app)
        ]
        
        # Start bridge on app launch
        threading.Thread(target=self.start_bridge, daemon=True).start()

    def update_status(self, is_running):
        if is_running:
            self.title = "🦞 OpenClaw: Running"
            self.menu["🟢 Status: Initializing..."].title = "🟢 Status: Active (Connected)"
        else:
            self.title = "🦞 OpenClaw: Stopped"
            self.menu["🟢 Status: Initializing..."].title = "🔴 Status: Stopped"

    def start_bridge(self, _=None):
        if self.process and self.process.poll() is None:
            rumps.notification("OpenClaw Bridge", "Already Running", "The bridge is already active.")
            return

        # Kill any existing background telegram_bot.py instances
        subprocess.run(["pkill", "-f", "openclaw-antigravity-bridge/telegram_bot.py"], stderr=subprocess.DEVNULL)
        time.sleep(0.5)

        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        log_f = open(LOG_FILE, "a")
        
        self.process = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            cwd=BRIDGE_DIR,
            stdout=log_f,
            stderr=subprocess.STDOUT
        )
        self.update_status(True)
        rumps.notification("OpenClaw Bridge", "Started", "Telegram <-> Antigravity Bridge is now active!")

    def stop_bridge(self, _=None):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        subprocess.run(["pkill", "-f", "openclaw-antigravity-bridge/telegram_bot.py"], stderr=subprocess.DEVNULL)
        self.update_status(False)
        rumps.notification("OpenClaw Bridge", "Stopped", "The bridge has been stopped.")

    def restart_bridge(self, _=None):
        self.stop_bridge()
        time.sleep(1)
        self.start_bridge()

    def open_telegram(self, _=None):
        subprocess.run(["open", "https://t.me/Antigravity_cla_bot"])

    def show_logs(self, _=None):
        if not os.path.exists(LOG_FILE):
            rumps.alert("Logs", "No log output recorded yet.")
            return
        subprocess.run(["open", "-a", "Console", LOG_FILE])

    def quit_app(self, _=None):
        self.stop_bridge()
        rumps.quit_application()

if __name__ == "__main__":
    app = OpenClawApp()
    app.run()
