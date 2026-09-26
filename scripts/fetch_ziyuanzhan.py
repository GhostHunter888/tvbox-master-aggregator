#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, ssl, urllib.request

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_data", "ziyuanzhan_sites.json")

URLS = [
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/sources.json",
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/latest.json"
]

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    sites = []
    for url in URLS:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode('utf-8', 'ignore'), strict=False)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and (item.get("api") or item.get("url")):
                            sites.append({"name": item.get("name", "未命名"), "api": item.get("api") or item.get("url"), "type": 1})
        except: pass
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False)
    print(f"[ziyuanzhan] Fetched {len(sites)} sites.")

if __name__ == "__main__": main()
