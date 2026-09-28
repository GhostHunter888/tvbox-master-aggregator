#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本三：多层级深解析播放 CDN 域名提取器 (Deep CDN Edge Host Resolver)
=============================================================================
分类分组：
  1. top_facade_cdn      : 门面节点 (OK资源) 的播放 CDN 域名
  2. media_player_domains: 二级播放页与 M3U8 域名
  3. deep_ts_cdn_domains : 三级深层真实 TS 视频切片 CDN 边缘域名
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

def extract_root_domain(raw_str):
    if not raw_str or not isinstance(raw_str, str):
        return None

    clean_str = raw_str.split("|")[0].split("$")[0].strip()
    url_match = re.search(r'https?://([^\s"\'/<>#\$:]+)', clean_str)
    if url_match:
        host = url_match.group(1).split(":")[0]
    else:
        host = clean_str.split("/")[0].split(":")[0].strip()

    host = host.strip("@|*^ \t\r\n").lower()
    if not host or host.replace('.', '').isdigit() or "." not in host:
        return None

    parts = host.split(".")
    if len(parts) >= 3:
        if parts[-2] in ["com", "net", "org", "gov", "edu", "co"] and parts[-1] in ["cn", "uk", "jp", "kr", "hk", "tw"]:
            root = ".".join(parts[-3:])
        else:
            root = ".".join(parts[-2:])
    else:
        root = host

    root = root.strip()
    if root and "github" not in root and "jsdelivr" not in root and "." in root:
        return root
    return None

def resolve_deep_media_domains(sites, max_sites=30):
    """三层深度递归解析：抓取终极 TS 切片 CDN 域名并返回按功能分组的字典"""
    grouped_cdn_domains = {
        "top_facade_cdn": set(),
        "media_player_domains": set(),
        "deep_ts_cdn_domains": set()
    }

    def deep_resolve_single_site(site):
        api = site.get("api", "")
        is_top_facade = (site.get("key") == "OK资源")

        if not api or not isinstance(api, str) or not api.startswith("http") or "csp_" in api:
            return ("normal", set(), set())

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        l2_found = set()
        l3_found = set()

        try:
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    # 层级 2: 抓取 vod_play_url 里面的所有二级播放链接 (不限制 .m3u8，提取包含 jimaoys95.com 网页播放页在内的所有链接)
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$]+)', raw)

                    for pu in play_urls[:10]:
                        if any(ext in pu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']):
                            continue
                        try:
                            dom_l2 = extract_root_domain(pu)
                            if dom_l2:
                                l2_found.add(dom_l2)

                            # 层级 3: 发起深层请求，抓取 M3U8 文件内部嵌套的终极 TS 切片 CDN 域名
                            if ".m3u8" in pu.lower():
                                req_m3u8 = urllib.request.Request(pu, headers=HEADERS)
                                with urllib.request.urlopen(req_m3u8, timeout=4, context=SSL_CTX) as m3u8_resp:
                                    if m3u8_resp.status == 200:
                                        m3u8_text = m3u8_resp.read().decode("utf-8", errors="ignore")
                                        ts_urls = re.findall(r'(https?://[^\s"\'<>#\$]+)', m3u8_text)
                                        for tu in ts_urls:
                                            dom_l3 = extract_root_domain(tu)
                                            if dom_l3:
                                                l3_found.add(dom_l3)
                        except Exception: pass
        except Exception: pass

        return ("top" if is_top_facade else "normal"), l2_found, l3_found

    print(f"  [深层 CDN 提取器] 正在执行多层级物理探测 (API ➔ M3U8/网页播放页 ➔ 终极 TS 切片 CDN)...", flush=True)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(deep_resolve_single_site, site) for site in sites[:max_sites]]
        for f in as_completed(futures):
            stype, l2, l3 = f.result()
            if stype == "top":
                grouped_cdn_domains["top_facade_cdn"].update(l2)
                grouped_cdn_domains["top_facade_cdn"].update(l3)
            else:
                grouped_cdn_domains["media_player_domains"].update(l2)
                grouped_cdn_domains["deep_ts_cdn_domains"].update(l3)

    print(f"  └─ 深层 CDN 探测完成！抓取到 门面节点CDN: {len(grouped_cdn_domains['top_facade_cdn'])}个, 播放页: {len(grouped_cdn_domains['media_player_domains'])}个, 终极TS切片: {len(grouped_cdn_domains['deep_ts_cdn_domains'])}个", flush=True)
    return grouped_cdn_domains

if __name__ == "__main__":
    pass
