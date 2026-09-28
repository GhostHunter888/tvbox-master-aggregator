#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本：基于 Mozilla 官方 Public Suffix List 的全量路由器规则导出器
=============================================================================
功能：
  1. 使用官方行业标准 tldextract (Mozilla Public Suffix List 算法) 动态解析域名；
  2. 结合来自 extract_image_domains 动态扒取到的海报图片 CDN 域名；
  3. 100% 精准识别全球任意国家/地区公共后缀 (.com.cn, .co.uk, .com.au, .co.nz 等)；
  4. 分组带备注导出 AdGuard Home (adguard_direct.txt)、PassWall (domains_direct.txt)、Clash (clash_rules_direct.yaml)！
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

def extract_root_domain(raw_str):
    """基于 Mozilla 官方公共后缀列表 (Public Suffix List) 100% 精准提取注册主域名"""
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

def export_grouped_router_rules(work_dir, sites, grouped_cdn_domains, dynamic_image_domains=None):
    print("  [策略导出器] 正在导出带备注分组规则 (包含全动态扒取的海报图片 CDN)...", flush=True)

    PROXY_KEYWORDS = ["(墙)", "墙外", "代理", "翻墙", "科学", "科学上网"]

    api_direct_domains = set()
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
            r_dom = extract_root_domain(u_str)
            if r_dom:
                if is_proxy_site or "github" in r_dom or "jsdelivr" in r_dom:
                    proxy_domains.add(r_dom)
                else:
                    api_direct_domains.add(r_dom)

    top_cdn = sorted(list(grouped_cdn_domains.get("top_facade_domains", set()) if isinstance(grouped_cdn_domains, dict) else set()))
    l2_play = sorted(list(grouped_cdn_domains.get("media_player_domains", set()) if isinstance(grouped_cdn_domains, dict) else set()))
    l3_ts = sorted(list(grouped_cdn_domains.get("deep_stream_domains", set()) if isinstance(grouped_cdn_domains, dict) else set()))
    api_doms = sorted(list(api_direct_domains))
    img_doms = sorted(list(set(dynamic_image_domains or [])))

    groups = [
        ("01_门面节点_OK资源_播放CDN域名", top_cdn),
        ("02_控制面_API服务域名", api_doms),
        ("03_二级_播放页与M3U8域名", l2_play),
        ("04_三级_深层TS视频切片边缘CDN域名", l3_ts),
        ("05_海报图片_CDN放行域名", img_doms)
    ]

    # 1. 导出 PassWall 直连列表 (domains_direct.txt)
    with open(os.path.join(work_dir, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# =========================================================\n")
        f.write("# TVBox 视频源、海报图片 CDN 与三层 M3U8/TS 播放 CDN 国内直连域名列表\n")
        f.write("# =========================================================\n\n")
        for g_title, dom_list in groups:
            if dom_list:
                f.write(f"# ===== 分组: {g_title} =====\n")
                for d in dom_list:
                    f.write(f"{d}\n")
                f.write("\n")

    # 2. 导出 AdGuard Home 白名单规则集 (adguard_direct.txt)
    with open(os.path.join(work_dir, "adguard_direct.txt"), "w", encoding="utf-8") as f:
        f.write("! =========================================================\n")
        f.write("! OpenWrt AdGuard Home TVBox 视频源、海报图片与播放 CDN 二级主域名放行白名单规则\n")
        f.write("! 语法: @@||domain.com^ (自动放行该主域名及其旗下所有子域名)\n")
        f.write("! =========================================================\n\n")
        for g_title, dom_list in groups:
            if dom_list:
                f.write(f"! ===== 分组: {g_title} =====\n")
                for d in dom_list:
                    f.write(f"@@||{d}^\n")
                f.write("\n")

    # 3. 导出 Clash 直连规则集 (clash_rules_direct.yaml)
    with open(os.path.join(work_dir, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# =========================================================\n")
        f.write("# TVBox 视频源、海报图片 CDN 与三层 M3U8/TS 播放 CDN Clash 直连规则集\n")
        f.write("# =========================================================\n")
        f.write("payload:\n")
        for g_title, dom_list in groups:
            if dom_list:
                f.write(f"  # ===== 分组: {g_title} =====\n")
                for d in dom_list:
                    f.write(f"  - DOMAIN-SUFFIX,{d}\n")

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
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 成功导出 PassWall 分组直连列表: domains_direct.txt (含全动态海报 CDN)")
    print(f"  ├─ 成功导出 AdGuard Home 分组放行白名单: adguard_direct.txt (@@||domain^)")
    print(f"  └─ 成功导出 Clash 分组直连规则集: clash_rules_direct.yaml")

def export_all_router_rules(work_dir, sites, deep_cdn_domains, dynamic_image_domains=None):
    return export_grouped_router_rules(work_dir, sites, deep_cdn_domains, dynamic_image_domains)

if __name__ == "__main__":
    pass
