#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, ssl, urllib.request

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_data", "github_singles_sites.json")

URLS = [
    "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json",
    "https://raw.githubusercontent.com/Yoursmile7/TVBox/main/XC.json",
    "https://raw.githubusercontent.com/liu673cn/box/main/m.json",
    "https://raw.githubusercontent.com/xiaolong69/tv/main/1.json",
    "https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json",
    "https://raw.githubusercontent.com/guot55/YGBH/main/vip2.json",
    "https://dxawi.github.io/0/0.json"
]

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    sites = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode('utf-8', 'ignore'), strict=False)
                if isinstance(data, dict) and "sites" in data:
                    sites.extend(data["sites"])
        except: pass
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False)
    print(f"[GitHub-Singles] Fetched {len(sites)} sites.")

if __name__ == "__main__": main()
