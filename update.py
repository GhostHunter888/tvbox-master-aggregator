#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox Master 资源聚合与纯净清洗引擎 (基于权威参考库 1:1 规范构建)
=============================================================================
参考库标准规范说明：
  1. 1:1 遵循 FongMi, tvbox-dc, tvyuan, tvbox-source 等开源成熟库的代码逻辑与 JSON 协议；
  2. 单仓 (tvbox.json) 包含完整的 spider, wallpaper, sites, lives, parses, rules 节点；
  3. 多仓 (tvbox_multi.json) 兼容 sites (type:0), stores, urls 三重标准多仓映射协议；
  4. 路由器规则 (domains_direct.txt / clash_rules_direct.yaml) 精确剥离 API 主域名，排除 GitHub 依赖；
  5. 全过程实行双重 18+/低俗内容黑名单隔离，确保输出数据 100% 规范干净。
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

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

WORK_DIR = os.path.dirname(os.path.abspath(__file__))

# 黑名单词库：彻底过滤低俗/成人/18+ 内容
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_text(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            raw_data = resp.read()
            try:
                return raw_data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return raw_data.decode("gbk", errors="ignore")
                except:
                    return raw_data.decode("utf-8", errors="ignore")
    except Exception as e:
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
    "https://raw.githubusercontent.com/songlees355-wq/okay/main/tvbox.json"
]

def sync_upstream_generated_data():
    print("[1/4] 拉取开源参考库数据源...", flush=True)
    raw_sites, raw_lives, raw_parses, spider_jars = [], [], [], []
    for url in UPSTREAM_REPO_ENDPOINTS:
        content = fetch_text(url)
        data = parse_json_safely(content)
        if not data: continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    api = item.get("api") or item.get("url")
                    name = item.get("name", "未命名")
                    if api and not is_blacklisted(name) and not is_blacklisted(str(api)):
                        raw_sites.append(item)
        elif isinstance(data, dict):
            spider = data.get("spider", "")
            if spider and ("github" in spider.lower() or "jsdelivr" in spider.lower()):
                spider_jars.append(spider)
            for s in (data.get("sites") or []):
                if s.get("api") and not is_blacklisted(s.get("name")) and not is_blacklisted(str(s.get("api"))):
                    raw_sites.append(s)
            raw_lives.extend(data.get("lives") or [])
            raw_parses.extend(data.get("parses") or [])
    print(f"  └─ 提取到 {len(raw_sites)} 个基础站点接口", flush=True)
    return raw_sites, raw_lives, raw_parses, spider_jars

def sync_web_sources():
    print("[2/4] 解析网页导航源 (zzzypro.com & clbug.com)...", flush=True)
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
    print(f"  └─ 获取到 {len(web_sites)} 个新站源", flush=True)
    return web_sites

def check_api_alive(site):
    api = site.get("api", "")
    stype = site.get("type", 1)
    # 对于带有 ext、jar 或 type=3 的高级 JS 爬虫，免检直通
    if stype == 3 or "ext" in site or "jar" in site or "js" in str(site.get("name", "")).lower():
        site["_cost"] = 10
        return site

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
    print("[3/4] 执行去重与存活测速...", flush=True)
    unique_sites = {}
    unique_names = set()

    for s in all_sites:
        api = s.get("api", "")
        raw_name = s.get("name", "")
        if not api or is_blacklisted(raw_name) or is_blacklisted(str(api)):
            continue

        clean_name = re.sub(r'^\[.*?\]\s*', '', raw_name).strip()
        if not clean_name: continue

        api_key = str(api).lower().strip()
        if api_key not in unique_sites and clean_name not in unique_names:
            s["_clean_name"] = clean_name
            unique_sites[api_key] = s
            unique_names.add(clean_name)

    candidates = list(unique_sites.values())
    print(f"  ├─ 去重后待测站点总数: {len(candidates)} 个", flush=True)

    alive_sites = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for res in as_completed([executor.submit(check_api_alive, site) for site in candidates]):
            if res.result(): alive_sites.append(res.result())

    # 按测速从小到大排序
    alive_sites.sort(key=lambda x: x.get("_cost", 9999))
    print(f"  └─ 联通测试存活可用站点: {len(alive_sites)} 个\n", flush=True)
    return alive_sites

def export_router_rules(sites):
    print("[4/4] 导出 PassWall / Clash 规则策略...", flush=True)
    domains_direct = set()
    domains_proxy = set()

    for s in sites:
        api = s.get("api", "")
        name = s.get("name", "")
        if api:
            try:
                domain = urllib.parse.urlparse(str(api)).netloc.split(":")[0]
                domain = re.sub(r'^(www|api|cj|vip|v|jx|m|wap|app)\.', '', domain)
                if domain:
                    if "代理" in name or "翻墙" in name or "科学" in name or "github" in domain or "jsdelivr" in domain:
                        domains_proxy.add(domain)
                    else:
                        domains_direct.add(domain)
            except: pass

    sorted_direct = sorted(list(domains_direct))
    sorted_proxy = sorted(list(domains_proxy))

    with open(os.path.join(WORK_DIR, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源国内直连域名列表 (PassWall / SmartDNS 专用)\n")
        for d in sorted_direct: f.write(f"{d}\n")

    with open(os.path.join(WORK_DIR, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 直连规则集 (DOMAIN-SUFFIX 格式)\npayload:\n")
        for d in sorted_direct: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    with open(os.path.join(WORK_DIR, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源强制代理域名列表\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    with open(os.path.join(WORK_DIR, "clash_rules_proxy.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 强制代理规则集 (DOMAIN-SUFFIX 格式)\npayload:\n")
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 导出 {len(sorted_direct)} 个直连域名")
    print(f"  └─ 导出 {len(sorted_proxy)} 个代理域名")

def build_multi_store():
    """按参考库标准的多仓协议 (sites, stores, urls 三重兼容) 生成 tvbox_multi.json"""
    multi_sites = [
        {"name": "🚀 [主推] 全网纯净采集大一统", "url": "https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox.json", "type": 0},
        {"name": "💎 [旗舰] 饭太硬精选仓", "url": "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json", "type": 0},
        {"name": "💎 [旗舰] 肥猫精选仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json", "type": 0},
        {"name": "💎 [旗舰] 欧歌专仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/ouge.json", "type": 0},
        {"name": "🔥 [高阶] FongMi 官方仓", "url": "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json", "type": 0},
        {"name": "🔥 [聚合] 王二小专仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/wangerxiao.json", "type": 0},
        {"name": "🔥 [聚合] 高天流云配置", "url": "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json", "type": 0},
        {"name": "✨ [4K] 蓝光专线仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json", "type": 0}
    ]
    multi_config = {
        "spider": "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/jar/custom_spider.jar",
        "sites": multi_sites,
        "stores": [{"name": m["name"], "url": m["url"]} for m in multi_sites],
        "urls": [{"name": m["name"], "url": m["url"]} for m in multi_sites],
        "note": "本配置由 TVBox 资源整合引擎自动生成。"
    }
    with open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8") as f:
        json.dump(multi_config, f, ensure_ascii=False, indent=2)
    print(f"[OK] 生成多仓配置文件: tvbox_multi.json", flush=True)

def main():
    print("==================================================", flush=True)
    print(f" TVBox 资源全量整合与自动化清洗引擎启动 ({time.strftime('%Y-%m-%d %H:%M:%S')})", flush=True)
    print("==================================================\n", flush=True)

    upstream_sites, upstream_lives, upstream_parses, spider_jars = sync_upstream_generated_data()
    web_sites = sync_web_sources()

    all_raw_sites = upstream_sites + web_sites
    cleaned_alive_sites = apply_master_cleaning(all_raw_sites)

    VALID_SITE_PROPS = [
        "key", "name", "type", "api", "searchable", "quickSearch", "filterable",
        "ext", "jar", "playerType", "click", "style", "playUrl", "timeout",
        "categories", "classes", "ua", "epg", "logo", "header", "indexs", "changeable",
        "recordable", "vipUrl", "flag", "parse", "jx", "url"
    ]

    clean_sites = []
    for s in cleaned_alive_sites:
        clean_name = s.pop("_clean_name", s.get("name", ""))
        c_site = {}
        for prop in VALID_SITE_PROPS:
            if prop in s:
                c_site[prop] = s[prop]

        c_site["key"] = s.get("key", clean_name)
        c_site["name"] = clean_name
        if "type" not in c_site: c_site["type"] = 1
        if "searchable" not in c_site: c_site["searchable"] = 1
        if "quickSearch" not in c_site: c_site["quickSearch"] = 1
        if "filterable" not in c_site: c_site["filterable"] = 1

        clean_sites.append(c_site)

    DEFAULT_SPIDER = "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/jar/custom_spider.jar"

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
        "wallpaper": "https://bing.img.run/1920x1080.php",
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
    print(f"\n[OK] 生成主单仓配置文件: tvbox.json ({len(clean_sites)} 个纯净站点)", flush=True)

    build_multi_store()
    export_router_rules(clean_sites)

    with open(os.path.join(WORK_DIR, "sources.txt"), "w", encoding="utf-8") as f:
        f.write(f"# TVBox 纯净全量资源汇总 ({time.strftime('%Y-%m-%d %H:%M:%S')})\n\n")
        for s in clean_sites:
            f.write(f"{s['name']}\n{s['api']}\n\n")

    print("\n[5/5] 完成！所有产物已准备完毕。", flush=True)

if __name__ == "__main__":
    main()
