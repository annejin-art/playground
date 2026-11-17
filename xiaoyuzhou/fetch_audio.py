#!/usr/bin/env python3
"""下载小宇宙单集音频，并保存节目简介(shownotes)。

用法: python3 fetch_audio.py <单集URL或eid> [输出目录]
页面里的 <script id="__NEXT_DATA__"> 含 episode JSON，其中 enclosure.url / media.source.url 即音频地址。
仅用标准库。
"""
import json, os, re, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")

def find_episode(node):
    # 递归找含音频地址的 episode 对象
    if isinstance(node, dict):
        if "enclosure" in node and isinstance(node["enclosure"], dict) and node["enclosure"].get("url"):
            return node
        for v in node.values():
            r = find_episode(v)
            if r: return r
    elif isinstance(node, list):
        for v in node:
            r = find_episode(v)
            if r: return r

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    arg = sys.argv[1]
    url = arg if arg.startswith("http") else f"https://www.xiaoyuzhoufm.com/episode/{arg}"
    url = url.split("?")[0]
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(out, exist_ok=True)

    html = get(url)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    ep = find_episode(json.loads(m.group(1))) if m else None
    audio = ep["enclosure"]["url"] if ep else None
    if not audio:  # 兜底：og:audio / 直接匹配媒体链接
        m2 = re.search(r'(https://media\.xyzcdn\.net/[^"\'\s<>]+\.(?:m4a|mp3))', html) \
            or re.search(r'property="og:audio" content="([^"]+)"', html)
        audio = m2.group(1) if m2 else None
    if not audio: sys.exit("没找到音频地址（页面结构可能变了，或被拦截）")

    title = (ep or {}).get("title") or re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", title).strip("_")[:80] or "episode"
    ext = os.path.splitext(audio.split("?")[0])[1] or ".m4a"
    path = os.path.join(out, safe + ext)
    with open(path, "wb") as f: f.write(get(audio, binary=True))
    if ep:
        with open(os.path.join(out, safe + ".shownotes.txt"), "w") as f:
            f.write(f"{title}\n\n{ep.get('description') or ep.get('shownotes') or ''}\n")
    print("音频:", path, "\n地址:", audio)

if __name__ == "__main__":
    main()
