#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门用于抓取 FongMi、gao 等开源爬虫配置的子脚本。
运行后将数据输出为 /tmp_data/spider_sites.json 供主引擎合并。
"""
import json
import os
import ssl
import urllib.request

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {"User-Agent": "Mozilla/5.0"}
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_data", "spider_sites.json")

URLS = [
    "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json",
    "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json",
    "https://raw.githubusercontent.com/Yoursmile7/TVBox/main/XC.json"
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
        except Exception as e:
            print(f"[Spider] Fetch error from {url}: {e}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False)
    print(f"[Spider] Successfully fetched {len(sites)} sites from Spider repos.")

if __name__ == "__main__":
    main()
