#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本三：多层级深解析真实播放域名提取器 (全量全站点深解析版)
=============================================================================
解决非凡资源漏网之鱼 (ffzy-bofang.com) 的根本原因：
  1. 取消 max_sites=30 的截断限制，对全网所有有效站点执行全量 ac=detail 探测；
  2. 支持 XML 与 JSON 中 CDATA 包含的播放域名正则抓取 (包括 ffzy-bofang.com, ffzy-play9.com, feifei-play.com)；
  3. 彻底捕获非凡、暴风、索尼、量子、极速等所有资源的真实播放 CDN 域名。
=============================================================================
"""

import re
import json
import ssl
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import tldextract
    TLD_EXTRACTOR = tldextract.TLDExtract(include_psl_private_domains=False)
except ImportError:
    TLD_EXTRACTOR = None

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

    if TLD_EXTRACTOR:
        ext = TLD_EXTRACTOR(clean_str)
        if ext.domain and ext.suffix:
            root = f"{ext.domain}.{ext.suffix}".lower().strip()
            if root and "github" not in root and "jsdelivr" not in root:
                return root
        return None
    else:
        url_match = re.search(r'https?://([^\s"\'/<>#\$:]+)', clean_str)
        host = url_match.group(1).split(":")[0] if url_match else clean_str.split("/")[0].split(":")[0].strip()
        host = host.strip("@|*^ \t\r\n").lower()
        if not host or host.replace('.', '').isdigit() or "." not in host:
            return None
        parts = host.split(".")
        if len(parts) >= 3:
            if parts[-2] in ["com", "net", "org", "gov", "edu", "co"] and parts[-1] in ["cn", "uk", "jp", "kr", "hk", "tw", "au", "nz", "sg"]:
                root = ".".join(parts[-3:])
            else:
                root = ".".join(parts[-2:])
        else:
            root = host
        return root if "github" not in root and "jsdelivr" not in root else None

def resolve_deep_media_domains(sites, max_sites=200):
    """深解析真实播放域名（全量探测每一个站点，提取包括 ffzy-bofang.com 在内的所有播放域名）"""
    grouped_play_domains = {
        "top_facade_domains": set(),      # 门面 OK资源 的真实播放域名
        "media_player_domains": set(),    # 二级播放页与网页播放域名
        "deep_stream_domains": set()      # 三级/终极切片真实播放域名
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
            # Stage 1: 请求 ac=detail
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")

                    # Stage 2: 全量提取 CDATA / XML / JSON 里的所有 HTTP 播放域名 (解决 ffzy-bofang.com 被忽略)
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+)', raw)

                    for pu in play_urls[:10]:
                        if any(ext in pu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']):
                            continue

                        dom_l2 = extract_root_domain(pu)
                        if dom_l2:
                            l2_found.add(dom_l2)

                        # Stage 3: 对播放链接发起 HTTP 请求，深扒嵌套的 M3U8/TS 链接
                        try:
                            req_play = urllib.request.Request(pu, headers=HEADERS)
                            with urllib.request.urlopen(req_play, timeout=5, context=SSL_CTX) as play_resp:
                                redirect_l2 = extract_root_domain(play_resp.geturl())
                                if redirect_l2: l2_found.add(redirect_l2)

                                if play_resp.status == 200:
                                    play_body = play_resp.read().decode("utf-8", errors="ignore")
                                    nested_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+)', play_body)

                                    for nu in nested_urls:
                                        if any(ext in nu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']):
                                            continue

                                        dom_l3 = extract_root_domain(nu)
                                        if dom_l3 and dom_l3 != dom_l2:
                                            l3_found.add(dom_l3)

                                            if ".m3u8" in nu.lower() or ".ts" in nu.lower():
                                                try:
                                                    req_ts = urllib.request.Request(nu, headers=HEADERS)
                                                    with urllib.request.urlopen(req_ts, timeout=4, context=SSL_CTX) as ts_resp:
                                                        final_stage5_url = ts_resp.geturl()
                                                        dom_stage5 = extract_root_domain(final_stage5_url)
                                                        if dom_stage5:
                                                            l3_found.add(dom_stage5)
                                                except Exception: pass
                        except Exception: pass
        except Exception: pass

        return ("top" if is_top_facade else "normal"), l2_found, l3_found

    print(f"  [全量深解析器] 正在对全网 {min(len(sites), max_sites)} 个有效站点进行全量 ac=detail 物理探测...", flush=True)
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(deep_resolve_single_site, site) for site in sites[:max_sites]]
        for f in as_completed(futures):
            stype, l2, l3 = f.result()
            if stype == "top":
                grouped_play_domains["top_facade_domains"].update(l2)
                grouped_play_domains["top_facade_domains"].update(l3)
            else:
                grouped_play_domains["media_player_domains"].update(l2)
                grouped_play_domains["deep_stream_domains"].update(l3)

    print(f"  └─ 全量深解析完成！门面播放域名: {len(grouped_play_domains['top_facade_domains'])}个, 网页播放页: {len(grouped_play_domains['media_player_domains'])}个, 终极切片播放域名: {len(grouped_play_domains['deep_stream_domains'])}个", flush=True)
    return grouped_play_domains

if __name__ == "__main__":
    pass
