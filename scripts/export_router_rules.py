#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本：基于 Mozilla PSL 算法与纯 IP CIDR 支持的全量路由器规则导出器
=============================================================================
重点更新：
  1. 取消对纯 IP 地址 (IPv4) 的擦除丢弃！
  2. 纯 IP 自动识别并生成 Clash 标准语法：- IP-CIDR,124.223.214.31/32；
  3. PassWall (domains_direct.txt) 与 AdGuard Home (adguard_direct.txt) 包含纯 IP 直连；
  4. 彻底解决纯 IP 视频切片服务器跑去走代理节点 (漏网之鱼) 的偷跑硬伤！
=============================================================================
"""

import os
import re
import urllib.parse

try:
    import tldextract
    TLD_EXTRACTOR = tldextract.TLDExtract(include_psl_private_domains=False)
except ImportError:
    TLD_EXTRACTOR = None

def parse_host_type(raw_str):
    """解析网址中的主机：自动区分纯 IP 地址 (124.223.x.x) 与 域名 (domain.com)"""
    if not raw_str or not isinstance(raw_str, str):
        return None, None

    clean_str = raw_str.split("|")[0].split("$")[0].strip()

    url_match = re.search(r'https?://([^\s"\'/<>#\$:]+)', clean_str)
    if url_match:
        host = url_match.group(1).split(":")[0]
    else:
        host = clean_str.split("/")[0].split(":")[0].strip()

    host = host.strip("@|*^ \t\r\n").lower()
    if not host or "." not in host:
        return None, None

    # 1. 判断是否为 IPv4 纯数字地址
    ip_parts = host.split(".")
    if len(ip_parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in ip_parts):
        return "ip", host

    # 2. 如果是域名，使用 Mozilla PSL 算法提取二级主域名
    if TLD_EXTRACTOR:
        ext = TLD_EXTRACTOR(clean_str)
        if ext.domain and ext.suffix:
            root = f"{ext.domain}.{ext.suffix}".lower().strip()
            if root and "github" not in root and "jsdelivr" not in root:
                return "domain", root
        return None, None
    else:
        parts = host.split(".")
        if len(parts) >= 3:
            if parts[-2] in ["com", "net", "org", "gov", "edu", "co"] and parts[-1] in ["cn", "uk", "jp", "kr", "hk", "tw", "au", "nz", "sg"]:
                root = ".".join(parts[-3:])
            else:
                root = ".".join(parts[-2:])
        else:
            root = host
        return "domain", root if "github" not in root and "jsdelivr" not in root else None, None

def export_grouped_router_rules(work_dir, sites, grouped_cdn_domains, dynamic_image_domains=None):
    print("  [策略导出器] 正在导出带备注分组规则 (全面支持 域名 + 纯 IP CIDR 直连)...", flush=True)

    PROXY_KEYWORDS = ["(墙)", "墙外", "代理", "翻墙", "科学", "科学上网"]

    api_direct_domains = set()
    api_direct_ips = set()
    proxy_domains = set()

    for s in sites:
        name = str(s.get("name", ""))
        key = str(s.get("key", ""))
        is_proxy_site = any(kw in name or kw in key for kw in PROXY_KEYWORDS)

        extracted_urls = []
        for prop in ["api", "ext", "jar", "pic"]:
            val = s.get(prop)
            if isinstance(val, str):
                extracted_urls.append(val)
            elif isinstance(val, dict):
                extracted_urls.extend([str(v) for v in val.values() if isinstance(v, str)])

        for u_str in extracted_urls:
            htype, item = parse_host_type(u_str)
            if item:
                if is_proxy_site or "github" in item or "jsdelivr" in item:
                    proxy_domains.add(item)
                else:
                    if htype == "ip":
                        api_direct_ips.add(item)
                    else:
                        api_direct_domains.add(item)

    # 处理深解析出来的域名与纯 IP
    top_cdn_doms, top_cdn_ips = set(), set()
    l2_play_doms, l2_play_ips = set(), set()
    l3_ts_doms, l3_ts_ips = set(), set()

    if isinstance(grouped_cdn_domains, dict):
        for raw_item in grouped_cdn_domains.get("top_facade_domains", set()):
            htype, item = parse_host_type(raw_item)
            if item: (top_cdn_ips if htype == "ip" else top_cdn_doms).add(item)

        for raw_item in grouped_cdn_domains.get("media_player_domains", set()):
            htype, item = parse_host_type(raw_item)
            if item: (l2_play_ips if htype == "ip" else l2_play_doms).add(item)

        for raw_item in grouped_cdn_domains.get("deep_stream_domains", set()):
            htype, item = parse_host_type(raw_item)
            if item: (l3_ts_ips if htype == "ip" else l3_ts_doms).add(item)

    img_doms = sorted(list(set(dynamic_image_domains or [])))

    groups = [
        ("01_门面节点_OK资源与播放直连", sorted(list(top_cdn_doms)), sorted(list(top_cdn_ips))),
        ("02_控制面_API服务与海报图片", sorted(list(api_direct_domains)), sorted(list(api_direct_ips))),
        ("03_二级_播放页与M3U8直连", sorted(list(l2_play_doms)), sorted(list(l2_play_ips))),
        ("04_三级_深层TS视频切片边缘服务器", sorted(list(l3_ts_doms)), sorted(list(l3_ts_ips))),
        ("05_海报图片_CDN放行域名", img_doms, [])
    ]

    # 1. 导出 PassWall / SmartDNS 直连列表 (domains_direct.txt - 包含域名与纯 IP)
    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# =========================================================\n")
        f.write("# TVBox 视频源、海报图片 CDN 与三层 M3U8/TS 播放 CDN/纯IP 国内直连列表\n")
        f.write("# =========================================================\n\n")
        for g_title, dom_list, ip_list in groups:
            if dom_list or ip_list:
                f.write(f"# ===== 分组: {g_title} =====\n")
                for d in dom_list: f.write(f"{d}\n")
                for ip in ip_list: f.write(f"{ip}\n")
                f.write("\n")

    # 2. 导出 AdGuard Home 放行白名单规则集 (adguard_direct.txt)
    with open(os.path.join(work_dir, "adguard_direct.txt"), "w", encoding="utf-8") as f:
        f.write("! =========================================================\n")
        f.write("! OpenWrt AdGuard Home TVBox 视频源、海报图片与播放 CDN/纯IP 放行白名单规则\n")
        f.write("! =========================================================\n\n")
        for g_title, dom_list, ip_list in groups:
            if dom_list or ip_list:
                f.write(f"! ===== 分组: {g_title} =====\n")
                for d in dom_list: f.write(f"@@||{d}^\n")
                for ip in ip_list: f.write(f"@@||{ip}^\n")
                f.write("\n")

    # 3. 导出 Clash 直连规则集 (clash_rules_direct.yaml - 区分 DOMAIN-SUFFIX 与 IP-CIDR)
    with open(os.path.join(work_dir, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# =========================================================\n")
        f.write("# TVBox 视频源、海报图片 CDN 与三层 M3U8/TS 播放 CDN/纯IP Clash 直连规则集\n")
        f.write("# =========================================================\n")
        f.write("payload:\n")
        for g_title, dom_list, ip_list in groups:
            if dom_list or ip_list:
                f.write(f"  # ===== 分组: {g_title} =====\n")
                for d in dom_list:
                    f.write(f"  - DOMAIN-SUFFIX,{d}\n")
                for ip in ip_list:
                    f.write(f"  - IP-CIDR,{ip}/32\n")

    # 4. 导出强制代理规则列表
    sorted_proxy = sorted(list(proxy_domains))
    with open(os.path.join(work_dir, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 强制代理域名列表 (含 '(墙)' 节点)\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    with open(os.path.join(work_dir, "adguard_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home 强制代理域名放行规则\n")
        for d in sorted_proxy: f.write(f"@@||{d}^\n")

    with open(os.path.join(work_dir, "clash_rules_proxy.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 强制代理 Clash 规则集\npayload:\n")
        for d in sorted_proxy:
            if d.replace('.', '').isdigit():
                f.write(f"  - IP-CIDR,{d}/32\n")
            else:
                f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 成功导出 PassWall 直连列表 (含域名 + 纯IP): domains_direct.txt")
    print(f"  ├─ 成功导出 AdGuard Home 放行白名单: adguard_direct.txt (@@||domain^)")
    print(f"  └─ 成功导出 Clash 规则集 (含 DOMAIN-SUFFIX 与 IP-CIDR): clash_rules_direct.yaml")

def export_all_router_rules(work_dir, sites, deep_cdn_domains, dynamic_image_domains=None):
    return export_grouped_router_rules(work_dir, sites, deep_cdn_domains, dynamic_image_domains)

if __name__ == "__main__":
    pass
