#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox 资源全量整合与自动化清洗引擎 (多源采集与规则导出)
=============================================================================
系统架构与工作流程：
  1. 动态与上游开源数据源保持同步采集与数据拉取；
  2. 实时解析并归一化原始资源池；
  3. 自动化数据清洗与加工控制：
     - 识别并剔除不合规及低俗内容源；
     - 消除品牌渠道前缀，实现接口资源的归一化去重；
     - 依赖资源（如 Spider 模块）统一映射至 GitHub 官方 Raw 与 CDN 镜像服务；
     - 自动提取站点主域名，生成适配 PassWall 与 Clash 的策略规则文件；
     - 输出标准化主配置文件 (`tvbox.json`) 与兼容配置 (`tvbox_multi.json`)。
=============================================================================
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# 强制开启 Python 实时无缓冲日志输出 (确保 GitHub Actions 控制台实时显示日志)
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

WORK_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 1. 黑名单与色情/18+ 过滤词库
# ---------------------------------------------------------------------------
SEX_KEYWORDS = [
    "x站", "18+", "色情", "伦理", "成人", "福利", "三级", "激情", "av",
    "杏吧", "极品x", "免费x", "嘿嘿", "火速", "红楼", "优优", "天美",
    "香蕉", "番茄", "黑料", "黄色仓库", "小鸡", "细胞", "大地", "奶香香",
    "桃花", "ck伦理", "大奶子", "搜av", "奥斯卡", "jkun", "滴滴", "豆豆",
    "精品x", "鲨鱼", "辣椒", "森林", "155", "色猫", "乐播", "玉兔",
    "老色p", "老色批", "番号", "sex", "adult", "porn", "91", "黄",
    "久草", "大x子", "老色x"
]

# ---------------------------------------------------------------------------
# 2. 网络请求与辅助函数
# ---------------------------------------------------------------------------
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_text(url, timeout=12):
    """安全拉取远程文本内容"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def is_blacklisted(text):
    """检测是否含有黑名单/18+词汇"""
    if not text:
        return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def parse_json_safely(content):
    """解析容错 JSON"""
    if not content:
        return None
    content_clean = content.lstrip('\ufeff')
    content_clean = re.sub(r',(\s*[}\]])', r'\1', content_clean)
    try:
        return json.loads(content_clean, strict=False)
    except Exception:
        s1, e1 = content_clean.find('{'), content_clean.rfind('}')
        if s1 >= 0 and e1 > s1:
            try:
                return json.loads(content_clean[s1:e1+1], strict=False)
            except Exception:
                pass
        s2, e2 = content_clean.find('['), content_clean.rfind(']')
        if s2 >= 0 and e2 > s2:
            try:
                return json.loads(content_clean[s2:e2+1], strict=False)
            except Exception:
                pass
    return None

# ---------------------------------------------------------------------------
# 3. 动态同步上游参考库与开源数据源
# ---------------------------------------------------------------------------
UPSTREAM_REPO_ENDPOINTS = [
    "https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_full.json",
    "https://raw.githubusercontent.com/25175/tvyuan/master/tvbox.json",
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/dc_full.json",
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/sources_pool.json",
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/sources.json",
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/latest.json",
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
]

def sync_upstream_generated_data():
    print("[1/5] 动态拉取上游参考库与数据源...", flush=True)
    raw_sites = []
    raw_lives = []
    raw_parses = []
    spider_jars = []

    for url in UPSTREAM_REPO_ENDPOINTS:
        content = fetch_text(url)
        if not content:
            continue
        data = parse_json_safely(content)
        if not data:
            continue

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
                s_name = s.get("name", "")
                s_api = s.get("api", "")
                if s_api and not is_blacklisted(s_name) and not is_blacklisted(str(s_api)):
                    raw_sites.append(s)
            for l in (data.get("lives") or []):
                raw_lives.append(l)
            for p in (data.get("parses") or []):
                raw_parses.append(p)

    print(f"  └─ 实时获取到 {len(raw_sites)} 个基础站点接口", flush=True)
    return raw_sites, raw_lives, raw_parses, spider_jars

# ---------------------------------------------------------------------------
# 4. 抓取 https://www.zzzypro.com/ 影视区 与 clbug
# ---------------------------------------------------------------------------
def sync_web_sources():
    print("[2/5] 动态解析网页资源 (zzzypro.com 影视区 & clbug.com)...", flush=True)
    web_sites = []

    html = fetch_text("https://www.zzzypro.com/")
    if html:
        part = html.split("❶影视资源")[1] if "❶影视资源" in html else html
        if "❷X站资源" in part:
            part = part.split("❷X站资源")[0]

        matches = re.findall(
            r'<a[^>]+data-url=["\']([^"\']+)["\'][^>]*>.*?<strong>([^<]+)</strong>',
            part,
            re.DOTALL | re.IGNORECASE
        )
        for raw_url, name in matches:
            name = name.strip()
            raw_url = raw_url.strip().rstrip("/")
            if is_blacklisted(name) or is_blacklisted(raw_url):
                continue
            if not raw_url.startswith("http"):
                raw_url = "https://" + raw_url
            api_url = f"{raw_url}/api.php/provide/vod/"
            web_sites.append({"name": name, "api": api_url, "type": 1})

    clbug_html = fetch_text("https://tvbox.clbug.com/user.php")
    if clbug_html:
        c_part = clbug_html.split("X站")[0] if "X站" in clbug_html else clbug_html
        src_urls = re.findall(r'data-url="([^"]+)"', c_part)
        src_names = re.findall(r'<td class="td-name">([^<]+)</td>', c_part)
        for name, url in zip(src_names, src_urls):
            name, url = name.strip(), url.strip().replace("&amp;", "&")
            if url and not url.startswith("#") and not is_blacklisted(name) and not is_blacklisted(url):
                if url.endswith(".json") or "json" in url:
                    sub_content = fetch_text(url)
                    sub_data = parse_json_safely(sub_content)
                    if isinstance(sub_data, dict):
                        for s in (sub_data.get("sites") or []):
                            if s.get("api") and not is_blacklisted(s.get("name")) and not is_blacklisted(s.get("api")):
                                web_sites.append(s)

    print(f"  └─ 网页动态提取获取到 {len(web_sites)} 个新站源", flush=True)
    return web_sites

# ---------------------------------------------------------------------------
# 5. 多线程并发连通性检测与去重
# ---------------------------------------------------------------------------
def check_api_alive(site):
    api = site.get("api", "")
    if not api or not str(api).startswith("http"):
        return None
    if is_blacklisted(site.get("name", "")) or is_blacklisted(api):
        return None

    test_url = str(api).rstrip("/") + ("&ac=list" if "?" in str(api) else "?ac=list")
    try:
        req = urllib.request.Request(test_url, headers=HEADERS)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as resp:
            if resp.status == 200:
                cost = int((time.time() - t0) * 1000)
                site["_cost"] = cost
                return site
    except Exception:
        pass
    return None

def apply_master_cleaning(all_sites):
    print("[3/5] 执行数据清洗与物理去重 (接口联通性与存活验证)...", flush=True)
    unique_sites = {}

    for s in all_sites:
        api = s.get("api", "")
        if not api:
            continue
        if is_blacklisted(s.get("name", "")) or is_blacklisted(str(api)):
            continue

        try:
            domain = urllib.parse.urlparse(str(api)).netloc
        except Exception:
            domain = str(api)

        if domain not in unique_sites:
            unique_sites[domain] = s

    candidates = list(unique_sites.values())
    print(f"  ├─ 归一去重后待测站点总数: {len(candidates)} 个", flush=True)

    alive_sites = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(check_api_alive, site) for site in candidates]
        for future in as_completed(futures):
            res = future.result()
            if res:
                alive_sites.append(res)

    alive_sites.sort(key=lambda x: x.get("_cost", 9999))
    print(f"  └─ 联通测试存活可用站点: {len(alive_sites)} 个", flush=True)
    return alive_sites

# ---------------------------------------------------------------------------
# 6. 导出 PassWall / Clash 规则
# ---------------------------------------------------------------------------
def export_router_rules(sites):
    print("[4/5] 导出 PassWall / Clash 国内直连域名规则策略...", flush=True)
    domains = set()

    for s in sites:
        api = s.get("api", "")
        if api:
            try:
                domain = urllib.parse.urlparse(str(api)).netloc.split(":")[0]
                if domain:
                    domains.add(domain)
            except Exception:
                pass

    domains.add("raw.githubusercontent.com")
    domains.add("cdn.jsdelivr.net")
    domains.add("fastly.jsdelivr.net")

    sorted_domains = sorted(list(domains))

    passwall_path = os.path.join(WORK_DIR, "domains_direct.txt")
    with open(passwall_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源国内直连域名列表 (PassWall / SmartDNS 专用)\n")
        for d in sorted_domains:
            f.write(f"{d}\n")

    clash_path = os.path.join(WORK_DIR, "clash_rules.yaml")
    with open(clash_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 直连规则集 (DOMAIN-SUFFIX 格式)\n")
        f.write("payload:\n")
        for d in sorted_domains:
            f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 导出 {len(sorted_domains)} 个直连域名到 domains_direct.txt", flush=True)
    print(f"  └─ 导出 Clash 规则集到 clash_rules.yaml", flush=True)

# ---------------------------------------------------------------------------
# 7. 主程序入口
# ---------------------------------------------------------------------------
def main():
    print(f"==================================================", flush=True)
    print(f" TVBox 资源全量整合与自动化清洗引擎启动 ({time.strftime('%Y-%m-%d %H:%M:%S')})", flush=True)
    print(f"==================================================", flush=True)

    upstream_sites, upstream_lives, upstream_parses, spider_jars = sync_upstream_generated_data()
    web_sites = sync_web_sources()

    all_raw_sites = []
    all_raw_sites.extend(upstream_sites)
    all_raw_sites.extend(web_sites)

    cleaned_alive_sites = apply_master_cleaning(all_raw_sites)

    STD_CATEGORIES = ["电影", "电视剧", "综艺", "动漫", "泰剧", "韩剧", "美剧", "日剧", "港剧"]

    TOP_PINNED_KEYWORDS = [
        "4k", "夸克", "阿里", "uc网盘", "豆瓣", "索尼", "360", "暴风",
        "非凡", "极速", "光速", "巨量", "天涯", "爱奇艺", "红牛", "无尽"
    ]

    def get_site_priority(site_name, site_api):
        name_lower = str(site_name).lower()
        api_lower = str(site_api).lower()
        for idx, kw in enumerate(TOP_PINNED_KEYWORDS):
            if kw in name_lower or kw in api_lower:
                return idx
        return 999

    clean_sites = []
    for s in cleaned_alive_sites:
        cost = s.pop("_cost", 0)
        raw_name = s.get("name", "")
        clean_name = re.sub(r'^\[.*?\]\s*', '', raw_name)
        priority = get_site_priority(clean_name, s.get("api", ""))

        c_site = {
            "key": s.get("key", clean_name),
            "name": f"[{cost}ms] {clean_name}",
            "type": s.get("type", 1),
            "api": s.get("api", ""),
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1,
            "categories": STD_CATEGORIES,
            "_priority": priority,
            "_cost": cost
        }
        if "ext" in s:
            c_site["ext"] = s["ext"]
        clean_sites.append(c_site)

    clean_sites.sort(key=lambda x: (x["_priority"], x["_cost"]))

    for s in clean_sites:
        s.pop("_priority", None)
        s.pop("_cost", None)

    DEFAULT_SPIDER = "https://cdn.jsdelivr.net/gh/CatVod/CatVodSpider@main/jar/custom_spider.jar"

    lives = [
        {
            "name": "IPTV国内直连直播",
            "type": 0,
            "url": "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"
        }
    ]
    if upstream_lives:
        lives.extend(upstream_lives)

    parses_list = [
        {"name": "聚合VIP解析1", "type": 3, "url": "Demo"},
        {"name": "并发VIP解析2", "type": 1, "url": "https://api.json.pro/api/?url="}
    ]
    if upstream_parses:
        parses_list.extend(upstream_parses)

    master_config = {
        "spider": DEFAULT_SPIDER,
        "sites": clean_sites,
        "lives": lives,
        "parses": parses_list,
        "rules": [
            {"name": "lz", "hosts": ["lz"], "regex": ["#EXT-X-DISCONTINUITY"]},
            {"name": "ff", "hosts": ["ff"], "regex": ["#EXT-X-DISCONTINUITY"]}
        ],
        "note": "本配置由 TVBox 资源整合引擎自动生成。致谢开源贡献者：FongMi、gaotianliuyun、Yoursmile7、liu673cn、Lightconer、zzzypro。"
    }

    tvbox_json_path = os.path.join(WORK_DIR, "tvbox.json")
    with open(tvbox_json_path, "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 生成主单仓配置文件: tvbox.json ({len(clean_sites)} 个纯净站点)", flush=True)

    multi_stores = []
    for s in clean_sites:
        multi_stores.append({
            "sourceName": s["name"],
            "sourceUrl": s["api"]
        })
    multi_config = {
        "storeHouse": multi_stores
    }
    multi_json_path = os.path.join(WORK_DIR, "tvbox_multi.json")
    with open(multi_json_path, "w", encoding="utf-8") as f:
        json.dump(multi_config, f, ensure_ascii=False, indent=2)
    print(f"[OK] 生成多仓配置文件: tvbox_multi.json ({len(multi_stores)} 个独立仓库)", flush=True)

    export_router_rules(clean_sites)

    sources_txt_path = os.path.join(WORK_DIR, "sources.txt")
    with open(sources_txt_path, "w", encoding="utf-8") as f:
        f.write(f"# TVBox 纯净全量资源汇总 ({time.strftime('%Y-%m-%d %H:%M:%S')})\n\n")
        for s in clean_sites:
            f.write(f"{s['name']}\n{s['api']}\n\n")

    print(f"\n[5/5] 完成！所有产物已同步写入仓库。", flush=True)

if __name__ == "__main__":
    main()
