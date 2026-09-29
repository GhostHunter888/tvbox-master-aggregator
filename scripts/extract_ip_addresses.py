#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本七：纯 IPv4 地址提取与中文域名 Punycode IDNA DNS 自动解析器
=============================================================================
重点修复：
  1. 增加中文域名 Punycode IDNA 自动转码支持 (如 摸鱼儿.top -> xn--9kqr9lk79c.top)；
  2. 解决中文域名在 socket.gethostbyname 中抛出 UnicodeEncodeError 导致的 DNS 解析失败硬伤；
  3. 扒取 M3U8、TS 切片及 API 里的纯 IPv4 地址，输出 extracted_ip_addresses.json。
=============================================================================
"""

import os
import re
import json
import socket
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_valid_ipv4(ip_str):
    if not ip_str or not isinstance(ip_str, str):
        return False
    parts = ip_str.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

def to_punycode_domain(dom_str):
    """将中文域名自动转码为标准的 Punycode (IDNA) 格式，解决 DNS 解析崩溃问题"""
    if not dom_str or not isinstance(dom_str, str):
        return None
    try:
        # 如果包含非 ASCII 中文字符，进行 IDNA 编码
        return dom_str.encode("idna").decode("ascii")
    except Exception:
        return dom_str

def extract_ip_addresses_and_dns(sites, domain_dict=None):
    """专门抓取纯 IPv4 地址并对域名 (含中文 Punycode) 执行 DNS 反向解析"""
    print("  [专干 IP & 中文 Punycode] 正在扒取纯 IPv4 地址并执行 DNS 反向解析...", flush=True)
    extracted_ips = set()

    # 1. 扫描本地文件 (live.txt, tvbox.json, sources.txt, .py 源码) 中的所有 IPv4 地址
    scan_files = [
        os.path.join(WORK_DIR, "live.txt"),
        os.path.join(WORK_DIR, "tvbox.json"),
        os.path.join(WORK_DIR, "sources.txt"),
        os.path.join(WORK_DIR, "not_suitable", "live.txt")
    ]

    local_py_dir = os.path.join(WORK_DIR, "repos", "cat", "TVBOX", "PY")
    if os.path.exists(local_py_dir):
        for fname in os.listdir(local_py_dir):
            if fname.endswith(".py"):
                scan_files.append(os.path.join(local_py_dir, fname))

    for fpath in scan_files:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
                    for ip in ips:
                        if is_valid_ipv4(ip) and not ip.startswith("127.") and not ip.startswith("0."):
                            extracted_ips.add(ip)
            except Exception: pass

    # 2. 从传入的视频播放域名 (支持中文 IDNA) 发起系统 DNS 实时反向解析得到物理 IP
    domains_to_resolve = set()
    if isinstance(domain_dict, dict):
        for key in ["top_facade_domains", "media_player_domains", "deep_stream_domains"]:
            domains_to_resolve.update(domain_dict.get(key, set()))

    for site in sites[:150]:
        api = site.get("api", "")
        if isinstance(api, str) and api.startswith("http"):
            host = urllib.parse.urlparse(api).netloc.split(":")[0]
            if is_valid_ipv4(host):
                extracted_ips.add(host)
            elif host and "." in host:
                domains_to_resolve.add(host)

    def resolve_domain_to_ip(dom):
        # 核心：将中文域名转码为 Punycode 后再发起 DNS 解析
        puny_dom = to_punycode_domain(dom)
        found_ip = None
        try:
            found_ip = socket.gethostbyname(puny_dom)
            if is_valid_ipv4(found_ip) and not found_ip.startswith("127."):
                return found_ip
        except Exception: pass
        return None

    socket.setdefaulttimeout(3.0)
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(resolve_domain_to_ip, dom) for dom in list(domains_to_resolve)[:200]]
        for f in as_completed(futures):
            res_ip = f.result()
            if res_ip:
                extracted_ips.add(res_ip)

    sorted_ips = sorted(list(extracted_ips))
    print(f"  └─ 纯 IP 抓取与中文 Punycode DNS 解析完成！共捕获到 {len(sorted_ips)} 个物理 IPv4 地址！", flush=True)
    return sorted_ips

if __name__ == "__main__":
    pass
