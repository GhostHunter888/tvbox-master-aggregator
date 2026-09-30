#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本三：多层级深解析播放域名提取器 (Cloudflare 403 屏蔽判定 + 全线路全量扫描)
=============================================================================
重点更新：
  1. Cloudflare 403 / 1020 "Geo-blocked / 屏蔽境外 IP" 判定：
     - 当 HTTP 请求收到 403 / 1020 时，说明对方禁止境外 IP 访问；
     - 此类站点必须走国内直连 (direct list)，立刻强行计入国内直连域名！
  2. 彻底取消 [:6] 截断，对 vod_play_url 里的所有播放线路与资源全量展开扫描；
  3. 结合本地 repos/cat/TVBOX/PY/ 下的 .py 源码做静态域名提取。
=============================================================================
"""

import os
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

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

def extract_domains_from_local_py_code():
    """从本地 repos/cat/TVBOX/PY/ 源码中静态提取硬编码的播放域名"""
    extracted = set()
    local_py_dir = os.path.join(WORK_DIR, "repos", "cat", "TVBOX", "PY")
    if os.path.exists(local_py_dir):
        for fname in os.listdir(local_py_dir):
            if fname.endswith(".py"):
                fpath = os.path.join(local_py_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        code_text = f.read()
                        code_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]\(\)]+)', code_text)
                        for u in code_urls:
                            dom = extract_root_domain(u)
                            if dom: extracted.add(dom)
                except Exception: pass
    return extracted

def resolve_deep_media_domains(sites, max_sites=200):
    """只抓域名（50 线程极速并发 + Cloudflare 403 强行归入国内直连）"""
    grouped_play_domains = {
        "top_facade_domains": set(),
        "media_player_domains": set(),
        "deep_stream_domains": set()
    }

    # 合入本地 .py 源码域名
    grouped_play_domains["deep_stream_domains"].update(extract_domains_from_local_py_code())

    maccms_sites = [s for s in sites if s.get("type") in (0, 1) and isinstance(s.get("api"), str) and s["api"].startswith("http")]

    def deep_resolve_single_site(site):
        api = site.get("api", "")
        is_top_facade = (site.get("key") == "OK资源")

        # 将站点自身的 API 域名直接加入直连
        self_dom = extract_root_domain(api)
        l2_found = {self_dom} if self_dom else set()
        l3_found = set()

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        try:
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=3.0, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    # 取消 [:6] 限制，全量扫描页面里的所有视频/切片 URL
                    play_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+)', raw)

                    for pu in play_urls:
                        if any(ext in pu.lower() for ext in ['.jpg', '.png', '.css', '.js', '.gif', '.ico']): continue
                        dom_l2 = extract_root_domain(pu)
                        if dom_l2: l2_found.add(dom_l2)

                        if any(kw in pu.lower() for kw in ['.m3u8', '/share/', '/play/']):
                            try:
                                req_play = urllib.request.Request(pu, headers=HEADERS)
                                with urllib.request.urlopen(req_play, timeout=3.0, context=SSL_CTX) as play_resp:
                                    dom_redirect = extract_root_domain(play_resp.geturl())
                                    if dom_redirect: l3_found.add(dom_redirect)
                            except urllib.error.HTTPError as e:
                                # 核心：捕获 Cloudflare 403 / 1020 屏蔽境外 IP，强行计入国内直连 (direct list)！
                                if e.code in [403, 1020, 451]:
                                    blocked_dom = extract_root_domain(pu)
                                    if blocked_dom: l2_found.add(blocked_dom)
                            except Exception: pass
        except urllib.error.HTTPError as e:
            # 捕获主 API 的 Cloudflare 403 屏蔽，归入国内直连
            if e.code in [403, 1020, 451] and self_dom:
                l2_found.add(self_dom)
        except Exception: pass

        return ("top" if is_top_facade else "normal"), l2_found, l3_found

    print(f"  [专干域名 & 403屏蔽判定] 正在对 {len(maccms_sites)} 个真实 MacCMS 站点进行域名抓取...", flush=True)
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

    print(f"  └─ 纯域名抓取完成！门面: {len(grouped_play_domains['top_facade_domains'])}个, 播放页: {len(grouped_play_domains['media_player_domains'])}个, 切片域名: {len(grouped_play_domains['deep_stream_domains'])}个", flush=True)
    return grouped_play_domains

if __name__ == "__main__":
    pass
