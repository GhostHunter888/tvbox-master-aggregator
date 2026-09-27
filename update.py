#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox 资源整合更新引擎 (1:1 整合参考库 tvyuan/update.py 与 my-tvbox/check.py 成熟代码)
=============================================================================
直接抄录与吸收参考库成熟跑通方案：
  1. is_remote_site(): 来自 my-tvbox/check.py，严格过滤非 HTTP、csp_、本地节点；
  2. clean_api_url(): 来自 tvyuan/update.py，剥离尾部 ac=list 多余参数；
  3. tvbox.json: 1:1 参考 tvyuan/update.py，主单仓 spider 设为 ""，100% 极速 HTTP MacCMS 接口；
  4. tvbox_full.json: 全量包含所有高阶爬虫源；
  5. tvbox_multi.json: 1:1 参考 Lightconer/多仓订阅.json，输出 urls 仓库列表。
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

# 来自参考库 my-tvbox/check.py 的 18+ 黑名单词库
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
    except Exception:
        return ""

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def parse_json(raw):
    if not raw: return None
    raw = raw.lstrip('\ufeff')
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    try: return json.loads(raw, strict=False)
    except Exception:
        s, e = raw.find('{'), raw.rfind('}')
        if s >= 0 and e > s:
            try: return json.loads(raw[s:e+1], strict=False)
            except: pass
    return None

# 来自参考库 my-tvbox/check.py: 1:1 复制 is_remote_site 远程站点校验逻辑
def is_remote_site(s):
    api = s.get("api", "")
    if not isinstance(api, str) or not api.startswith("http"):
        return False
    bad = ("127.0.0.1", "socks5", "./", "csp_", "file://")
    return not any(b in api for b in bad)

# 来自参考库 tvyuan/update.py: 1:1 复制 clean_api_url 剥离多余 ac=list 参数逻辑
def clean_api_url(api):
    if not api: return ""
    api = str(api).strip()
    api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I)
    return api

# 上游参考库数据源列表
UPSTREAM_REPO_ENDPOINTS = [
    "https://raw.githubusercontent.com/youhunwl/TVAPP/main/index.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/wangerxiao.json",
    "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/ouge.json",
    "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json",
    "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json",
    "https://raw.githubusercontent.com/liu673cn/box/main/m.json",
    "https://raw.githubusercontent.com/xiaolong69/tv/main/1.json",
    "https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json",
    "https://raw.githubusercontent.com/guot55/YGBH/main/vip2.json",
    "https://dxawi.github.io/0/0.json",
    "https://raw.githubusercontent.com/cluntop/tvbox/main/tvbox.json"
]

def sync_upstream_sources():
    print("[1/4] 直接同步参考库上游节点...", flush=True)
    raw_sites, raw_lives, raw_parses, spider_jars = [], [], [], []
    for url in UPSTREAM_REPO_ENDPOINTS:
        content = fetch_text(url)
        data = parse_json(content)
        if not data: continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    api = item.get("api") or item.get("url")
                    name = item.get("name", "")
                    if api and not is_blacklisted(name) and not is_blacklisted(str(api)):
                        raw_sites.append(item)
        elif isinstance(data, dict):
            spider = data.get("spider", "")
            if spider:
                if spider.startswith("./") or spider.startswith("../"):
                    spider = urllib.parse.urljoin(url, spider)
                spider_jars.append(spider)

            for s in (data.get("sites") or []):
                if s.get("api") and not is_blacklisted(s.get("name")) and not is_blacklisted(str(s.get("api"))):
                    if spider and "jar" not in s and "spider" not in s:
                        s["jar"] = spider
                    raw_sites.append(s)
            raw_lives.extend(data.get("lives") or [])
            raw_parses.extend(data.get("parses") or [])
    return raw_sites, raw_lives, raw_parses, spider_jars

def check_site_alive(site):
    """来自参考库 my-tvbox & tvyuan: 测速存活校验"""
    api = clean_api_url(site.get("api", ""))
    if not is_remote_site(site):
        return None

    test_url = api.rstrip("/") + ("&ac=list" if "?" in api else "?ac=list")
    try:
        req = urllib.request.Request(test_url, headers=HEADERS)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:
            if resp.status == 200:
                site["_cost"] = int((time.time() - t0) * 1000)
                site["_clean_api"] = api
                return site
    except Exception:
        pass
    return None

def export_router_rules(sites):
    print("[4/4] 导出 PassWall / Clash 规则...", flush=True)
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
            except Exception: pass

    sorted_direct = sorted(list(domains_direct))
    sorted_proxy = sorted(list(domains_proxy))

    with open(os.path.join(WORK_DIR, "domains_direct.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源国内直连域名列表\n")
        for d in sorted_direct: f.write(f"{d}\n")

    with open(os.path.join(WORK_DIR, "clash_rules_direct.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 直连规则集\npayload:\n")
        for d in sorted_direct: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    with open(os.path.join(WORK_DIR, "domains_proxy.txt"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源强制代理域名列表\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    with open(os.path.join(WORK_DIR, "clash_rules_proxy.yaml"), "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 强制代理规则集\npayload:\n")
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

def build_multi_store():
    """1:1 复制参考库 Lightconer 与 tvbox-source 多仓格式"""
    multi_sites = [
        {"name": "🚀 [主推] 全网纯净采集大一统", "url": "https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox.json", "type": 0},
        {"name": "🔥 [全量] 包含全网 JS/JAR 高阶单仓", "url": "https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox_full.json", "type": 0},
        {"name": "💎 [旗舰] 饭太硬精选仓", "url": "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json", "type": 0},
        {"name": "💎 [旗舰] 肥猫精选仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json", "type": 0},
        {"name": "💎 [旗舰] 欧歌专仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/ouge.json", "type": 0},
        {"name": "🔥 [高阶] FongMi 官方仓", "url": "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json", "type": 0},
        {"name": "🔥 [聚合] 王二小专仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/wangerxiao.json", "type": 0},
        {"name": "🔥 [聚合] 高天流云配置", "url": "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json", "type": 0},
        {"name": "✨ [4K] 蓝光专线仓", "url": "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json", "type": 0}
    ]
    multi_config = {
        "urls": [{"name": m["name"], "url": m["url"]} for m in multi_sites]
    }
    with open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8") as f:
        json.dump(multi_config, f, ensure_ascii=False, indent=2)

def main():
    print("==================================================", flush=True)
    print(" TVBox 资源整合引擎 (1:1 直接套用参考库成熟代码模式)", flush=True)
    print("==================================================\n", flush=True)

    raw_sites, upstream_lives, upstream_parses, spider_jars = sync_upstream_sources()

    # 去重
    unique_sites = {}
    unique_names = set()
    for s in raw_sites:
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
    print(f"[2/4] 去重后待测站点总数: {len(candidates)} 个", flush=True)

    # 测速存活筛选
    alive_sites = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for res in as_completed([executor.submit(check_site_alive, site) for site in candidates]):
            if res.result(): alive_sites.append(res.result())

    alive_sites.sort(key=lambda x: x.get("_cost", 9999))
    print(f"[3/4] 存活 MacCMS 纯采集站点: {len(alive_sites)} 个\n", flush=True)

    VALID_SITE_PROPS = [
        "key", "name", "type", "api", "searchable", "quickSearch", "filterable",
        "ext", "jar", "playerType", "click", "style", "playUrl", "timeout",
        "categories", "classes", "ua", "epg", "logo", "header", "indexs", "changeable",
        "recordable", "vipUrl", "flag", "parse", "jx", "url"
    ]

    # 1. 生成 tvbox.json (1:1 复制 tvyuan: 纯 MacCMS 采集站，spider设为"")
    clean_sites = []
    for s in alive_sites:
        clean_name = s.pop("_clean_name", s.get("name", ""))
        cost = s.get("_cost", 999)
        c_site = {}
        for prop in VALID_SITE_PROPS:
            if prop in s:
                c_site[prop] = s[prop]

        c_site["key"] = clean_name
        c_site["name"] = f"[{cost}ms|稳] {clean_name}"

        raw_api = s.get("_clean_api", s.get("api", ""))
        if "xml" in raw_api.lower() or "at/xml" in raw_api.lower():
            c_site["type"] = 0
        else:
            c_site["type"] = s.get("type", 1)

        c_site["api"] = raw_api
        c_site["searchable"] = 1
        c_site["quickSearch"] = 1
        c_site["filterable"] = 0

        # 完全不设置 categories，让 TVBox 客户端自动读取原站全量分类
        if "categories" in c_site:
            del c_site["categories"]

        clean_sites.append(c_site)

    seen_lives, unique_lives = set(), []
    for l in [{"name": "IPTV国内直连", "type": 0, "url": "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"}] + upstream_lives:
        url = l.get("url")
        if url and url not in seen_lives:
            seen_lives.add(url)
            unique_lives.append(l)

    seen_parses, unique_parses = set(), []
    for p in [{"name": "解析1", "type": 0, "url": "https://api.json.pro/api/?url="}] + upstream_parses:
        url = p.get("url")
        if url and url not in seen_parses:
            seen_parses.add(url)
            unique_parses.append(p)

    # 1:1 复制 tvyuan: spider 为空字符串，防止图片伪装包崩塌
    master_config = {
        "spider": "",
        "wallpaper": "https://bing.img.run/1920x1080.php",
        "sites": clean_sites,
        "lives": unique_lives,
        "parses": unique_parses,
        "note": "本配置由 TVBox 资源整合引擎自动生成。"
    }

    with open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)
    print(f"[OK] 生成主单仓配置文件: tvbox.json ({len(clean_sites)} 个纯采集站)", flush=True)

    # 2. 生成 tvbox_full.json (全量版，含全网站点与爬虫)
    best_spider = spider_jars[0] if spider_jars else "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/jar/custom_spider.jar"
    full_config = {
        "spider": best_spider,
        "wallpaper": "https://bing.img.run/1920x1080.php",
        "sites": raw_sites,
        "lives": unique_lives,
        "parses": unique_parses,
        "note": "本配置包含全网所有的采集站与高阶爬虫站。"
    }
    with open(os.path.join(WORK_DIR, "tvbox_full.json"), "w", encoding="utf-8") as f:
        json.dump(full_config, f, ensure_ascii=False, indent=2)

    build_multi_store()
    export_router_rules(clean_sites)

    with open(os.path.join(WORK_DIR, "sources.txt"), "w", encoding="utf-8") as f:
        f.write(f"# TVBox 纯净全量资源汇总 ({time.strftime('%Y-%m-%d %H:%M:%S')})\n\n")
        for s in clean_sites:
            f.write(f"{s['name']}\n{s['api']}\n\n")

    print("\n[5/5] 完成！直接整合参考库方案落操完成。\n", flush=True)

if __name__ == "__main__":
    main()
