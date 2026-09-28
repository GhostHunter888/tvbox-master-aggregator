#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本五：海报图片 CDN 域名全动态提取器 (Extract Image CDN Domains)
=============================================================================
功能：
  1. 彻底不靠任何手写穷举硬编码，全量并发向各站点发起 ac=detail 请求；
  2. 正则动态扒取 XML/JSON 内部所有 .jpg / .jpeg / .png / .webp 海报图片 URL；
  3. 调用 Mozilla PSL 官方算法动态解析海报图片服务器的主域名 (如 zyxpedu.com, fffgood.com, okzyw.xyz)；
  4. 供规则导出器注入放行白名单，彻底解决电视盒子海报大颜色框显示失败难题。
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

def extract_all_poster_image_domains(sites, max_sites=150):
    """全动态并发扒取全网所有站点的海报图片 CDN 域名 (零穷举硬编码)"""
    print(f"  [海报图片扒取器] 正在对全网 {min(len(sites), max_sites)} 个有效站点并发扒取海报图片 CDN 域名...", flush=True)
    image_domains = set()

    def fetch_site_poster_domains(site):
        api = site.get("api", "")
        if not api or not isinstance(api, str) or not api.startswith("http") or "csp_" in api:
            return set()

        base_api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I).rstrip("/")
        detail_url = base_api + ("&ac=detail" if "?" in base_api else "?ac=detail")

        found_img_doms = set()
        try:
            req = urllib.request.Request(detail_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw_text = resp.read().decode("utf-8", errors="ignore")
                    # 动态匹配所有 .jpg / .jpeg / .png / .webp 格式的海报 URL
                    img_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]]+?\.(?:jpg|jpeg|png|webp))', raw_text, re.IGNORECASE)
                    for img_u in img_urls:
                        img_dom = extract_root_domain(img_u)
                        if img_dom:
                            found_img_doms.add(img_dom)
        except Exception: pass

        return found_img_doms

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(fetch_site_poster_domains, site) for site in sites[:max_sites]]
        for f in as_completed(futures):
            image_domains.update(f.result())

    print(f"  └─ 动态海报扒取完成！共全自动捕获到 {len(image_domains)} 个海报图片 CDN 放行主域名！", flush=True)
    return list(sorted(image_domains))

if __name__ == "__main__":
    pass
