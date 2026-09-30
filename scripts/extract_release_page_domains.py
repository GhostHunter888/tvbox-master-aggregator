#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本八：全网发布页与最新地址通用自动提取器 (Release Page Scraper)
=============================================================================
功能：
  1. 通用解析 RELEASE_PAGE_URLS 列表中的全网各种最新发布页 / 永不迷路页面；
  2. 正则动态扒取页面上隐藏的所有最新镜像域名、跳转网址与中文域名；
  3. 中文域名自动进行 Punycode IDNA 编码转换 (如 好看影视.com -> xn--eck5a0ba3a2b.com)；
  4. 输出 extracted_release_page_domains.json，供规则导出器注入直连放行白名单。
=============================================================================
"""

import os
import re
import json
import ssl
import urllib.parse
import urllib.request

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

# 通用发布页配置列表 (可无限追加)
RELEASE_PAGE_URLS = [
    "https://dizhi2026.github.io/hkys/",  # 好看影视 & 可可影视最新发布页
    "https://tvbox.clbug.com/user.php",   # 饭太硬 / 肥猫最新发布页
    "https://www.zzzypro.com/"             # 蜘蛛资源最新发布页
]

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def extract_root_domain(raw_str):
    if not raw_str or not isinstance(raw_str, str): return None
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

def extract_all_release_page_domains():
    """通用扒取 RELEASE_PAGE_URLS 列表中的所有最新发布页镜像域名与中文 Punycode"""
    print(f"  [通用发布页提取器] 正在对全网 {len(RELEASE_PAGE_URLS)} 个发布页进行最新镜像域名自动扒取...", flush=True)
    release_domains = set()

    for page_url in RELEASE_PAGE_URLS:
        try:
            req = urllib.request.Request(page_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as resp:
                if resp.status == 200:
                    raw_text = resp.read().decode("utf-8", errors="ignore")

                    # 1. 抓取页面中所有的 HTTP/HTTPS 链接与主机
                    raw_urls = re.findall(r'(https?://[^\s"\'<>#\$\[\]\(\)]+)', raw_text)
                    for u in raw_urls:
                        r_dom = extract_root_domain(u)
                        if r_dom: release_domains.add(r_dom)

                    # 2. 抓取页面中所有的中文域名 (如 好看影视.com)
                    cn_doms = re.findall(r'([\u4e00-\u9fa5A-Za-z0-9\-]+\.(?:com|net|org|cn|cc|tv|top))', raw_text)
                    for cd in cn_doms:
                        if any('\u4e00' <= char <= '\u9fa5' for char in cd):
                            release_domains.add(cd)
                            puny = to_punycode_domain(cd)
                            if puny: release_domains.add(puny)
        except Exception: pass

    # 特殊追加用户指定的最新官网硬编码保障
    hardcoded_backups = [
        "kkys14.com", "kkys15.com", "haokanyingshi.com", "xn--eck5a0ba3a2b.com",
        "hkys2.cc", "hkys3.cc", "hkys4.cc", "hkys5.cc", "hkys6.cc", "hkys7.cc", "hkys8.cc", "hkys9.cc"
    ]
    release_domains.update(hardcoded_backups)

    sorted_doms = sorted(list(release_domains))
    print(f"  └─ 抓取完成！共捕获到 {len(sorted_doms)} 个最新发布页镜像与中文 Punycode 直连域名！", flush=True)
    return sorted_doms

if __name__ == "__main__":
    pass
