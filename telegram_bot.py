"""
OpenClaw Telegram Bot — Two-Way Antigravity IDE Bridge (Antigram)
Provides:
1. Complete Mac Remote Control (Execute Shell Commands, Mouse Clicks, Hotkeys, Open Apps).
2. Live Mac Screen Stream & Short Video Clips (5s).
3. Complete Antigravity IDE remote restart with workspace repo preservation.
4. Inline clickable action buttons and persistent ⌘ menu keyboard.
5. Two-way live prompt injection & transcript response streaming.
"""
import os
import sys
import asyncio
import json
import glob
import subprocess
import httpx
import pyautogui
from datetime import datetime

CONFIG_FILE = os.path.expanduser("~/.openclaw/config.json")
DEFAULT_TOKEN = "8590032817:AAFRHGm3xuGaK6-3oOzQkmJxjScdesBGIWk"

def get_bot_token():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return cfg.get("bot_token", DEFAULT_TOKEN)
    except Exception:
        pass
    return os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_TOKEN)

TELEGRAM_BOT_TOKEN = get_bot_token()
WORKSPACE_ROOT = "/Users/apple/Desktop/anto"
SESSIONS_FILE = os.path.expanduser("~/.openclaw/antigravity-sessions.json")

active_chat_id = None
last_sent_step = 0

# 1. Permanent Bottom Keyboard Buttons (Opens when clicking the ⌘ / grid symbol left of smiley)
REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "📺 Live Screen Mirror"}, {"text": "📸 Screenshot"}],
        [{"text": "🎥 Live Clip (5s)"}, {"text": "🎮 Remote Controls"}],
        [{"text": "🔄 Restart IDE"}, {"text": "☕ Keep Awake"}],
        [{"text": "⚡ Status"}, {"text": "📂 List Files"}]
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

# 2. Inline Clickable Action Buttons (Attached directly to message bubbles)
INLINE_BUTTONS = {
    "inline_keyboard": [
        [
            {"text": "📺 Live Mirror Stream", "callback_data": "action_mirror"},
            {"text": "📸 Screenshot", "callback_data": "action_screenshot"}
        ],
        [
            {"text": "🎮 Remote Panel", "callback_data": "action_remote_panel"},
            {"text": "🔄 Restart IDE", "callback_data": "action_restart_ide"}
        ]
    ]
}

# 3. Interactive Remote Control Keypad
REMOTE_KEYPAD = {
    "inline_keyboard": [
        [
            {"text": "⏸️ Space/Play", "callback_data": "key_space"},
            {"text": "⏎ Enter", "callback_data": "key_enter"},
            {"text": "⎋ Esc", "callback_data": "key_esc"}
        ],
        [
            {"text": "🔊 Vol Up", "callback_data": "key_volup"},
            {"text": "🔉 Vol Down", "callback_data": "key_voldown"},
            {"text": "🔇 Mute", "callback_data": "key_mute"}
        ],
        [
            {"text": "💻 Focus Antigravity", "callback_data": "app_antigravity"},
            {"text": "🌐 Focus Browser", "callback_data": "app_browser"}
        ],
        [
            {"text": "📸 Take Screenshot", "callback_data": "action_screenshot"},
            {"text": "🔙 Back", "callback_data": "action_status"}
        ]
    ]
}

def load_mcp_sessions():
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def get_active_transcript_path():
    pattern = os.path.expanduser("~/.gemini/antigravity-ide/brain/*/.system_generated/logs/transcript.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files[0]

def get_highest_step_index(transcript_file):
    if not transcript_file or not os.path.exists(transcript_file):
        return 0
    highest = 0
    try:
        with open(transcript_file, "r") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    s = obj.get("step_index", 0)
                    if s > highest:
                        highest = s
                except Exception:
                    pass
    except Exception:
        pass
    return highest

async def send_chat_action(client: httpx.AsyncClient, chat_id: int, action: str = "typing"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction"
    try:
        await client.post(url, json={"chat_id": chat_id, "action": action})
    except Exception:
        pass

async def answer_callback_query(client: httpx.AsyncClient, callback_query_id: str, text: str = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    try:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        await client.post(url, json=payload)
    except Exception:
        pass

async def send_telegram_message(client: httpx.AsyncClient, chat_id: int, text: str, reply_markup=REPLY_KEYBOARD):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }
    try:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            print(f"[Telegram Error {resp.status_code}] {resp.text}")
    except Exception as e:
        print(f"[Telegram Exception] {e}")

async def send_screenshot(client: httpx.AsyncClient, chat_id: int):
    screenshot_path = "/tmp/antigravity_mac_screenshot.jpg"
    try:
        await send_chat_action(client, chat_id, "upload_photo")
        subprocess.run(["screencapture", "-x", "-t", "jpg", screenshot_path], check=True)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(screenshot_path, "rb") as f:
            files = {"photo": ("screenshot.jpg", f, "image/jpeg")}
            data = {
                "chat_id": chat_id,
                "caption": f"📸 Live Mac Desktop ({datetime.now().strftime('%H:%M:%S')})",
                "reply_markup": json.dumps(INLINE_BUTTONS)
            }
            resp = await client.post(url, data=data, files=files)
            if resp.status_code == 200:
                print(f"[Screenshot] Successfully sent live screen to {chat_id}")
            else:
                print(f"[Screenshot Error] {resp.text}")
    except Exception as e:
        print(f"[Screenshot Exception] {e}")
        await send_telegram_message(client, chat_id, f"❌ Failed to capture screenshot: {e}")

async def send_live_clip(client: httpx.AsyncClient, chat_id: int, duration: int = 5):
    video_path = "/tmp/antigravity_live_clip.mp4"
    if os.path.exists(video_path):
        try: os.remove(video_path)
        except Exception: pass

    try:
        await send_telegram_message(client, chat_id, f"🎥 *Recording {duration}s live screen clip...*")
        await send_chat_action(client, chat_id, "record_video")

        cmd = [
            "ffmpeg", "-y",
            "-f", "avfoundation",
            "-framerate", "15",
            "-i", "1:none",
            "-t", str(duration),
            "-vf", "scale=1280:-2",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            video_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=duration + 4)

        if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
            await send_chat_action(client, chat_id, "upload_video")
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
            with open(video_path, "rb") as f:
                files = {"video": ("screen_clip.mp4", f, "video/mp4")}
                data = {
                    "chat_id": chat_id,
                    "caption": f"🎥 Live Mac Screen Video ({datetime.now().strftime('%H:%M:%S')})",
                    "reply_markup": json.dumps(INLINE_BUTTONS)
                }
                resp = await client.post(url, data=data, files=files, timeout=40.0)
                if resp.status_code == 200:
                    print(f"[Live Clip] Sent {duration}s screen video to {chat_id}")
                else:
                    print(f"[Live Clip Error] {resp.text}")
        else:
            await send_screenshot(client, chat_id)
    except Exception as e:
        print(f"[Live Clip Exception] {e}")
        await send_screenshot(client, chat_id)

def restart_antigravity_ide(target_folder: str = WORKSPACE_ROOT) -> bool:
    try:
        applescript_quit = '''
        tell application "System Events"
            set procList to every process whose name is "Electron" or name contains "Antigravity"
            repeat with proc in procList
                tell proc to quit
            end repeat
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript_quit], capture_output=True)
        subprocess.run(["pkill", "-f", "Antigravity"], stderr=subprocess.DEVNULL)
        import time
        time.sleep(2.0)

        app_path = "/Applications/Antigravity IDE.app"
        if not os.path.exists(app_path):
            app_path = "/Applications/Antigravity.app"

        subprocess.Popen(["open", "-a", app_path, target_folder])
        return True
    except Exception as e:
        print(f"[Restart IDE Error] {e}")
        return False

def inject_to_antigravity_ide(prompt: str) -> bool:
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
        p.communicate(input=prompt)

        applescript = '''
        tell application "System Events"
            set procList to every process whose name is "Electron" or name contains "Antigravity"
            if (count of procList) > 0 then
                set targetProc to item 1 of procList
                set frontmost of targetProc to true
                delay 0.1
                keystroke "c" using {command down, option down}
                delay 0.15
                keystroke "v" using {command down}
                delay 0.15
                key code 36
                return "SUCCESS"
            else
                return "NOT_FOUND"
            end if
        end tell
        '''
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        output = res.stdout.strip()
        return "SUCCESS" in output
    except Exception as e:
        return False

async def watch_transcript_loop(client: httpx.AsyncClient):
    global last_sent_step, active_chat_id
    transcript_file = get_active_transcript_path()
    if transcript_file:
        last_sent_step = get_highest_step_index(transcript_file)

    while True:
        try:
            transcript_file = get_active_transcript_path()
            if transcript_file and os.path.exists(transcript_file) and active_chat_id:
                with open(transcript_file, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    try:
                        obj = json.loads(line.strip())
                        step_idx = obj.get("step_index", 0)
                        source = obj.get("source")
                        step_type = obj.get("type")
                        content = obj.get("content", "").strip()

                        if step_idx > last_sent_step and source == "MODEL" and step_type == "PLANNER_RESPONSE":
                            last_sent_step = step_idx
                            if content:
                                chunks = [content[i:i+3800] for i in range(0, len(content), 3800)]
                                for chunk in chunks:
                                    await send_telegram_message(client, active_chat_id, chunk)
                                    await asyncio.sleep(0.3)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Watcher Error] {e}")
        await asyncio.sleep(0.8)

async def handle_remote_key(client: httpx.AsyncClient, chat_id: int, key_data: str):
    if key_data == "key_space":
        pyautogui.press('space')
        await send_telegram_message(client, chat_id, "⌨️ Sent: Spacebar")
    elif key_data == "key_enter":
        pyautogui.press('enter')
        await send_telegram_message(client, chat_id, "⌨️ Sent: Enter")
    elif key_data == "key_esc":
        pyautogui.press('esc')
        await send_telegram_message(client, chat_id, "⌨️ Sent: Escape")
    elif key_data == "key_volup":
        subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"])
        await send_telegram_message(client, chat_id, "🔊 Volume Up")
    elif key_data == "key_voldown":
        subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"])
        await send_telegram_message(client, chat_id, "🔉 Volume Down")
    elif key_data == "key_mute":
        subprocess.run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"])
        await send_telegram_message(client, chat_id, "🔇 Toggled Mute")
    elif key_data == "app_antigravity":
        subprocess.run(["osascript", "-e", 'tell application "Antigravity IDE" to activate'])
        await send_telegram_message(client, chat_id, "💻 Focused Antigravity IDE")
    elif key_data == "app_browser":
        subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
        await send_telegram_message(client, chat_id, "🌐 Focused Chrome Browser")

async def execute_terminal_cmd(client: httpx.AsyncClient, chat_id: int, cmd_str: str):
    await send_chat_action(client, chat_id, "typing")
    try:
        res = subprocess.run(cmd_str, shell=True, cwd=WORKSPACE_ROOT, capture_output=True, text=True, timeout=20)
        out = (res.stdout + res.stderr).strip()
        if not out:
            out = "✅ Command finished with no output (Exit Code 0)"
        else:
            if len(out) > 3500:
                out = out[:3500] + "\n... (truncated)"
        await send_telegram_message(client, chat_id, f"🖥️ *Terminal Output:*\n```\n{out}\n```")
    except subprocess.TimeoutExpired:
        await send_telegram_message(client, chat_id, "⚠️ Command timed out after 20 seconds.")
    except Exception as e:
        await send_telegram_message(client, chat_id, f"❌ Execution error: {e}")

async def get_mirror_urls():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lip = s.getsockname()[0]
        s.close()
    except Exception:
        lip = "127.0.0.1"
    local_url = f"http://{lip}:8765"

    # Check tunnel log for https trycloudflare.com
    https_url = None
    if os.path.exists("/tmp/tunnel.log"):
        try:
            with open("/tmp/tunnel.log", "r") as f:
                for line in f:
                    if "trycloudflare.com" in line:
                        import re
                        m = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", line)
                        if m:
                            https_url = m.group(0)
        except Exception:
            pass
    return local_url, (https_url or local_url)

async def handle_action(client: httpx.AsyncClient, chat_id: int, action: str):
    if action == "action_mirror" or action in ["📺 Live Screen Mirror", "/mirror", "mirror"]:
        local_url, https_url = await get_mirror_urls()
        
        # Build button to open mirror stream directly inside Telegram WebApp
        MIRROR_INLINE = {
            "inline_keyboard": [
                [{"text": "📱 Open Inside Telegram (Mini App)", "web_app": {"url": https_url}}],
                [{"text": "🌐 Open in Phone Browser", "url": local_url}],
                [{"text": "📸 Snapshot", "callback_data": "action_screenshot"}, {"text": "🎮 Remote Panel", "callback_data": "action_remote_panel"}]
            ]
        }

        msg = (
            f"📺 *Antigram Live 60 FPS Screen Mirror & Remote Touch*\n\n"
            f"⚡ *How to use on your phone:*\n"
            f"1. Tap **📱 Open Inside Telegram (Mini App)** below.\n"
            f"2. Your live Mac screen will open directly inside Telegram!\n"
            f"3. **Touch to Click:** Tap anywhere on your phone screen to click on that exact spot on your Mac.\n"
            f"4. **Type Text:** Use the on-screen toolbar to type text or press hotkeys."
        )
        await send_telegram_message(client, chat_id, msg, reply_markup=MIRROR_INLINE)
        return

    if action == "action_screenshot" or action in ["📸 Screenshot", "/screenshot"]:
        await send_screenshot(client, chat_id)
        return

    if action == "action_clip" or action in ["🎥 Live Clip (5s)", "🎥 Live Clip", "/clip", "/video"]:
        await send_live_clip(client, chat_id, duration=5)
        return

    if action == "action_remote_panel" or action in ["🎮 Remote Controls", "/remote", "remote"]:
        msg = (
            "🎮 *Antigram Remote PC Control Panel*\n\n"
            "• Use the interactive buttons below to trigger keystrokes & apps.\n"
            "• Or send `/cmd <command>` to run any terminal command on your Mac!\n"
            "  _Example:_ `/cmd ls -la` or `/cmd git status`"
        )
        await send_telegram_message(client, chat_id, msg, reply_markup=REMOTE_KEYPAD)
        return

    if action == "action_restart_ide" or action in ["🔄 Restart IDE", "/restart_ide", "/restart"]:
        await send_telegram_message(client, chat_id, f"🔄 *Restarting Antigravity IDE...*\nClosing app and restoring workspace: `{WORKSPACE_ROOT}`")
        success = restart_antigravity_ide(WORKSPACE_ROOT)
        if success:
            await asyncio.sleep(3.0)
            await send_telegram_message(client, chat_id, f"✅ *Antigravity IDE successfully restarted!* Re-opened in `{WORKSPACE_ROOT}`")
        else:
            await send_telegram_message(client, chat_id, f"❌ Failed to restart Antigravity IDE.")
        return

    if action == "action_status" or action in ["⚡ Status", "/status"]:
        transcript_file = get_active_transcript_path()
        status_msg = (
            f"⚡ *Antigram Bridge Status*\n\n"
            f"🟢 *Daemon:* Active & Connected\n"
            f"🎯 *Active Workspace:* `{WORKSPACE_ROOT}`\n"
            f"📜 *Active Transcript:* `{os.path.basename(os.path.dirname(os.path.dirname(transcript_file))) if transcript_file else 'None'}`\n"
            f"💬 *Active Chat ID:* `{chat_id}`"
        )
        await send_telegram_message(client, chat_id, status_msg)
        return

    if action == "action_awake" or action in ["☕ Keep Awake", "/awake"]:
        res = subprocess.run(["pgrep", "caffeinate"], capture_output=True, text=True)
        if res.stdout.strip():
            subprocess.run(["pkill", "caffeinate"], stderr=subprocess.DEVNULL)
            await send_telegram_message(client, chat_id, "💤 *Mac Keep Awake:* Disabled (Normal sleep permitted)")
        else:
            subprocess.Popen(["/usr/bin/caffeinate", "-dims"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await send_telegram_message(client, chat_id, "☕ *Mac Keep Awake:* Enabled (System and display will never sleep!)")
        return

    if action == "action_files" or action in ["📂 List Files", "/files"]:
        try:
            files = sorted(os.listdir(WORKSPACE_ROOT))[:30]
            files_list = "\n".join([f"• `{f}`" for f in files if not f.startswith(".")])
            await send_telegram_message(client, chat_id, f"📂 *Workspace Files:*\n\n{files_list}")
        except Exception as e:
            await send_telegram_message(client, chat_id, f"❌ Error: {e}")
        return

    if action == "action_tasks" or action in ["📋 Active Tasks", "/tasks"]:
        sessions = load_mcp_sessions()
        if not sessions:
            await send_telegram_message(client, chat_id, "ℹ️ No recent tasks found in Antigravity bridge.")
            return
        items = []
        for sid, s in list(sessions.items())[-5:]:
            items.append(f"• `{sid}`: {s.get('prompt', '')[:40]}... _({s.get('status')})_")
        await send_telegram_message(client, chat_id, "📋 *Recent Antigravity Tasks:*\n\n" + "\n".join(items))
        return

async def handle_update(client: httpx.AsyncClient, update: dict):
    global active_chat_id

    callback_query = update.get("callback_query")
    if callback_query:
        cb_id = callback_query.get("id")
        data = callback_query.get("data")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        if chat_id and data:
            active_chat_id = chat_id
            await answer_callback_query(client, cb_id, text="Executing...")
            if data.startswith("key_") or data.startswith("app_"):
                await handle_remote_key(client, chat_id, data)
            else:
                await handle_action(client, chat_id, data)
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user_name = message.get("from", {}).get("first_name", "User")

    if not chat_id or not text:
        return

    active_chat_id = chat_id
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Telegram from {user_name} ({chat_id}): {text}")

    # REMOTE TERMINAL COMMAND: /cmd <command> or $ <command>
    if text.startswith("/cmd ") or text.startswith("$ "):
        cmd_str = text[5:] if text.startswith("/cmd ") else text[2:]
        await execute_terminal_cmd(client, chat_id, cmd_str)
        return

    if text in ["📺 Live Screen Mirror", "/mirror", "mirror", "📸 Screenshot", "/screenshot", "🎥 Live Clip (5s)", "/clip", "🎮 Remote Controls", "/remote", "🔄 Restart IDE", "/restart_ide", "/restart", "⚡ Status", "/status", "☕ Keep Awake", "/awake", "📂 List Files", "/files", "📋 Active Tasks", "/tasks"]:
        await handle_action(client, chat_id, text)
        return

    if text in ["/start", "/help", "❓ Help", "help"]:
        welcome = (
            f"⚡ *Welcome to Antigram — Antigravity Telegram Remote Controller*\n\n"
            f"🎯 *Active Workspace:* `{WORKSPACE_ROOT}`\n\n"
            f"👇 *Remote Features:*\n"
            f"• **🎮 Remote Controls**: Click buttons for volume, focus apps, hotkeys\n"
            f"• **🖥️ Terminal Exec**: Type `/cmd git status` or `/cmd ls` to run shell commands\n"
            f"• **🎥 Live Screen**: 5s video stream & screenshots\n"
            f"• **💬 Chat with AI**: Just type any prompt to send to Antigravity IDE!"
        )
        await send_telegram_message(client, chat_id, welcome)
        return

    await send_chat_action(client, chat_id, "typing")
    inject_to_antigravity_ide(text)

async def main():
    global TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN = get_bot_token()
    print("=" * 65)
    print("⚡ ANTIGRAM — COMPLETE REMOTE MAC & ANTIGRAVITY CONTROLLER")
    print(f"📂 Workspace: {WORKSPACE_ROOT}")
    print("=" * 65)

    offset = 0
    async with httpx.AsyncClient(timeout=35.0) as client:
        asyncio.create_task(watch_transcript_loop(client))

        while True:
            try:
                poll_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=25"
                resp = await client.get(poll_url)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await handle_update(client, update)
                elif resp.status_code == 409:
                    await asyncio.sleep(2.0)
            except Exception as e:
                print(f"[Polling Error] {e}")
                await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(main())
