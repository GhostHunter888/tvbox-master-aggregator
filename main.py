#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox 主任务入口管道 (Pipeline Orchestrator)
=============================================================================
按顺序串联 5 个独立的单职责 Python 任务脚本：
  01. scripts/merge_sources.py                 : 资源抓取与合并
  02. scripts/analyze_potential_duplicates.py   : 潜在重复资源日志分析
  03. scripts/resolve_deep_cdn.py               : 多层级 Stage 5 物理播放域名探测
  04. scripts/extract_image_domains.py          : 动态海报图片 CDN 域名扒取
  05. scripts/export_router_rules.py            : 路由器与 AdGuard 放行规则导出
=============================================================================
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

from scripts import merge_sources as step1
from scripts import analyze_potential_duplicates as step2
from scripts import resolve_deep_cdn as step3
from scripts import extract_image_domains as step4
from scripts import export_router_rules as step5

def main():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] ===== 开始 TVBox 模块化管道全量更新 =====")

    # 1. 运行独立任务一：合并资源
    sites = step1.merge_sources()

    # 2. 运行独立任务二：日志分析潜在重复
    work_dir = os.path.dirname(os.path.abspath(__file__))
    step2.analyze_potential_duplicates(work_dir, sites)

    # 3. 运行独立任务三：多层级深解析播放域名
    grouped_cdn_domains = step3.resolve_deep_media_domains(sites, max_sites=len(sites))

    # 4. 运行独立任务四：动态海报图片 CDN 扒取
    dynamic_image_domains = step4.extract_all_poster_image_domains(sites, max_sites=len(sites))

    # 5. 运行独立任务五：策略导出 (AdGuard / PassWall / Clash)
    step5.export_all_router_rules(work_dir, sites, grouped_cdn_domains, dynamic_image_domains)

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] ===== TVBox 模块化管道更新全部成功完成! =====")

if __name__ == "__main__":
    main()
