#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import re
from lxml import etree

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
os.makedirs(PROCESS_DIR, exist_ok=True)

cat_py_dir = os.path.join(WORK_DIR, "repos", "cat", "TVBOX", "PY")
if os.path.exists(cat_py_dir):
    sys.path.insert(0, cat_py_dir)

sys.path.insert(0, os.path.join(WORK_DIR, "scripts"))

from kkys_master import Spider

def parse_list_with_lxml(html):
    if not html: return []
    tree = etree.HTML(html.encode('utf-8'))
    if tree is None: return []
    out, seen = [], set()
    for a in tree.xpath('//div[contains(@class,"module-item")]//a[contains(@class,"v-item")]'):
        href = a.get("href", "")
        m = re.search(r'/detail/(\d+)\.html', href)
        if not m or m.group(1) in seen: continue
        seen.add(m.group(1))
        name = "".join(a.xpath('.//div[contains(@class,"v-item-title")][not(@style)]//text()')).strip()
        if not name:
            name = "".join(a.xpath('.//div[contains(@class,"v-item-title")]//text()')).strip()
        if not name: continue
        pic = (a.xpath('.//img[not(contains(@data-original,"logo_placeholder"))]/@data-original') or [""])[0]
        if not pic:
            pic = (a.xpath('.//img[not(contains(@src,"logo_placeholder"))]/@src') or [""])[0]
        rem = "".join(a.xpath('.//div[contains(@class,"v-item-bottom")]//text()')).strip()
        out.append({"vod_id": m.group(1), "vod_name": name, "vod_pic": pic, "vod_remarks": rem})
    return out

def debug_kkys():
    print("开始对可可影视 (kkys_master.py 与 lxml 方案) 在 GitHub Actions 云端进行双向对比测试...", flush=True)
    spider = Spider()
    spider.init()

    # 抓取可可影视首页原始 HTML
    raw_html = spider._get("https://www.kkys20.com/")

    # 1. 之前 master 版本的 regex 解析结果
    master_parsed = spider._parse_list(raw_html)

    # 2. 使用 lxml/XPath 方案的解析结果
    lxml_parsed = parse_list_with_lxml(raw_html)

    output = {
        "master_regex_output_sample": master_parsed[:10],
        "lxml_xpath_output_sample": lxml_parsed[:10]
    }

    out_path = os.path.join(PROCESS_DIR, "kkys_debug_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"云端双向对比调试完成！对比日志已保存至: {out_path}", flush=True)

if __name__ == "__main__":
    debug_kkys()
