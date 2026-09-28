#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本三：多层级深解析真实播放域名与纯 IP 提取器 (含 IPv4 支持)
=============================================================================
重点修复：
  1. 修复 extract_root_domain 遇到纯 IPv4 地址 (如 124.223.214.31) 被 tldextract 误删丢弃的重大 Bug；
  2. 纯 IPv4 地址原样保留并存入 grouped_cdn_domains.json；
  3. 使得 export_router_rules 能够 100% 正确输出 Clash 的 IP-CIDR 与 PassWall 纯 IP 直连规则。
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

    url_match = re.search(r'https?://([^\s"\'/<>#\$:]+)', clean_str)
    if url_match:
        host = url_match.group(1).split(":")[0]
    else:
        host = clean_str.split("/")[0].split(":")[0].strip()

    host = host.strip("@|*^ \t\r\n").lower()
    if not host or "." not in host:
        return None

    # 关键修复：优先判断是否为 IPv4 纯数字地址，如果是原样保留返回！
    ip_parts = host.split(".")
    if len(ip_parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in ip_parts):
        return host

    if TLD_EXTRACTOR:
        ext = TLD_EXTRACTOR(clean_str)
        if ext.domain and ext.suffix:
            root = f"{ext.domain}.{ext.suffix}".lower().strip()
            if root and "github" not in root and "jsdelivr" not in root:
                return root
        return None
    else:
        parts = host.split(".")
        if len(parts) >= 3:
            if parts[-2] in ["com", "net", "org", "gov", "edu", "co"] and parts[-1] in ["cn", "uk", "jp", "kr", "hk", "tw", "au", "nz", "sg"]:
                root = ".".join(parts[-3:])
            else:
                root = ".".join(parts[-2:])
        else:
            root = host
        return root if "github" not in root and "jsdelivr" not in root else None

def resolve_deep_media_domains(sites, max_sites=30):
    """深解析真实播放域名与纯 IP 地址"""
    grouped_play_domains = {
        "top_facade_domains": set(),      # 门面 OK资源 的真实播放域名与 IP
        "media_player_domains": set(),    # Stage 2 网页播放域名
        "deep_stream_domains": set()      # Stage 5 终极切片播放域名与 IP
    }

    # 过滤出真正的 MacCMS HTTP 站点
    maccms_sites = [s for s in sites if s.get("type") in (0, 1) and isinstance(s.get("api"), str) and s["api"].startswith("http")]

    def deep_resolve_single_site(site):
        api = site.get("api", "")
        is_top_facade = (site.get("key") == "OK资源")

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        l2_found = set()
        l3_found = set()

        try:
            # Stage 1: 请求 ac=detail
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=2.5, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")

                    # Stage 2: 抓取 vod_play_url 里的所有播放链接
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+)', raw)

                    for pu in play_urls[:8]:
                        if any(ext in pu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']):
                            continue

                        dom_l2 = extract_root_domain(pu)
                        if dom_l2:
                            l2_found.add(dom_l2)

                        # Stage 3: 请求播放页，追踪 302 重定向
                        try:
                            req_play = urllib.request.Request(pu, headers=HEADERS)
                            with urllib.request.urlopen(req_play, timeout=2.5, context=SSL_CTX) as play_resp:
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

                                            # Stage 4 & Stage 5: 请求 .m3u8 追踪 302 终极 CDN/IP 域名！
                                            if ".m3u8" in nu.lower() or ".ts" in nu.lower():
                                                try:
                                                    req_ts = urllib.request.Request(nu, headers=HEADERS)
                                                    with urllib.request.urlopen(req_ts, timeout=2.5, context=SSL_CTX) as ts_resp:
                                                        final_stage5_url = ts_resp.geturl()
                                                        dom_stage5 = extract_root_domain(final_stage5_url)
                                                        if dom_stage5:
                                                            l3_found.add(dom_stage5)

                                                        if ts_resp.status == 200 and ".m3u8" in nu.lower():
                                                            ts_text = ts_resp.read().decode("utf-8", errors="ignore")
                                                            final_ts_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+)', ts_text)
                                                            for tu in final_ts_urls[:5]:
                                                                dom_l5 = extract_root_domain(tu)
                                                                if dom_l5: l3_found.add(dom_l5)
                                                except Exception: pass
                        except Exception: pass
        except Exception: pass

        return ("top" if is_top_facade else "normal"), l2_found, l3_found

    print(f"  [Stage 5 真实 IP/域名提取器] 正在探测视频域名与纯 IPv4 地址...", flush=True)
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(deep_resolve_single_site, site) for site in maccms_sites]
        for f in as_completed(futures):
            stype, l2, l3 = f.result()
            if stype == "top":
                grouped_play_domains["top_facade_domains"].update(l2)
                grouped_play_domains["top_facade_domains"].update(l3)
            else:
                grouped_play_domains["media_player_domains"].update(l2)
                grouped_play_domains["deep_stream_domains"].update(l3)

    print(f"  └─ 探测完成！门面域名/IP: {len(grouped_play_domains['top_facade_domains'])}个, 播放页: {len(grouped_play_domains['media_player_domains'])}个, 终极切片: {len(grouped_play_domains['deep_stream_domains'])}个", flush=True)
    return grouped_play_domains

if __name__ == "__main__":
    pass
