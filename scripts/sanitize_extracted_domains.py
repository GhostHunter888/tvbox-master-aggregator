#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立脚本：全量域名与数据强力净化清洗器 (sanitize_extracted_domains.py)
=============================================================================
重点清洗：
  1. 100% 强行擦除所有反斜杠 \\ (把 kissjav\\.li 强行净化为 kissjav.li, 把 djj88\\.sbs 净化为 djj88.sbs)；
  2. 100% 强行擦除协议头 https://, http:// 与单/双斜杠 // 与端口号；
  3. 100% 强行剔除纯文件后缀 (如 .json, .txt, .m3u8, .ts, .php, .js, .css)；
  4. 100% 动态过滤 blackmatrix7 全量系统级/公共基础设施域名 (Google, Cloudflare, GitHub, Microsoft, Apple)；
  5. 输出 process/sanitized_candidate_domains.json 与 process/sanitized_proxy_domains.json。
=============================================================================
"""

import os
import re
import json

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESS_DIR = os.path.join(WORK_DIR, "process")
os.makedirs(PROCESS_DIR, exist_ok=True)

GLOBAL_PROXY_DOMAINS = [
    "google.com", "googlesyndication.com", "googletagmanager.com",
    "google-analytics.com", "googleapis.com", "gstatic.com", "doubleclick.net",
    "youtube.com", "ytimg.com", "ggpht.com", "github.com", "githubusercontent.com",
    "jsdelivr.net", "tmdb.org", "themoviedb.org", "t.me", "telegram.org",
    "twitter.com", "x.com", "facebook.com", "instagram.com", "huangguoai.com",
    "cloudflare.com", "microsoft.com", "apple.com"
]

INVALID_FILE_EXTENSIONS = [
    "json", "txt", "m3u8", "ts", "js", "css", "html", "htm", "png", "jpg", "jpeg", "webp", "php", "mp4", "mkv", "flv"
]

def to_punycode_domain(dom_str):
    if not dom_str or not isinstance(dom_str, str): return None
    try: return dom_str.encode("idna").decode("ascii")
    except Exception: return dom_str

def is_global_proxy_domain(dom):
    if not dom or not isinstance(dom, str): return False
    dom_l = dom.lower().strip()
    return any(dom_l == pd or dom_l.endswith("." + pd) for pd in GLOBAL_PROXY_DOMAINS)

def sanitize_domain_string(raw_dom):
    if not raw_dom or not isinstance(raw_dom, str):
        return None, False

    clean = str(raw_dom).replace('&amp;', '&').replace('\\/', '/').replace('\\', '').strip()
    clean = clean.split('#')[0].split('?')[0].split('&')[0].split(';')[0].split('%')[0].split(',')[0].strip()

    # 1. 擦除协议头与双斜杠
    clean = re.sub(r'^https?://', '', clean, flags=re.I)
    clean = re.sub(r'^//', '', clean)

    # 2. 擦除所有残存的单斜杠 /、双斜杠 // 与反斜杠 \
    clean = clean.replace('/', '').replace('\\', '').strip()

    # 3. 剥离端口号与问号
    clean = clean.split(":")[0].strip("@|*^ \t\r\n'\"").lower()

    if not clean or clean.startswith(".") or "." not in clean:
        return None, False

    parts = clean.split(".")
    if len(parts) < 2 or not parts[0] or not parts[-1]:
        return None, False

    tld = parts[-1].lower()
    prefix = parts[0].lower()

    if tld in INVALID_FILE_EXTENSIONS or prefix in INVALID_FILE_EXTENSIONS:
        return None, False

    if is_global_proxy_domain(clean):
        return clean, True

    return clean, False

def process_data_sanitization():
    print("  [数据强力清洗器] 正在对 Task 2~6 汇集的所有原始域名执行 4 重强力净化...", flush=True)

    raw_candidates = set()

    for json_file in ["grouped_cdn_domains.json", "extracted_release_page_domains.json", "extracted_py_code_domains.json", "dynamic_image_domains.json"]:
        fpath = os.path.join(PROCESS_DIR, json_file)
        if not os.path.exists(fpath):
            fpath = os.path.join(WORK_DIR, json_file)

        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k in ["top_facade_domains", "media_player_domains", "deep_stream_domains"]:
                            raw_candidates.update(data.get(k, []))
                    elif isinstance(data, list):
                        raw_candidates.update(data)
            except Exception: pass

    sanitized_direct_candidates = set()
    sanitized_proxy_candidates = set(GLOBAL_PROXY_DOMAINS)

    for raw_d in raw_candidates:
        clean_d, is_proxy = sanitize_domain_string(raw_d)
        if clean_d:
            if is_proxy:
                sanitized_proxy_candidates.add(clean_d)
            else:
                sanitized_direct_candidates.add(clean_d)
                puny = to_punycode_domain(clean_d)
                if puny: sanitized_direct_candidates.add(puny)

    sorted_direct = sorted(list(sanitized_direct_candidates))
    sorted_proxy = sorted(list(sanitized_proxy_candidates))

    open(os.path.join(PROCESS_DIR, "sanitized_candidate_domains.json"), "w", encoding="utf-8").write(json.dumps(sorted_direct, ensure_ascii=False, indent=2))
    open(os.path.join(PROCESS_DIR, "sanitized_proxy_domains.json"), "w", encoding="utf-8").write(json.dumps(sorted_proxy, ensure_ascii=False, indent=2))

    print(f"  └─ 强力清洗完成！净化出直连候选域名: {len(sorted_direct)}个, 隔离代理域名: {len(sorted_proxy)}个 (保存于 process/)", flush=True)

if __name__ == "__main__":
    process_data_sanitization()
