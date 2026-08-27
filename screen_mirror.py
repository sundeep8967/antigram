#!/usr/bin/env python3
"""
Antigram Live Screen Mirror & Integrated Trackpad
Layout:
  [Screen stream - tap to click precisely]
  [Compact trackpad strip - slide to move cursor]
  [L-Click] [2x Click] [R-Click] [scroll up/dn] [keys]
"""
import io, time, re, socket, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mss
from PIL import Image
import pyautogui

pyautogui.FAILSAFE = False
PORT = 8765

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

def get_tunnel_url():
    try:
        with open("/tmp/tunnel.log") as f:
            matches = re.findall(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', f.read())
            if matches: return matches[-1]
    except: pass
    return f"http://{LOCAL_IP}:{PORT}"

def build_html():
    base = get_tunnel_url()
    print(f"⚡ [Antigram] INPUT_BASE = {base}")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
  <title>Antigram Remote</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script>const B = '{base}';</script>
  <style>
    *,*::before,*::after{{margin:0;padding:0;box-sizing:border-box;-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}}
    html,body{{background:#000;color:#e6edf3;height:100%;height:100dvh;width:100vw;overflow:hidden;display:flex;flex-direction:column;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif}}

    /* ─── HEADER ─── */
    .hdr{{flex-shrink:0;background:rgba(13,17,23,.95);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid #21262d;padding:5px 12px;display:flex;align-items:center;justify-content:space-between;z-index:100}}
    .logo{{font-size:12px;font-weight:700;background:linear-gradient(90deg,#38bdf8,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
    .live{{display:flex;align-items:center;gap:4px;font-size:10px;font-weight:600;color:#3fb950}}
    .dot{{width:5px;height:5px;border-radius:50%;background:#3fb950;box-shadow:0 0 5px #3fb950;animation:p 1.4s infinite}}
    @keyframes p{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}

    /* ─── SCREEN AREA ─── */
    .screen-wrap{{
      flex:1;min-height:0;position:relative;background:#111;
      display:flex;align-items:center;justify-content:center;
      overflow:hidden;touch-action:none;
    }}
    /* Simple CSS fit — image always letterboxed, no JS needed */
    #simg{{
      display:block;
      max-width:100%;
      max-height:100%;
      width:auto;
      height:auto;
      object-fit:contain;
      pointer-events:none;
      border:1px solid #21262d;
      box-shadow:0 4px 40px rgba(0,0,0,.9);
    }}
    /* Zoom wrapper for pinch */
    .stage{{
      display:flex;align-items:center;justify-content:center;
      width:100%;height:100%;
      transform-origin:center center;
      will-change:transform;
    }}
    .ripple{{position:absolute;width:26px;height:26px;border-radius:50%;background:rgba(56,189,248,.3);border:2px solid #38bdf8;pointer-events:none;transform:translate(-50%,-50%) scale(.4);animation:rpl .35s ease-out forwards;z-index:60}}
    @keyframes rpl{{0%{{transform:translate(-50%,-50%) scale(.4);opacity:1}}100%{{transform:translate(-50%,-50%) scale(1.7);opacity:0}}}}

    /* ─── TRACKPAD ─── */
    .trackpad-wrap{{flex-shrink:0;display:flex;flex-direction:column;background:#0d1117;border-top:1px solid #21262d}}
    .tp-label{{text-align:center;font-size:9px;font-weight:600;color:#484f58;letter-spacing:.5px;padding:3px 0 0}}

    .tp-row{{display:flex;gap:0;height:80px;margin:4px 8px 4px}}
    .tp-area{{flex:1;border-radius:10px;background:#161b22;border:1.5px solid #21262d;position:relative;touch-action:none;overflow:hidden;transition:background .15s}}
    .tp-area.touching{{background:#1c2128}}
    .tp-hint{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:10px;color:#3a424c;pointer-events:none;transition:opacity .2s}}
    .tp-area.touching .tp-hint{{opacity:0}}
    /* right scroll strip */
    .tp-scroll{{flex-shrink:0;width:28px;margin-left:6px;border-radius:10px;background:#161b22;border:1.5px dashed #21262d;display:flex;align-items:center;justify-content:center;touch-action:none}}
    .tp-scroll-lbl{{writing-mode:vertical-rl;font-size:8px;color:#3a424c;font-weight:600;letter-spacing:1px}}

    /* ─── BUTTON ROWS ─── */
    .btn-row{{flex-shrink:0;display:flex;gap:5px;padding:0 8px 8px}}
    .bk{{flex:1;padding:8px 0;border-radius:9px;border:1.5px solid #21262d;background:#161b22;color:#e6edf3;font-size:11px;font-weight:700;cursor:pointer;text-align:center;transition:background .1s,transform .1s}}
    .bk:active{{transform:scale(.95);background:#21262d}}
    .bk.blue{{border-color:rgba(56,189,248,.4);color:#38bdf8}}
    .bk.purple{{border-color:rgba(168,85,247,.4);color:#a855f7}}
    .bk.green{{border-color:rgba(63,185,80,.4);color:#3fb950}}
    .bk.gray{{color:#7d8590;font-size:10px}}
  </style>
</head>
<body>

<div class="hdr">
  <div class="logo">⚡ Antigram Remote</div>
  <div class="live"><div class="dot"></div> LIVE</div>
</div>

<!-- SCREEN MIRROR -->
<div class="screen-wrap" id="sw">
  <div class="stage" id="st">
    <img id="simg" src="/stream.mjpg" alt="Live Desktop">
  </div>
</div>

<!-- TRACKPAD -->
<div class="trackpad-wrap">
  <div class="tp-label">▲ TAP SCREEN TO CLICK PRECISELY &nbsp;|&nbsp; SLIDE BELOW TO MOVE CURSOR ▼</div>
  <div class="tp-row">
    <div class="tp-area" id="tpad">
      <div class="tp-hint">Slide to move cursor</div>
    </div>
    <div class="tp-scroll" id="tscroll">
      <div class="tp-scroll-lbl">SCROLL</div>
    </div>
  </div>
  <div class="btn-row">
    <button class="bk blue" onclick="doAction('click')">Click</button>
    <button class="bk green" onclick="doAction('dclick')">2× Click</button>
    <button class="bk purple" onclick="doAction('rclick')">R‑Click</button>
    <button class="bk" onclick="typePrompt()">⌨️ Type</button>
    <button class="bk gray" onclick="doAction('enter')">↵</button>
    <button class="bk gray" onclick="doAction('esc')">⎋</button>
  </div>
</div>

<script>
if(window.Telegram&&Telegram.WebApp){{Telegram.WebApp.ready();Telegram.WebApp.expand();}}

// ── API call ──────────────────────────────────────────────────
function api(p) {{ return fetch(B+p).catch(()=>fetch(p)); }}

function doAction(a) {{ api('/input?action='+a); }}

function typePrompt() {{
  const t = prompt('Type text to send to Mac:');
  if(t) api('/input?action=type&text='+encodeURIComponent(t));
}}

// ── SCREEN: CSS handles fit, JS handles tap + pinch-zoom ──────
const sw=document.getElementById('sw'),
      st=document.getElementById('st'),
      img=document.getElementById('simg');

let pinchScale=1, pinch0=0, sc0=1;
let tpTouchCount=0;
let dragging=false,t0x=0,t0y=0,tT0=0,dragDist=0;
let cmMode='click';
let panX=0,panY=0,panX0=0,panY0=0;

function applyStage(){{
  st.style.transform=`scale(${{pinchScale}}) translate(${{panX}}px,${{panY}}px)`;
}}

function resetZoom(){{
  pinchScale=1; panX=0; panY=0; applyStage();
}}

function ripple(cx,cy){{
  const d=document.createElement('div');
  d.className='ripple';
  d.style.left=cx+'px'; d.style.top=cy+'px';
  sw.appendChild(d); setTimeout(()=>d.remove(),380);
}}

sw.addEventListener('touchstart',e=>{{
  tpTouchCount=e.touches.length;
  if(e.touches.length===1){{
    dragging=false; dragDist=0;
    t0x=e.touches[0].clientX; t0y=e.touches[0].clientY;
    panX0=panX; panY0=panY;
    tT0=Date.now();
  }} else if(e.touches.length===2){{
    // Don't set dragging=true yet — wait to see if fingers actually move
    pinch0=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,
                       e.touches[0].clientY-e.touches[1].clientY);
    sc0=pinchScale;
    tT0=Date.now(); // track 2-finger start time for tap detection
  }}
}},{{passive:false}});

sw.addEventListener('touchmove',e=>{{
  e.preventDefault();
  if(e.touches.length===1 && tpTouchCount===1){{
    const dx=e.touches[0].clientX-t0x, dy=e.touches[0].clientY-t0y;
    dragDist=Math.hypot(dx,dy);
    if(dragDist>8){{
      dragging=true;
      panX=panX0+dx/pinchScale;
      panY=panY0+dy/pinchScale;
      applyStage();
    }}
  }} else if(e.touches.length===2){{
    const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,
                        e.touches[0].clientY-e.touches[1].clientY);
    // Only treat as pinch if distance changed significantly
    if(Math.abs(d-pinch0)>12){{
      dragging=true;
      pinchScale=Math.min(Math.max(.5,sc0*(d/pinch0)),5);
      applyStage();
    }}
  }}
}},{{passive:false}});

sw.addEventListener('touchend',e=>{{
  const elapsed=Date.now()-tT0;

  // 2-finger tap → right-click at midpoint
  if(tpTouchCount===2 && !dragging && elapsed<300){{
    // Midpoint of the two original fingers
    const allT=e.changedTouches;
    const midX=(e.changedTouches[0].clientX+(e.changedTouches[1]?e.changedTouches[1].clientX:e.changedTouches[0].clientX))/2;
    const midY=(e.changedTouches[0].clientY+(e.changedTouches[1]?e.changedTouches[1].clientY:e.changedTouches[0].clientY))/2;
    const r=img.getBoundingClientRect();
    const xr=(midX-r.left)/r.width, yr=(midY-r.top)/r.height;
    if(xr>=0&&xr<=1&&yr>=0&&yr<=1){{
      ripple(midX-sw.getBoundingClientRect().left, midY-sw.getBoundingClientRect().top);
      api(`/input?action=rclick&x=${{xr}}&y=${{yr}}`);
    }}
    dragging=false; return;
  }}

  // 1-finger tap → click (or whatever cmMode is)
  if(!dragging && e.changedTouches.length===1 && tpTouchCount===1 && elapsed<300){{
    const t=e.changedTouches[0];
    const r=img.getBoundingClientRect();
    const xr=(t.clientX-r.left)/r.width;
    const yr=(t.clientY-r.top)/r.height;
    if(xr>=0&&xr<=1&&yr>=0&&yr<=1){{
      ripple(t.clientX-sw.getBoundingClientRect().left, t.clientY-sw.getBoundingClientRect().top);
      api(`/input?action=${{cmMode}}&x=${{xr}}&y=${{yr}}`);
      cmMode='click';
    }}
  }}
  dragging=false;
}});

// desktop mouse click
sw.addEventListener('click',e=>{{
  const r=img.getBoundingClientRect();
  const xr=(e.clientX-r.left)/r.width, yr=(e.clientY-r.top)/r.height;
  if(xr>=0&&xr<=1&&yr>=0&&yr<=1){{
    api(`/input?action=click&x=${{xr}}&y=${{yr}}`);
  }}
}});

// ── TRACKPAD: Real Mac Trackpad Behavior ──────────────────────
// 1-finger slide  → move cursor
// 1-finger tap    → left click
// 2-finger slide  → scroll (natural: down=scroll down)
// 2-finger tap    → right click
const tpad=document.getElementById('tpad');
const tscroll=document.getElementById('tscroll');
const SENS=2.5;

let tpLastX=0,tpLastY=0;
let tpStartX=0,tpStartY=0,tpStartTime=0;
let tpMoved=false,tpActive=false,tpFingers=0;
let tpMidY=0; // for 2-finger scroll

tpad.addEventListener('touchstart',e=>{{
  e.preventDefault();
  tpFingers=e.touches.length;
  tpad.classList.add('touching');

  if(e.touches.length===1){{
    tpLastX=tpStartX=e.touches[0].clientX;
    tpLastY=tpStartY=e.touches[0].clientY;
    tpStartTime=Date.now();
    tpMoved=false;
    tpActive=true;
  }} else if(e.touches.length===2){{
    tpMidY=(e.touches[0].clientY+e.touches[1].clientY)/2;
    tpMoved=true; // suppress 1-finger tap
    tpActive=true;
  }}
}},{{passive:false}});

tpad.addEventListener('touchmove',e=>{{
  e.preventDefault();
  if(!tpActive) return;

  if(e.touches.length===1 && tpFingers===1){{
    const dx=Math.round((e.touches[0].clientX-tpLastX)*SENS);
    const dy=Math.round((e.touches[0].clientY-tpLastY)*SENS);
    tpLastX=e.touches[0].clientX;
    tpLastY=e.touches[0].clientY;
    const dist=Math.hypot(tpLastX-tpStartX,tpLastY-tpStartY);
    if(dist>5) tpMoved=true;
    if(tpMoved && (Math.abs(dx)>0||Math.abs(dy)>0))
      api(`/input?action=mousemove&dx=${{dx}}&dy=${{dy}}`);

  }} else if(e.touches.length===2){{
    tpFingers=2;
    const midY=(e.touches[0].clientY+e.touches[1].clientY)/2;
    const delta=midY-tpMidY;
    tpMidY=midY;
    // Natural scroll: finger up = scroll down = negative lines
    if(Math.abs(delta)>1.5){{
      const lines=delta<0?-3:3;
      api(`/input?action=scroll&lines=${{lines}}`);
    }}
  }}
}},{{passive:false}});

tpad.addEventListener('touchend',e=>{{
  // Tap to click (1-finger, short, barely moved)
  if(!tpMoved && tpFingers===1 && Date.now()-tpStartTime<300){{
    api('/input?action=click');
  }}
  // 2-finger tap = right click
  if(tpFingers===2 && Date.now()-tpStartTime<250){{
    api('/input?action=rclick');
  }}
  if(e.touches.length===0){{
    tpActive=false;
    tpad.classList.remove('touching');
    tpFingers=0; tpMoved=false;
  }}
}},{{passive:false}});

// ── SCROLL STRIP (side strip, single finger) ─────────────────
let scLastY=0,scActive=false;

tscroll.addEventListener('touchstart',e=>{{
  e.preventDefault();
  scLastY=e.touches[0].clientY; scActive=true;
}},{{passive:false}});

tscroll.addEventListener('touchmove',e=>{{
  e.preventDefault();
  if(!scActive) return;
  const dy=e.touches[0].clientY-scLastY;
  scLastY=e.touches[0].clientY;
  if(Math.abs(dy)>2) api(`/input?action=scroll&lines=${{dy>0?3:-3}}`);
}},{{passive:false}});

tscroll.addEventListener('touchend',()=>scActive=false,{{passive:false}});
</script>
</body>
</html>"""


class MirrorHandler(BaseHTTPRequestHandler):
    def log_message(self,f,*a): return

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","*")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        path=self.path.split("?")[0]

        if path in ("/","/index.html"):
            html=build_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(html)))
            self._cors(); self.end_headers()
            self.wfile.write(html); return

        elif path=="/input":
            from urllib.parse import urlparse,parse_qs
            params=parse_qs(urlparse(self.path).query)
            action=params.get("action",[""])[0]
            sw,sh=pyautogui.size()

            if action in ("click","rclick","dclick"):
                # Only move if x,y explicitly provided — otherwise click at current cursor
                if "x" in params and "y" in params:
                    xr=float(params["x"][0]); yr=float(params["y"][0])
                    cx=max(0,min(sw-1,int(xr*sw))); cy=max(0,min(sh-1,int(yr*sh)))
                    print(f"[Touch→Click] {action} ({cx},{cy})")
                    if action=="click":    pyautogui.click(cx,cy)
                    elif action=="rclick": pyautogui.rightClick(cx,cy)
                    elif action=="dclick": pyautogui.doubleClick(cx,cy)
                else:
                    # Click at CURRENT mouse position — no move!
                    cx,cy=pyautogui.position()
                    print(f"[Trackpad→Click] {action} at current pos ({cx},{cy})")
                    if action=="click":    pyautogui.click()
                    elif action=="rclick": pyautogui.rightClick()
                    elif action=="dclick": pyautogui.doubleClick()

            elif action=="mousemove":
                dx=int(params.get("dx",["0"])[0])
                dy=int(params.get("dy",["0"])[0])
                try:
                    cx,cy=pyautogui.position()
                    nx=max(0,min(sw-1,cx+dx))
                    ny=max(0,min(sh-1,cy+dy))
                    pyautogui.moveTo(nx,ny,duration=0)
                except Exception as me:
                    # Fallback: use cliclick if installed
                    try:
                        cx,cy=pyautogui.position()
                        subprocess.run(["cliclick",f"m:{cx+dx},{cy+dy}"],capture_output=True)
                    except: pass

            elif action=="scroll":
                lines=int(params.get("lines",["1"])[0])
                try:
                    pyautogui.scroll(lines)
                except:
                    # Fallback: osascript scroll
                    direction="up" if lines>0 else "down"
                    subprocess.run(["osascript","-e",
                        f'tell application "System Events" to key code {"125" if direction=="down" else "126"} using {{}}'],
                        capture_output=True)

            elif action=="type":
                text=params.get("text",[""])[0]
                if text: pyautogui.write(text,interval=0.01)

            elif action=="click_ide":
                subprocess.run(["osascript","-e",'tell application "Antigravity IDE" to activate'])
            elif action=="enter":  pyautogui.press("enter")
            elif action=="esc":    pyautogui.press("esc")
            elif action=="space":  pyautogui.press("space")
            elif action=="volup":
                subprocess.run(["osascript","-e","set volume output volume ((output volume of (get volume settings)) + 10)"])
            elif action=="voldown":
                subprocess.run(["osascript","-e","set volume output volume ((output volume of (get volume settings)) - 10)"])

            self.send_response(200)
            self.send_header("Content-Type","text/plain")
            self._cors(); self.end_headers()
            self.wfile.write(b"OK"); return

        elif path=="/stream.mjpg":
            self.send_response(200)
            self.send_header("Age","0")
            self.send_header("Cache-Control","no-cache, private")
            self.send_header("Pragma","no-cache")
            self.send_header("Content-Type","multipart/x-mixed-replace; boundary=FRAME")
            self._cors(); self.end_headers()
            with mss.mss() as sct:
                mon=sct.monitors[1]
                while True:
                    try:
                        raw=sct.grab(mon)
                        fi=Image.frombytes("RGB",raw.size,raw.bgra,"raw","BGRX")
                        fi.thumbnail((1280,800),Image.Resampling.BILINEAR)
                        buf=io.BytesIO(); fi.save(buf,format="JPEG",quality=60)
                        frame=buf.getvalue()
                        self.wfile.write(b"--FRAME\r\n")
                        self.send_header("Content-Type","image/jpeg")
                        self.send_header("Content-Length",str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame); self.wfile.write(b"\r\n")
                        time.sleep(0.04)
                    except: break
        else:
            self.send_error(404)

def run():
    s=ThreadingHTTPServer(("0.0.0.0",PORT),MirrorHandler)
    s.daemon_threads=True
    print(f"⚡ [Antigram] http://{LOCAL_IP}:{PORT}  |  {get_tunnel_url()}")
    s.serve_forever()

if __name__=="__main__":
    run()
