#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本四：路由器 PassWall / Clash 直连与代理策略导出器
=============================================================================
"""

import os
import re
import urllib.parse

def export_all_router_rules(work_dir, sites, deep_cdn_domains):
    print("  [策略导出器] 正在导出 PassWall 与 Clash 规则策略...", flush=True)
    domains_direct = set(deep_cdn_domains)
    domains_proxy = set()

    for s in sites:
        api = s.get("api", "")
        name = s.get("name", "")
        if api and isinstance(api, str) and api.startswith("http"):
            try:
                domain = urllib.parse.urlparse(str(api)).netloc.split(":")[0]
                domain = re.sub(r'^(www|api|cj|vip|v|jx|m|wap|app)\.', '', domain)
                if domain:
                    if "代理" in name or "翻墙" in name or "科学" in name or "github" in domain or "jsdelivr" in domain:
                        domains_proxy.add(domain)
                    else:
                        domains_direct.add(domain)
            except Exception: pass

    sorted_direct = sorted(list(domains_direct))
    sorted_proxy = sorted(list(domains_proxy))

    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源、网页播放页与三层 M3U8/TS 播放 CDN 国内直连域名列表\n")
        for d in sorted_direct: f.write(f"{d}\n")

    with open(os.path.join(work_dir, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源、网页播放页与三层 M3U8/TS 播放 CDN Clash 直连规则集\npayload:\n")
        for d in sorted_direct: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    with open(os.path.join(work_dir, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源强制代理域名列表\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    with open(os.path.join(work_dir, "clash_rules_proxy.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 强制代理规则集\npayload:\n")
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 成功导出 {len(sorted_direct)} 个国内直连域名 (含三层深解析 CDN)")
    print(f"  └─ 成功导出 {len(sorted_proxy)} 个强制代理域名")

if __name__ == "__main__":
    pass
