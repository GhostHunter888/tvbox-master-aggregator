#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 专属脚本：真实视频播放流 CDN 域名提取器 (做视频切片直连 Direct Domain)
=============================================================================
功能：
  1. 深度请求 MacCMS 采集站的 ac=detail 详情接口；
  2. 从 vod_play_url 中精准抓取真实的 m3u8 播放切片域名 (例如 v13.rstuuv.com)；
  3. 将这些真实视频播放 CDN 域名合并导出至 domains_direct.txt 与 clash_rules_direct.yaml，
     确保路由软路由 (PassWall / SmartDNS / Clash) 能够实现视频切片直连秒播！
=============================================================================
"""

import re
import json
import ssl
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_stream_cdn_domains(sites, max_sites=20):
    """从给定的 MacCMS 站点列表中，抓取真实的 m3u8 播放域名"""
    stream_domains = set()

    def fetch_site_stream_domains(site):
        api = site.get("api", "")
        if not api or not api.startswith("http") or "csp_" in api:
            return set()

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        found = set()
        try:
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    # 抓取播放链接中的所有 m3u8 URL 域名
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$]+?\.m3u8)', raw)
                    for pu in play_urls:
                        try:
                            netloc = urllib.parse.urlparse(pu).netloc.split(":")[0]
                            # 提取根域名，例如 v13.rstuuv.com -> rstuuv.com
                            clean_dom = re.sub(r'^(www|api|v\d*|m\d*)\.', '', netloc)
                            if clean_dom and "github" not in clean_dom and "jsdelivr" not in clean_dom:
                                found.add(clean_dom)
                        except Exception: pass
        except Exception: pass
        return found

    print(f"  [视频流 CDN 提取器] 正在从前 {min(len(sites), max_sites)} 个采集站抓取真实播放切片域名...", flush=True)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_site_stream_domains, site) for site in sites[:max_sites]]
        for f in as_completed(futures):
            stream_domains.update(f.result())

    print(f"  └─ 成功捕获到 {len(stream_domains)} 个真实视频播放 CDN 直连域名！", flush=True)
    return stream_domains

if __name__ == "__main__":
    pass
