#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本七：纯 IPv4 地址提取与视频域名 DNS 自动解析器 (专干 IP，单一职责)
=============================================================================
功能：
  1. 专门扒取 M3U8、TS 切片及 API 里的纯 IPv4 地址 (如 124.223.214.31)；
  2. 对提取到的关键视频域名发起 DNS 实时解析 (socket.gethostbyname) 强行拿到底层数字 IP；
  3. 输出纯 IP 缓存文件 extracted_ip_addresses.json。
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

def extract_ip_addresses_and_dns(sites, domain_dict=None):
    """专门抓取纯 IPv4 地址并执行 DNS 反向解析 (专干 IP，单一职责)"""
    print("  [专干 IP] 正在扒取纯 IPv4 地址并执行 DNS 域名反向解析...", flush=True)
    extracted_ips = set()

    # 1. 从本地 .py 源码文本中强抓纯 IPv4 地址
    local_py_dir = os.path.join(WORK_DIR, "repos", "cat", "TVBOX", "PY")
    if os.path.exists(local_py_dir):
        for fname in os.listdir(local_py_dir):
            if fname.endswith(".py"):
                fpath = os.path.join(local_py_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
                        for ip in ips:
                            if is_valid_ipv4(ip) and not ip.startswith("127.") and not ip.startswith("0."):
                                extracted_ips.add(ip)
                except Exception: pass

    # 2. 从传入的视频播放域名中，批量发起系统 DNS 实时反向解析得到物理 IP！
    domains_to_resolve = set()
    if isinstance(domain_dict, dict):
        for key in ["top_facade_domains", "media_player_domains", "deep_stream_domains"]:
            domains_to_resolve.update(domain_dict.get(key, set()))

    for site in sites[:100]:
        api = site.get("api", "")
        if isinstance(api, str) and api.startswith("http"):
            host = urllib.parse.urlparse(api).netloc.split(":")[0]
            if is_valid_ipv4(host):
                extracted_ips.add(host)
            elif host and "." in host:
                domains_to_resolve.add(host)

    def resolve_domain_to_ip(dom):
        found_ip = None
        try:
            found_ip = socket.gethostbyname(dom)
            if is_valid_ipv4(found_ip) and not found_ip.startswith("127."):
                return found_ip
        except Exception: pass
        return None

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(resolve_domain_to_ip, dom) for dom in list(domains_to_resolve)[:150]]
        for f in as_completed(futures):
            res_ip = f.result()
            if res_ip:
                extracted_ips.add(res_ip)

    sorted_ips = sorted(list(extracted_ips))
    print(f"  └─ 纯 IP 抓取与 DNS 解析完成！共全自动捕获到 {len(sorted_ips)} 个物理 IPv4 地址！", flush=True)
    return sorted_ips

if __name__ == "__main__":
    pass
