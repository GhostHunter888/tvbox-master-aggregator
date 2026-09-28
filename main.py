#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox 主任务入口管道 (Pipeline Orchestrator)
=============================================================================
按顺序串联 5 个独立的单职责 Python 任务脚本：
  01. scripts/01_merge_sources.py              : 资源抓取与合并
  02. scripts/analyze_potential_duplicates.py   : 潜在重复资源日志分析
  03. scripts/resolve_deep_cdn.py               : 多层级物理播放域名探测
  04. scripts/export_router_rules.py            : 路由器与 AdGuard 放行规则导出
=============================================================================
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

from scripts import01_merge_sources as step1
from scripts import analyze_potential_duplicates as step2
from scripts import resolve_deep_cdn as step3
from scripts import export_router_rules as step4

def main():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] ===== 开始 TVBox 模块化管道全量更新 =====")

    # 1. 运行独立任务一：合并资源
    sites = step1.merge_sources()

    # 2. 运行独立任务二：日志分析潜在重复
    work_dir = os.path.dirname(os.path.abspath(__file__))
    step2.analyze_potential_duplicates(work_dir, sites)

    # 3. 运行独立任务三：多层级深解析播放域名 (带 3 天缓存)
    cache_file = os.path.join(work_dir, "grouped_cdn_domains.json")
    force_resolve = os.environ.get("FORCE_CDN_RESOLVE", "0") == "1"
    grouped_cdn_domains = None

    if not force_resolve and os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if (time.time() - mtime) < (3 * 86400):
            try:
                import json
                with open(cache_file, "r", encoding="utf-8") as f:
                    grouped_cdn_domains = json.load(f)
                print(f"  [深解析缓存] 找到 3 天内已生成的 CDN 域名缓存，直接复用！")
            except Exception: pass

    if not grouped_cdn_domains:
        grouped_cdn_domains = step3.resolve_deep_media_domains(sites, max_sites=len(sites))
        try:
            import json
            cache_data = {
                "top_facade_domains": list(grouped_cdn_domains.get("top_facade_domains", set())),
                "media_player_domains": list(grouped_cdn_domains.get("media_player_domains", set())),
                "deep_stream_domains": list(grouped_cdn_domains.get("deep_stream_domains", set()))
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception: pass

    # 4. 运行独立任务四：策略导出 (AdGuard / PassWall / Clash)
    step4.export_all_router_rules(work_dir, sites, grouped_cdn_domains)

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ===== TVBox 模块化管道更新全部成功完成! =====")

if __name__ == "__main__":
    main()
