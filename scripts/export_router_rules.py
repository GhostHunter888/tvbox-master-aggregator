#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本：PassWall / Clash / OpenWrt AdGuard Home 全量策略规则导出器
=============================================================================
功能：
  1. 深度提取 site 中的 api、ext、jar 里的全部域名；
  2. 智能识别含 "(墙)"、"墙外"、"科学"、"代理"、"翻墙" 的节点，将其归入强制代理列表；
  3. 导出 PassWall/SmartDNS txt 列表；
  4. 导出 Clash yaml 规则集；
  5. 导出 OpenWrt AdGuard Home 放行白名单规则 (@@||domain^ 格式)！
=============================================================================
"""

import os
import re
import urllib.parse

def extract_domain_from_url(url_str):
    if not url_str or not isinstance(url_str, str):
        return None
    match = re.search(r'https?://([^\s"\'/<>#\$:]+)', url_str)
    if match:
        raw_dom = match.group(1).split(":")[0]
        clean_dom = re.sub(r'^(www|api|v\d*|m\d*|cj|vip)\.', '', raw_dom)
        if clean_dom and "github" not in clean_dom and "jsdelivr" not in clean_dom and not clean_dom.replace('.', '').isdigit():
            return clean_dom
    return None

def export_all_router_rules(work_dir, sites, deep_cdn_domains):
    print("  [策略导出器] 正在从 api, ext, jar 提取域名并生成 AdGuard / PassWall / Clash 规则...", flush=True)
    domains_direct = set(deep_cdn_domains)
    domains_proxy = set()

    PROXY_KEYWORDS = ["(墙)", "墙外", "代理", "翻墙", "科学", "科学上网"]

    for s in sites:
        name = str(s.get("name", ""))
        key = str(s.get("key", ""))
        is_proxy_site = any(kw in name or kw in key for kw in PROXY_KEYWORDS)

        # 提取 api, ext, jar 中的域名
        extracted_urls = []
        for prop in ["api", "ext", "jar"]:
            val = s.get(prop)
            if isinstance(val, str):
                extracted_urls.append(val)
            elif isinstance(val, dict):
                extracted_urls.extend([str(v) for v in val.values() if isinstance(v, str)])

        for u_str in extracted_urls:
            dom = extract_domain_from_url(u_str)
            if dom:
                if is_proxy_site or "github" in dom or "jsdelivr" in dom:
                    domains_proxy.add(dom)
                else:
                    domains_direct.add(dom)

    sorted_direct = sorted(list(domains_direct))
    sorted_proxy = sorted(list(domains_proxy))

    # 1. 导出 PassWall / SmartDNS 直连列表
    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源、网页播放页与三层 M3U8/TS 播放 CDN 国内直连域名列表\n")
        for d in sorted_direct: f.write(f"{d}\n")

    # 2. 导出 Clash 直连规则集
    with open(os.path.join(work_dir, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源、网页播放页与三层 M3U8/TS 播放 CDN Clash 直连规则集\npayload:\n")
        for d in sorted_direct: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    # 3. 导出 OpenWrt AdGuard Home 国内直连放行规则集 (@@||domain^)
    with open(os.path.join(work_dir, "adguard_direct.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home TVBox 视频源与播放 CDN 国内直连放行白名单规则\n")
        for d in sorted_direct: f.write(f"@@||{d}^\n")

    # 4. 导出 PassWall 代理列表
    with open(os.path.join(work_dir, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源强制代理域名列表\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    # 5. 导出 Clash 代理规则集
    with open(os.path.join(work_dir, "clash_rules_proxy.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 强制代理规则集\npayload:\n")
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    # 6. 导出 OpenWrt AdGuard Home 代理放行规则集 (@@||domain^)
    with open(os.path.join(work_dir, "adguard_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("! OpenWrt AdGuard Home TVBox 视频源强制代理放行白名单规则\n")
        for d in sorted_proxy: f.write(f"@@||{d}^\n")

    print(f"  ├─ 成功导出 {len(sorted_direct)} 个直连域名 (含 AdGuard: adguard_direct.txt)")
    print(f"  └─ 成功导出 {len(sorted_proxy)} 个代理域名 (含 AdGuard: adguard_proxy.txt)")

if __name__ == "__main__":
    pass
