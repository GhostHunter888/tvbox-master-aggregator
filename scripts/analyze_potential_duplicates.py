#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立分析脚本：潜在重复/高相似度站点日志分析器 (仅记录日志，绝不改变合并规则)
=============================================================================
功能：
  1. 计算全网合并站点之间的名称相似度与 API 域名相似度；
  2. 挖掘出 API 地址不同但极为相似的潜在重复资源站点；
  3. 将分析结果详细输出至 potential_duplicates.log，供后续审阅分析；
  4. 遵照用户指令：本脚本纯粹用于记录日志，绝不对节点进行任何强制合并。
=============================================================================
"""

import os
import re
import json
import difflib

def analyze_potential_duplicates(work_dir, sites):
    print("  [重复日志分析器] 正在分析全网合并站点中的潜在高相似度节点...", flush=True)
    log_path = os.path.join(work_dir, "potential_duplicates.log")

    similar_pairs = []

    # 提取所有清洗后的标准名字与 API
    clean_site_data = []
    for s in sites:
        raw_name = str(s.get("name", ""))
        clean_name = re.sub(r'^\[.*?\]\s*', '', raw_name).strip()
        api = str(s.get("api", ""))
        clean_site_data.append({
            "key": s.get("key"),
            "raw_name": raw_name,
            "clean_name": clean_name,
            "api": api
        })

    # 两两比对文本相似度
    n = len(clean_site_data)
    for i in range(n):
        for j in range(i + 1, n):
            s1 = clean_site_data[i]
            s2 = clean_site_data[j]

            # 排除完全相同的 API (已在主逻辑中去重)
            if s1["api"] == s2["api"]:
                continue

            # 计算名字相似度
            ratio = difflib.SequenceMatcher(None, s1["clean_name"], s2["clean_name"]).ratio()
            if ratio >= 0.75:
                similar_pairs.append({
                    "similarity": round(ratio * 100, 1),
                    "site_1": f"{s1['raw_name']} ({s1['api']})",
                    "site_2": f"{s2['raw_name']} ({s2['api']})"
                })

    # 按相似度从高到低排序
    similar_pairs.sort(key=lambda x: x["similarity"], reverse=True)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# TVBox 潜在高相似度节点分析日志 (共发现 {len(similar_pairs)} 组高相似潜在重复源)\n")
        f.write("# 本日志仅用于审查分析，未对实际节点进行任何强制合并改动。\n\n")
        for idx, pair in enumerate(similar_pairs, 1):
            f.write(f"【相似度 {pair['similarity']}%】序号 {idx}\n")
            f.write(f"  源 A: {pair['site_1']}\n")
            f.write(f"  源 B: {pair['site_2']}\n\n")

    print(f"  └─ 分析完成！共挖掘出 {len(similar_pairs)} 组潜在高相似节点，已详细写入 {log_path}", flush=True)

if __name__ == "__main__":
    pass
