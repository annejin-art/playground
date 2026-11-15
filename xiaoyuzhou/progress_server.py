#!/usr/bin/env python3
"""转写进度 GUI：python3 progress_server.py <工作目录> [端口=8765]
工作目录下 ep*/ 每个子目录含 .m4a、transcript.txt、log.txt（log 含 'done' 表示完成）。
"""
import glob, json, os, re, subprocess, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
TITLES = {  # 目录名 -> 展示标题（目录没有 shownotes 时使用）
    "ep": "钱感训练：如何一眼锁定，正在撒钱的老板or客户？",
    "ep2": "命运给我出难题，我说OK没问题", "ep3": "世界大部分的门，都是虚掩的",
    "ep4": "想转行，但不敢？打工人换赛道如何重新定价", "ep5": "搞钱第一步：找到自己的核心竞争力",
    "ep6": "赚钱的第一性原理，是创造价值", "ep7": "挖掘自己的优势",
}
_dur = {}

def duration(path):
    if path not in _dur:
        try:
            _dur[path] = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=20).stdout.strip())
        except Exception:
            _dur[path] = 0
    return _dur[path]

def last_ts(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); f.seek(max(0, f.tell() - 600))
            m = re.findall(r"\[(\d+):(\d+):(\d+)\]", f.read().decode("utf-8", "ignore"))
        if m: h, mi, s = map(int, m[-1]); return h * 3600 + mi * 60 + s
    except Exception:
        pass
    return 0

def status():
    items = []
    for d in sorted(glob.glob(os.path.join(ROOT, "ep*")), key=lambda p: (len(p), p)):
        name = os.path.basename(d)
        m4a = glob.glob(os.path.join(d, "*.m4a"))
        total = duration(m4a[0]) if m4a else 0
        pos = last_ts(os.path.join(d, "transcript.txt"))
        log = ""
        try: log = open(os.path.join(d, "log.txt"), errors="ignore").read()
        except Exception: pass
        done = "done" in log and "Traceback" not in log
        if done: state, pos = "完成", total
        elif "Traceback" in log: state = "出错"
        elif pos > 0: state = "转写中"
        elif m4a: state = "已下载，排队中"
        else: state = "未开始"
        items.append(dict(id=name, title=TITLES.get(name, name), state=state,
                          pos=pos, total=total, pct=round(100 * pos / total, 1) if total else 0))
    rem = sum(max(i["total"] - i["pos"], 0) for i in items if i["state"] != "完成")
    return dict(items=items, remaining_min=round(rem / 60), eta_min=round(rem / 60 / 3))

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>转写进度</title><style>
:root{--bg:#fafaf9;--card:#fff;--fg:#1c1917;--mut:#78716c;--bar:#e7e5e4;--ac:#4f46e5;--ok:#16a34a;--err:#dc2626}
@media(prefers-color-scheme:dark){:root{--bg:#1c1917;--card:#292524;--fg:#fafaf9;--mut:#a8a29e;--bar:#44403c;--ac:#818cf8;--ok:#4ade80;--err:#f87171}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:720px;margin:auto}
h1{font-size:20px}.sum{color:var(--mut);margin-bottom:12px}.c{background:var(--card);border-radius:10px;padding:12px 14px;margin:10px 0}
.t{display:flex;justify-content:space-between;gap:8px}.s{color:var(--mut);font-size:13px;white-space:nowrap}
.b{height:8px;background:var(--bar);border-radius:4px;margin:8px 0 4px;overflow:hidden}.b i{display:block;height:100%;background:var(--ac)}
.done .b i{background:var(--ok)}.err .b i{background:var(--err)}.m{font-size:12px;color:var(--mut)}</style>
<h1>转写进度</h1><div class=sum id=sum>加载中…</div><div id=l></div>
<script>
const f=s=>{s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
async function r(){try{const d=await (await fetch('status')).json();
document.getElementById('sum').textContent='剩余音频约 '+d.remaining_min+' 分钟，预计还需约 '+d.eta_min+' 分钟（按 3 倍速估算）';
document.getElementById('l').innerHTML=d.items.map(i=>`<div class="c ${i.state=='完成'?'done':i.state=='出错'?'err':''}">
<div class=t><b>${i.title}</b><span class=s>${i.state}</span></div><div class=b><i style="width:${i.pct}%"></i></div>
<div class=m>${f(i.pos)} / ${f(i.total)}（${i.pct}%）</div></div>`).join('')}catch(e){document.getElementById('sum').textContent='连接失败，重试中…'}}
r();setInterval(r,5000)</script>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/status"): body, ct = json.dumps(status(), ensure_ascii=False).encode(), "application/json"
        else: body, ct = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

HTTPServer(("0.0.0.0", PORT), H).serve_forever()
