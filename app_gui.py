#!/usr/bin/env python3
"""
OpenClaw Antigravity Native macOS Desktop Application & Menu Bar
Integrates:
- Self-configuring Telegram Bot API & Bot Name setup
- Auto-regenerates QR code when bot token/name is changed
- Native WebKit Window showing Telegram Connection QR Code and Dashboard
- Background Telegram <-> Antigravity Bridge Service
"""
import os
import sys
import json
import subprocess
import threading
import time
import urllib.parse
import qrcode
import objc
from Cocoa import (
    NSApplication, NSApp, NSWindow, NSBackingStoreBuffered,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskMiniaturizable,
    NSRect, NSPoint, NSSize, NSURL, NSObject
)
from WebKit import WKWebView, WKWebViewConfiguration, WKNavigationDelegate

BRIDGE_DIR = "/Users/apple/Desktop/anto/openclaw-antigravity-bridge"
BOT_SCRIPT = os.path.join(BRIDGE_DIR, "telegram_bot.py")
DASHBOARD_HTML = os.path.join(BRIDGE_DIR, "dashboard.html")
LOG_FILE = os.path.expanduser("~/.openclaw/bridge.log")
CONFIG_FILE = os.path.expanduser("~/.openclaw/config.json")
DEFAULT_TOKEN = "8590032817:AAFRHGm3xuGaK6-3oOzQkmJxjScdesBGIWk"
DEFAULT_BOT = "Antigravity_cla_bot"

bot_process = None
mirror_process = None
caffeinate_process = None
SCREEN_MIRROR_SCRIPT = os.path.join(BRIDGE_DIR, "screen_mirror.py")

def start_caffeinate():
    global caffeinate_process
    if not caffeinate_process or caffeinate_process.poll() is not None:
        # Prevents display and system from sleeping (-d -i -m -s)
        caffeinate_process = subprocess.Popen(["/usr/bin/caffeinate", "-dims"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[Antigram] ☕ Mac Keep Awake active (caffeinate enabled)")

def stop_caffeinate():
    global caffeinate_process
    if caffeinate_process and caffeinate_process.poll() is None:
        caffeinate_process.terminate()
        caffeinate_process = None
        print("[Antigram] 💤 Mac Keep Awake disabled (caffeinate stopped)")

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"bot_token": DEFAULT_TOKEN, "bot_username": DEFAULT_BOT}

def save_config(token, username):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"bot_token": token, "bot_username": username}, f, indent=2)
    # Regenerate QR
    bot_url = f"https://t.me/{username.replace('@', '')}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(bot_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(os.path.join(BRIDGE_DIR, "bot_qr.png"))

def start_bot_bridge():
    global bot_process
    subprocess.run(["pkill", "-f", "openclaw-antigravity-bridge/telegram_bot.py"], stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log_f = open(LOG_FILE, "a")
    bot_process = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        cwd=BRIDGE_DIR,
        stdout=log_f,
        stderr=subprocess.STDOUT
    )

def start_screen_mirror():
    global mirror_process
    subprocess.run(["pkill", "-f", "openclaw-antigravity-bridge/screen_mirror.py"], stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    mirror_log = os.path.expanduser("~/.openclaw/mirror.log")
    os.makedirs(os.path.dirname(mirror_log), exist_ok=True)
    log_f = open(mirror_log, "a")
    mirror_process = subprocess.Popen(
        [sys.executable, SCREEN_MIRROR_SCRIPT],
        cwd=BRIDGE_DIR,
        stdout=log_f,
        stderr=subprocess.STDOUT
    )
    print("[Antigram] 📺 Live Screen Mirror server launched!")

def stop_screen_mirror():
    global mirror_process
    subprocess.run(["pkill", "-f", "openclaw-antigravity-bridge/screen_mirror.py"], stderr=subprocess.DEVNULL)
    if mirror_process and mirror_process.poll() is None:
        mirror_process.terminate()
        mirror_process = None
    print("[Antigram] 🛑 Live Screen Mirror stopped.")

class NavDelegate(NSObject):
    def setWebView_(self, view):
        self.web_view = view

    def webView_decidePolicyForNavigationAction_decisionHandler_(self, webView, action, handler):
        req = action.request()
        url_str = req.URL().absoluteString()
        
        if url_str.startswith("openclaw-action://open-telegram"):
            cfg = load_config()
            tg_url = f"https://t.me/{cfg.get('bot_username', DEFAULT_BOT)}"
            subprocess.run(["open", tg_url])
            handler(0)
            return

        elif url_str.startswith("openclaw-action://view-logs"):
            if os.path.exists(LOG_FILE):
                subprocess.run(["open", "-a", "Console", LOG_FILE])
            handler(0)
            return

        elif url_str.startswith("openclaw-action://save-config"):
            parsed = urllib.parse.urlparse(url_str)
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("token", [DEFAULT_TOKEN])[0]
            username = params.get("username", [DEFAULT_BOT])[0] or DEFAULT_BOT
            save_config(token, username)
            start_bot_bridge()
            # Reload webview
            file_url = NSURL.fileURLWithPath_(DASHBOARD_HTML)
            self.web_view.loadFileURL_allowingReadAccessToURL_(file_url, NSURL.fileURLWithPath_(BRIDGE_DIR))
            handler(0)
            return

        elif url_str.startswith("openclaw-action://reset-config"):
            save_config(DEFAULT_TOKEN, DEFAULT_BOT)
            start_bot_bridge()
            file_url = NSURL.fileURLWithPath_(DASHBOARD_HTML)
            self.web_view.loadFileURL_allowingReadAccessToURL_(file_url, NSURL.fileURLWithPath_(BRIDGE_DIR))
            handler(0)
            return

        elif url_str.startswith("openclaw-action://toggle-caffeinate"):
            parsed = urllib.parse.urlparse(url_str)
            params = urllib.parse.parse_qs(parsed.query)
            enabled = params.get("enabled", ["1"])[0] == "1"
            if enabled:
                start_caffeinate()
            else:
                stop_caffeinate()
            handler(0)
            return

        elif url_str.startswith("openclaw-action://start-mirror"):
            start_screen_mirror()
            # Open local/tunnel mirror page in browser or inform user
            time.sleep(1)
            subprocess.run(["open", "http://localhost:8765"])
            handler(0)
            return

        elif url_str.startswith("openclaw-action://toggle-mirror"):
            parsed = urllib.parse.urlparse(url_str)
            params = urllib.parse.parse_qs(parsed.query)
            enabled = params.get("enabled", ["1"])[0] == "1"
            if enabled:
                start_screen_mirror()
            else:
                stop_screen_mirror()
            handler(0)
            return

        elif url_str.startswith("openclaw-action://open-mirror"):
            # Check for cloudflare tunnel url or fallback to localhost
            tunnel_url = "http://localhost:8765"
            try:
                if os.path.exists("/tmp/tunnel.log"):
                    with open("/tmp/tunnel.log", "r") as f:
                        import re
                        m = re.findall(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', f.read())
                        if m:
                            tunnel_url = m[-1]
            except Exception:
                pass
            subprocess.run(["open", tunnel_url])
            handler(0)
            return

        handler(1)

def run_app():
    start_bot_bridge()
    start_screen_mirror() # Start Screen Mirror on launch
    start_caffeinate() # Keep Mac awake by default on launch
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(0)

    rect = NSRect(NSPoint(300, 200), NSSize(600, 720))
    mask = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect, mask, NSBackingStoreBuffered, False
    )
    window.setTitle_("Antigram — Antigravity Bridge")
    window.center()

    config = WKWebViewConfiguration.alloc().init()
    web_view = WKWebView.alloc().initWithFrame_configuration_(window.contentView().bounds(), config)
    web_view.setAutoresizingMask_(18)

    delegate = NavDelegate.alloc().init()
    delegate.setWebView_(web_view)
    web_view.setNavigationDelegate_(delegate)

    file_url = NSURL.fileURLWithPath_(DASHBOARD_HTML)
    web_view.loadFileURL_allowingReadAccessToURL_(file_url, NSURL.fileURLWithPath_(BRIDGE_DIR))

    window.contentView().addSubview_(web_view)
    window.makeKeyAndOrderFront_(None)
    app.activateIgnoringOtherApps_(True)
    app.run()

if __name__ == "__main__":
    run_app()
