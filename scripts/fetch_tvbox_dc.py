#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门用于抓取 tvbox-dc 仓库单/多仓数据的子脚本。
运行后将数据输出为 /tmp_data/dc_sites.json 供主引擎合并。
"""
import json
import os
import ssl
import urllib.request

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_data", "dc_sites.json")

URLS = [
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/dc_full.json",
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/sources_pool.json",
    "https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_full.json"
]

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    sites = []

    for url in URLS:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode('utf-8', 'ignore'), strict=False)
                if isinstance(data, dict):
                    if "sites" in data:
                        sites.extend(data["sites"])
                    else:
                        for k, v in data.items():
                            if isinstance(v, dict) and "url" in v:
                                sites.append({"name": v.get("name", "未命名"), "api": v["url"], "type": 1})
        except Exception as e:
            print(f"[DC] Fetch error from {url}: {e}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False)
    print(f"[DC] Successfully fetched {len(sites)} sites from tvbox-dc/tvyuan.")

if __name__ == "__main__":
    main()
