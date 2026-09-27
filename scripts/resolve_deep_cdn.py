#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本三：多层级深度播放 CDN 域名解析器 (Deep Video Stream CDN Resolver)
=============================================================================
多层级解析链路：
  层级 1 (API 根地址) -> 层级 2 (ac=detail 获取 vod_play_url 播放页/m3u8)
  -> 层级 3 (深层解析 M3U8/TS 切片或 iFrame 网页播放器，获取最终真实媒体 CDN 域名)
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

def resolve_deep_media_domains(sites, max_sites=30):
    """三层深度递归解析：获取最终级别的播放器/切片 CDN 域名"""
    final_domains = set()

    def deep_resolve_site(site):
        api = site.get("api", "")
        if not api or not isinstance(api, str) or not api.startswith("http") or "csp_" in api:
            return set()

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        site_domains = set()
        try:
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    # 层级 2: 抓取 vod_play_url 里面的所有二级播放链接
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$]+)', raw)

                    for pu in play_urls[:10]: # 对前 10 条播放地址做三层深解析
                        if any(ext in pu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']):
                            continue
                        try:
                            # 提取二级域名 (如 jimaoys95.com 或 v13.rstuuv.com)
                            netloc = urllib.parse.urlparse(pu).netloc.split(":")[0]
                            clean_dom = re.sub(r'^(www|api|v\d*|m\d*)\.', '', netloc)
                            if clean_dom and "github" not in clean_dom and "jsdelivr" not in clean_dom:
                                site_domains.add(clean_dom)

                            # 层级 3: 发起深层请求，抓取 M3U8 Master Playlist 内部重定向的终极 TS 切片 CDN 域名
                            if ".m3u8" in pu.lower():
                                req_m3u8 = urllib.request.Request(pu, headers=HEADERS)
                                with urllib.request.urlopen(req_m3u8, timeout=4, context=SSL_CTX) as m3u8_resp:
                                    if m3u8_resp.status == 200:
                                        m3u8_text = m3u8_resp.read().decode("utf-8", errors="ignore")
                                        # 抓取 m3u8 文件内部嵌套的终极 TS 域名
                                        ts_urls = re.findall(r'(https?://[^\s"\'<>#\$]+)', m3u8_text)
                                        for tu in ts_urls:
                                            ts_netloc = urllib.parse.urlparse(tu).netloc.split(":")[0]
                                            ts_clean_dom = re.sub(r'^(www|api|v\d*|m\d*)\.', '', ts_netloc)
                                            if ts_clean_dom and "github" not in ts_clean_dom:
                                                site_domains.add(ts_clean_dom)
                        except Exception: pass
        except Exception: pass
        return site_domains

    print(f"  [多层级深解析器] 正在执行【层级1 API -> 层级2 播放页/M3U8 -> 层级3 终极 TS 切片 CDN】三层递归解析...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(deep_resolve_site, site) for site in sites[:max_sites]]
        for f in as_completed(futures):
            final_domains.update(f.result())

    print(f"  └─ 三层递归深解析完成！共捕获到 {len(final_domains)} 个终极视频 CDN 与播放页直连域名", flush=True)
    return final_domains

if __name__ == "__main__":
    pass
