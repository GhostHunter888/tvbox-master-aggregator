#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

WORK_DIR = os.path.dirname(os.path.abspath(__file__))

SEX_KEYWORDS = [
    "x站", "18+", "色情", "伦理", "成人", "福利", "三级", "激情", "av",
    "杏吧", "极品x", "免费x", "嘿嘿", "火速", "红楼", "优优", "天美",
    "香蕉", "番茄", "黑料", "黄色仓库", "小鸡", "细胞", "大地", "奶香香",
    "桃花", "ck伦理", "大奶子", "搜av", "奥斯卡", "jkun", "滴滴", "豆豆",
    "精品x", "鲨鱼", "辣椒", "森林", "155", "色猫", "乐播", "玉兔",
    "老色p", "老色批", "番号", "sex", "adult", "porn", "91", "黄",
    "久草", "大x子", "老色x", "写真"
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_text(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def parse_json_safely(content):
    if not content: return None
    content_clean = content.lstrip('\ufeff')
    content_clean = re.sub(r',(\s*[}\]])', r'\1', content_clean)
    try: return json.loads(content_clean, strict=False)
    except Exception:
        for wrap in [('{','}'), ('[',']')]:
            s, e = content_clean.find(wrap[0]), content_clean.rfind(wrap[1])
            if s >= 0 and e > s:
                try: return json.loads(content_clean[s:e+1], strict=False)
                except: pass
    return None

UPSTREAM_REPO_ENDPOINTS = [
    "https://raw.githubusercontent.com/youhunwl/TVAPP/main/index.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/wangerxiao.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/ouge.json",
    "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json",
    "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json",
    "https://raw.githubusercontent.com/Yoursmile7/TVBox/main/XC.json",
    "https://raw.githubusercontent.com/liu673cn/box/main/m.json",
    "https://raw.githubusercontent.com/xiaolong69/tv/main/1.json",
    "https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json",
    "https://raw.githubusercontent.com/guot55/YGBH/main/vip2.json",
    "https://dxawi.github.io/0/0.json",
    "https://raw.githubusercontent.com/mymine/CatVodSpider/main/json/config.json",
    "https://raw.githubusercontent.com/cluntop/tvbox/main/tvbox.json",
    "https://raw.githubusercontent.com/cluntop/tvbox/main/json/config.json"
]

def sync_upstream_generated_data():
    print("[1/4] 动态拉取开源数据源...", flush=True)
    raw_sites, raw_lives, raw_parses, spider_jars = [], [], [], []
    for url in UPSTREAM_REPO_ENDPOINTS:
        content = fetch_text(url)
        data = parse_json_safely(content)
        if not data: continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    api = item.get("api") or item.get("url")
                    name = item.get("name", "")
                    if api and not is_blacklisted(name) and not is_blacklisted(str(api)):
                        raw_sites.append({"name": name, "api": str(api), "type": item.get("type", 1)})
        elif isinstance(data, dict):
            spider = data.get("spider", "")
            if spider and ("github" in spider.lower() or "jsdelivr" in spider.lower()):
                spider_jars.append(spider)
            for s in (data.get("sites") or []):
                if s.get("api") and not is_blacklisted(s.get("name")) and not is_blacklisted(str(s.get("api"))):
                    raw_sites.append(s)
            raw_lives.extend(data.get("lives") or [])
            raw_parses.extend(data.get("parses") or [])
    print(f"  └─ 实时获取到 {len(raw_sites)} 个基础站点接口", flush=True)
    return raw_sites, raw_lives, raw_parses, spider_jars

def sync_web_sources():
    print("[2/4] 动态解析网页资源 (zzzypro.com & clbug.com)...", flush=True)
    web_sites = []
    html = fetch_text("https://www.zzzypro.com/")
    if html:
        part = html.split("❶影视资源")[1] if "❶影视资源" in html else html
        if "❷X站资源" in part: part = part.split("❷X站资源")[0]
        for raw_url, name in re.findall(r'<a[^>]+data-url=["\']([^"\']+)["\'][^>]*>.*?<strong>([^<]+)</strong>', part, re.I):
            name, raw_url = name.strip(), raw_url.strip().rstrip("/")
            if not is_blacklisted(name) and not is_blacklisted(raw_url):
                api_url = f"{'https://' if not raw_url.startswith('http') else ''}{raw_url}/api.php/provide/vod/"
                web_sites.append({"name": name, "api": api_url, "type": 1})

    clbug_html = fetch_text("https://tvbox.clbug.com/user.php")
    if clbug_html:
        c_part = clbug_html.split("X站")[0] if "X站" in clbug_html else clbug_html
        for name, url in zip(re.findall(r'<td class="td-name">([^<]+)</td>', c_part), re.findall(r'data-url="([^"]+)"', c_part)):
            name, url = name.strip(), url.strip().replace("&amp;", "&")
            if url and not url.startswith("#") and not is_blacklisted(name) and not is_blacklisted(url):
                if url.endswith(".json") or "json" in url:
                    sub_data = parse_json_safely(fetch_text(url))
                    if isinstance(sub_data, dict):
                        for s in (sub_data.get("sites") or []):
                            if s.get("api") and not is_blacklisted(s.get("name")) and not is_blacklisted(s.get("api")):
                                web_sites.append(s)
    print(f"  └─ 网页动态提取获取到 {len(web_sites)} 个新站源", flush=True)
    return web_sites

def check_api_alive(site):
    api = site.get("api", "")
    test_url = str(api).rstrip("/") + ("&ac=list" if "?" in str(api) else "?ac=list")
    try:
        req = urllib.request.Request(test_url, headers=HEADERS)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:
            if resp.status == 200:
                site["_cost"] = int((time.time() - t0) * 1000)
                return site
    except: pass
    return None

def apply_master_cleaning(all_sites):
    print("[3/4] 执行数据清洗与深度物理去重 (接口联通性与名称合并)...", flush=True)
    unique_sites = {}
    unique_names = set()

    for s in all_sites:
        api = s.get("api", "")
        raw_name = s.get("name", "")
        if not api or is_blacklisted(raw_name) or is_blacklisted(str(api)):
            continue

        # 深度清洗名称：去除品牌和垃圾后缀，实现真正的合并去重
        clean_name = re.sub(r'^\[.*?\]\s*', '', raw_name)
        clean_name = re.sub(r'(资源|采集|闪电|影视|网|站|线路|接口|专线|秒播|蓝光|高清|专区|官方|备用|\d+|-|!|！)+$', '', clean_name).strip()
        clean_name = re.sub(r'^(新|大)', '', clean_name).strip()
        if not clean_name:
            continue

        try:
            domain = urllib.parse.urlparse(str(api)).netloc
            domain = re.sub(r'^(www|api|cj|vip|v|jx)\.', '', domain)
        except:
            domain = str(api)

        # 通过主域名 AND 净化后的名称进行严格去重，确保没有重复的"豆瓣"等
        if domain not in unique_sites and clean_name not in unique_names:
            s["_clean_name"] = clean_name
            unique_sites[domain] = s
            unique_names.add(clean_name)

    candidates = list(unique_sites.values())
    print(f"  ├─ 归一去重后待测站点总数: {len(candidates)} 个", flush=True)

    alive_sites = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for res in as_completed([executor.submit(check_api_alive, site) for site in candidates]):
            if res.result(): alive_sites.append(res.result())

    # 完全按测速排序 (延迟 ms 从小到大)，移除硬编码的 top_pinned
    alive_sites.sort(key=lambda x: x.get("_cost", 9999))
    print(f"  └─ 联通测试存活可用站点: {len(alive_sites)} 个", flush=True)
    return alive_sites

def export_router_rules(sites):
    print("[4/4] 导出 PassWall / Clash 国内直连域名规则策略...", flush=True)
    domains = set(["raw.githubusercontent.com", "cdn.jsdelivr.net", "fastly.jsdelivr.net"])
    for s in sites:
        if s.get("api"):
            try: domains.add(urllib.parse.urlparse(str(s["api"])).netloc.split(":")[0])
            except: pass
    sorted_domains = sorted(list(domains))

    with open(os.path.join(WORK_DIR, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源国内直连域名列表 (PassWall / SmartDNS 专用)\n")
        for d in sorted_domains: f.write(f"{d}\n")

    with open(os.path.join(WORK_DIR, "clash_rules.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 直连规则集 (DOMAIN-SUFFIX 格式)\npayload:\n")
        for d in sorted_domains: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

def main():
    print("==================================================", flush=True)
    print(f" TVBox 资源全量整合与自动化清洗引擎启动 ({time.strftime('%Y-%m-%d %H:%M:%S')})", flush=True)
    print("==================================================", flush=True)

    upstream_sites, upstream_lives, upstream_parses, spider_jars = sync_upstream_generated_data()
    web_sites = sync_web_sources()

    all_raw_sites = upstream_sites + web_sites
    cleaned_alive_sites = apply_master_cleaning(all_raw_sites)

    # 科学的分类排序：将电影、电视剧、综艺等核心前置，纪录片、体育、戏曲等后置
    COMPREHENSIVE_CATEGORIES = [
        "电影", "电视剧", "国产剧", "综艺", "动漫", "韩剧", "美剧", "日剧", "港剧", "台剧", "泰剧", "海外剧",
        "短剧", "纪录片", "体育", "音乐", "解说", "游戏", "戏曲", "少儿"
    ]

    clean_sites = []
    for s in cleaned_alive_sites:
        cost = s.pop("_cost", 0)
        clean_name = s.pop("_clean_name", s.get("name", ""))

        # 提取原厂分类，若无则补充完整的分类
        assigned_cats = s.get("categories", [])
        if not isinstance(assigned_cats, list) or len(assigned_cats) == 0:
            assigned_cats = COMPREHENSIVE_CATEGORIES

        clean_sites.append({
            "key": s.get("key", clean_name),
            "name": f"[{cost}ms] {clean_name}",
            "type": s.get("type", 1),
            "api": s.get("api", ""),
            "searchable": s.get("searchable", 1),
            "quickSearch": s.get("quickSearch", 1),
            "filterable": s.get("filterable", 1),
            "categories": assigned_cats
        })

    DEFAULT_SPIDER = "https://cdn.jsdelivr.net/gh/CatVod/CatVodSpider@main/jar/custom_spider.jar"

    # 直播与解析去重合并
    seen_lives, unique_lives = set(), []
    for l in [{"name": "IPTV国内直连", "type": 0, "url": "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"}] + upstream_lives:
        url = l.get("url")
        if url and url not in seen_lives:
            seen_lives.add(url)
            unique_lives.append(l)

    seen_parses, unique_parses = set(), []
    for p in [{"name": "并发VIP解析", "type": 1, "url": "https://api.json.pro/api/?url="}] + upstream_parses:
        url = p.get("url")
        if url and url not in seen_parses:
            seen_parses.add(url)
            unique_parses.append(p)

    master_config = {
        "spider": DEFAULT_SPIDER,
        "sites": clean_sites,
        "lives": unique_lives,
        "parses": unique_parses,
        "rules": [
            {"name": "lz", "hosts": ["lz"], "regex": ["#EXT-X-DISCONTINUITY"]},
            {"name": "ff", "hosts": ["ff"], "regex": ["#EXT-X-DISCONTINUITY"]}
        ],
        "note": "本配置由 TVBox 资源全量整合引擎自动生成。"
    }

    with open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 生成整合主配置文件: tvbox.json ({len(clean_sites)} 个纯净站点)", flush=True)

    export_router_rules(clean_sites)
    print("\n[4/4] 完成！", flush=True)

if __name__ == "__main__":
    main()
