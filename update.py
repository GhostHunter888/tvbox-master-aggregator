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
        print(f"      [FETCH] 请求: {url}")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            # 修改：支持尝试多种解码方式，避免遇到类似饭太硬内部乱码时抛出异常
            raw_data = resp.read()
            try:
                content = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content = raw_data.decode("gbk", errors="ignore")
                except:
                    content = raw_data.decode("utf-8", errors="ignore")

            print(f"      [FETCH] 成功获取: {url} (长度: {len(content)} bytes)")
            return content
    except Exception as e:
        print(f"      [FETCH] 失败: {url} -> 错误: {e}")
        return ""

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    for kw in SEX_KEYWORDS:
        if kw in lower_text:
            return True, kw
    return False, ""

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
    "https://raw.githubusercontent.com/cluntop/tvbox/main/json/config.json",
    "https://raw.githubusercontent.com/25175/tvyuan/master/tvbox_full.json",
    "https://raw.githubusercontent.com/25175/tvyuan/master/tvbox.json",
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/dc_full.json",
    "https://raw.githubusercontent.com/25175/tvbox-dc/master/sources_pool.json",
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/sources.json",
    "https://raw.githubusercontent.com/25175/ziyuanzhan/master/docs/data/latest.json",
    # 你新补充的仓库 (支持丰富的 js 资源站配置)
    "https://raw.githubusercontent.com/songlees355-wq/okay/main/config.json",
    "https://raw.githubusercontent.com/songlees355-wq/okay/main/tvbox.json"
]

def sync_upstream_generated_data():
    print("[1/4] === 开始拉取并解析开源数据源 ===")
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
                    if api:
                        is_black, kw = is_blacklisted(name)
                        is_black_api, kw_api = is_blacklisted(str(api))
                        if is_black or is_black_api:
                            print(f"      [过滤] 拦截违规站点: 名称='{name}' 命中: {kw or kw_api}")
                            continue

                        # 重要：不要过滤带有 ext 或 jar 的爬虫类型接口！(type=3 等)
                        # 确保 js 和 jar 的专属源(如 FongMi)完整保留
                        site_config = {"name": name, "api": str(api), "type": item.get("type", 1)}
                        if "ext" in item: site_config["ext"] = item["ext"]
                        if "jar" in item: site_config["jar"] = item["jar"]
                        if "searchable" in item: site_config["searchable"] = item["searchable"]

                        raw_sites.append(site_config)

        elif isinstance(data, dict):
            spider = data.get("spider", "")
            if spider and ("github" in spider.lower() or "jsdelivr" in spider.lower()):
                spider_jars.append(spider)
            for s in (data.get("sites") or []):
                api = s.get("api")
                name = s.get("name", "未命名")
                if api:
                    # 拦截乱码源（包含无法显示的 UTF 占位符）
                    if '' in name or '' in str(api):
                        continue

                    is_black, kw = is_blacklisted(name)
                    is_black_api, kw_api = is_blacklisted(str(api))
                    if is_black or is_black_api:
                        print(f"      [过滤] 拦截违规站点: 名称='{name}' 命中: {kw or kw_api}")
                        continue

                    raw_sites.append(s)
            raw_lives.extend(data.get("lives") or [])
            raw_parses.extend(data.get("parses") or [])

    print(f"  └─ 开源源同步完成，合计提取到 {len(raw_sites)} 个基础站点接口\n")
    return raw_sites, raw_lives, raw_parses, spider_jars

def sync_web_sources():
    print("[2/4] === 开始解析动态网页资源 (zzzypro.com & clbug.com) ===")
    web_sites = []
    html = fetch_text("https://www.zzzypro.com/")
    if html:
        part = html.split("❶影视资源")[1] if "❶影视资源" in html else html
        if "❷X站资源" in part: part = part.split("❷X站资源")[0]

        for raw_url, name in re.findall(r'<a[^>]+data-url=["\']([^"\']+)["\'][^>]*>.*?<strong>([^<]+)</strong>', part, re.I):
            name, raw_url = name.strip(), raw_url.strip().rstrip("/")
            is_black, kw = is_blacklisted(name)
            is_black_api, kw_api = is_blacklisted(raw_url)
            if is_black or is_black_api:
                continue

            api_url = f"{'https://' if not raw_url.startswith('http') else ''}{raw_url}/api.php/provide/vod/"
            web_sites.append({"name": name, "api": api_url, "type": 1})

    clbug_html = fetch_text("https://tvbox.clbug.com/user.php")
    if clbug_html:
        c_part = clbug_html.split("X站")[0] if "X站" in clbug_html else clbug_html
        for name, url in zip(re.findall(r'<td class="td-name">([^<]+)</td>', c_part), re.findall(r'data-url="([^"]+)"', c_part)):
            name, url = name.strip(), url.strip().replace("&amp;", "&")
            if not url or url.startswith("#"): continue

            is_black, kw = is_blacklisted(name)
            is_black_api, kw_api = is_blacklisted(url)
            if is_black or is_black_api:
                continue

            if url.endswith(".json") or "json" in url:
                sub_data = parse_json_safely(fetch_text(url))
                if isinstance(sub_data, dict):
                    for s in (sub_data.get("sites") or []):
                        s_name = s.get("name", "未命名")
                        s_api = s.get("api")
                        if s_api:
                            is_b1, k1 = is_blacklisted(s_name)
                            is_b2, k2 = is_blacklisted(str(s_api))
                            if is_b1 or is_b2:
                                continue
                            web_sites.append(s)

    print(f"  └─ 网页动态解析完成，合计获取到 {len(web_sites)} 个新站源\n")
    return web_sites

def check_api_alive(site):
    api = site.get("api", "")
    stype = site.get("type", 1)

    # 核心修改：如果是带有 JS/JAR/EXT 依赖的专属爬虫站点 (Type=3) 或 特殊嗅探源
    # 我们放弃对它进行原生的 MacCMS (?ac=list) 测速！
    # 因为 JS/JAR 源不支持这种标准 HTTP 测试，强行测试必定报 404/500 导致被误杀！
    # 策略：直接将这些优质专属爬虫源保留，并赋予最高极速权限进入最后名单
    if stype == 3 or "ext" in site or "jar" in site or "js" in str(site.get("name", "")).lower():
        site["_cost"] = 10  # 给予极低耗时标记，保证优质源进入并排在前面
        print(f"      [免检-直通] 高级爬虫源保留: {site['name']}")
        return site

    test_url = str(api).rstrip("/") + ("&ac=list" if "?" in str(api) else "?ac=list")
    try:
        req = urllib.request.Request(test_url, headers=HEADERS)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=5, context=SSL_CTX) as resp:
            if resp.status == 200:
                cost = int((time.time() - t0) * 1000)
                site["_cost"] = cost
                print(f"      [测速-通过] {site['name']} ({cost}ms)")
                return site
    except Exception as e:
        print(f"      [测速-失败] {site['name']} | 错误: {e}")
        pass
    return None

def apply_master_cleaning(all_sites):
    print("[3/4] === 执行深度物理去重与联通性测速 ===")
    unique_sites = {}
    unique_names = set()

    for s in all_sites:
        api = s.get("api", "")
        raw_name = s.get("name", "")
        if not api: continue

        is_b1, k1 = is_blacklisted(raw_name)
        is_b2, k2 = is_blacklisted(str(api))
        if is_b1 or is_b2:
            continue

        clean_name = re.sub(r'^\[.*?\]\s*', '', raw_name)

        # 移除强制的后缀删除代码，避免破坏原始带有 [js] [V2] [V3] 等标记的名称
        # 只去除真正的乱码前缀
        clean_name = clean_name.strip()
        if not clean_name:
            continue

        # 按 API 全路径精确去重 (避免仅靠域名去重误杀同域下的不同路径源)
        api_key = str(api).lower().strip()
        if api_key not in unique_sites and clean_name not in unique_names:
            print(f"      [去重-保留] {clean_name} (API: {api_key})")
            s["_clean_name"] = clean_name
            unique_sites[api_key] = s
            unique_names.add(clean_name)
        else:
            print(f"      [去重-剔除] 重复内容: {clean_name}")

    candidates = list(unique_sites.values())
    print(f"\n  ├─ 归一去重完毕，最终进入并发测速池站点总数: {len(candidates)} 个")

    alive_sites = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for res in as_completed([executor.submit(check_api_alive, site) for site in candidates]):
            if res.result(): alive_sites.append(res.result())

    # 按测速从小到大排序 (JS/JAR/EXT 免检源因为 cost=10 会天然排在前面)
    alive_sites.sort(key=lambda x: x.get("_cost", 9999))
    print(f"  └─ 联通测试存活可用站点: {len(alive_sites)} 个\n")
    return alive_sites

def export_router_rules(sites):
    print("[4/4] === 导出 PassWall / Clash 规则策略 (直连与代理分离) ===")

    domains_direct = set()
    domains_proxy = set()

    for s in sites:
        api = s.get("api", "")
        name = s.get("name", "")
        if api:
            try:
                # 获取净域名并移除常见 API 前缀，实现真正的泛化域名直连
                domain = urllib.parse.urlparse(str(api)).netloc.split(":")[0]
                domain = re.sub(r'^(www|api|cj|vip|v|jx|m|wap|app)\.', '', domain)

                if domain:
                    # 判断源名称中是否显式标注了需要代理的字样，或者是 github/jsdelivr 等源
                    if "代理" in name or "翻墙" in name or "科学" in name or "科学上网" in name or "github" in domain or "jsdelivr" in domain:
                        domains_proxy.add(domain)
                    else:
                        domains_direct.add(domain)
            except: pass

    sorted_direct = sorted(list(domains_direct))
    sorted_proxy = sorted(list(domains_proxy))

    # ================= 导出直连白名单 =================
    passwall_direct_path = os.path.join(WORK_DIR, "domains_direct.txt")
    with open(passwall_direct_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源国内直连域名列表 (PassWall / SmartDNS 专用)\n")
        for d in sorted_direct: f.write(f"{d}\n")

    clash_direct_path = os.path.join(WORK_DIR, "clash_rules_direct.yaml")
    with open(clash_direct_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 直连规则集 (DOMAIN-SUFFIX 格式)\npayload:\n")
        for d in sorted_direct: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    # ================= 导出强制代理名单 =================
    passwall_proxy_path = os.path.join(WORK_DIR, "domains_proxy.txt")
    with open(passwall_proxy_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源强制代理域名列表 (含 GitHub/JS 依赖及需翻墙节点)\n")
        for d in sorted_proxy: f.write(f"{d}\n")

    clash_proxy_path = os.path.join(WORK_DIR, "clash_rules_proxy.yaml")
    with open(clash_proxy_path, "w", encoding="utf-8") as f:
        f.write("# TVBox 视频源 Clash 强制代理规则集 (DOMAIN-SUFFIX 格式)\npayload:\n")
        for d in sorted_proxy: f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print(f"  ├─ 导出 {len(sorted_direct)} 个直连域名 (国内接口)")
    print(f"  └─ 导出 {len(sorted_proxy)} 个强制代理域名 (含 GitHub/JS 依赖及需翻墙节点)")

def build_multi_store(cleaned_alive_sites):
    """
    智能聚合多仓：
    将所有高阶爬虫源（即带有 JS/JAR/EXT 解析的源）独立提取为一个专门的高阶多仓，
    把相同类型或相同特征的高阶源进行物理去重合并，不再死板地引用饭太硬/肥猫的原始链接！
    """
    advanced_spiders = []

    # 遍历洗炼后的全量站源，把所有含有 ext、jar 或特定 playerType 的高级爬虫源抽离出来
    for s in cleaned_alive_sites:
        if "ext" in s or "jar" in s or s.get("type") == 3 or "js" in str(s.get("name", "")).lower():
            advanced_spiders.append(s)

    # 将这个提纯出的所有高阶源打包写入一个独立的聚合配置中
    advanced_config = {
        "spider": "https://cdn.jsdelivr.net/gh/CatVod/CatVodSpider@main/jar/custom_spider.jar",
        "sites": advanced_spiders,
        "note": "本仓库包含全网去重聚合的所有高阶 JS/JAR 专属爬虫源"
    }

    with open(os.path.join(WORK_DIR, "tvbox_advanced.json"), "w", encoding="utf-8") as f:
        json.dump(advanced_config, f, ensure_ascii=False, indent=2)

    # 重新构建多仓机制
    multi_stores = [
        {"sourceName": "🚀 [主推] 全网纯净普通大一统采集", "sourceUrl": "https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox.json"},
        {"sourceName": "🔥 [高阶] 全网聚合优质 JS/JAR 爬虫大全", "sourceUrl": "https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox_advanced.json"}
    ]
    with open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8") as f:
        json.dump({"storeHouse": multi_stores}, f, ensure_ascii=False, indent=2)
    print(f"[OK] 生成智能分类多仓: tvbox_multi.json (共 {len(multi_stores)} 大分类)")

def main():
    print("==================================================")
    print(f" TVBox 资源全量整合与自动化清洗引擎启动 ({time.strftime('%Y-%m-%d %H:%M:%S')})")
    print("==================================================\n")

    upstream_sites, upstream_lives, upstream_parses, spider_jars = sync_upstream_generated_data()
    web_sites = sync_web_sources()

    all_raw_sites = upstream_sites + web_sites
    cleaned_alive_sites = apply_master_cleaning(all_raw_sites)

    COMPREHENSIVE_CATEGORIES = [
        "电影", "电视剧", "国产剧", "少儿", "动漫", "韩剧", "美剧", "日剧", "港剧", "台剧", "泰剧", "海外剧",
        "综艺", "纪录片", "短剧", "体育", "音乐", "解说", "游戏", "戏曲"
    ]

    # 动态构建：TVBox 客户端所支持的所有已知 Site 级别配置项 (完全保留)
    # 包括但不限于各种 js, jar, ali, ext 扩展，嗅探开关，展示样式等
    VALID_SITE_PROPS = [
        "key", "name", "type", "api", "searchable", "quickSearch", "filterable",
        "ext", "jar", "playerType", "click", "style", "playUrl", "timeout",
        "categories", "ua", "epg", "logo", "header", "indexs", "changeable",
        "recordable", "vipUrl", "flag", "parse", "jx", "url"
    ]

    clean_sites = []
    for i, s in enumerate(cleaned_alive_sites):
        cost = s.pop("_cost", 0)
        clean_name = s.pop("_clean_name", s.get("name", ""))

        c_site = {}
        # 1. 动态复制该站点在源配置中原有的所有合法属性 (动态大一统继承)
        for prop in VALID_SITE_PROPS:
            if prop in s:
                c_site[prop] = s[prop]

        # 2. 覆盖和强制重写必须标准化的属性
        c_site["key"] = s.get("key", clean_name)
        c_site["name"] = clean_name

        # 对于 type=3 或 ext 的高级爬虫源，必须有特定的 type
        if "type" not in c_site:
            c_site["type"] = 1

        if "searchable" not in c_site: c_site["searchable"] = 1
        if "quickSearch" not in c_site: c_site["quickSearch"] = 1
        if "filterable" not in c_site: c_site["filterable"] = 1

        clean_sites.append(c_site)

    # 3. 仅在第一个站点添加综合默认分类，供首页顶部加载全量菜单
    if clean_sites and "categories" not in clean_sites[0]:
        clean_sites[0]["categories"] = COMPREHENSIVE_CATEGORIES

    # =======================================================================
    # 动态抓取合并全局配置项 (lives, parses, rules, flags, ads, wallpaper, warning)
    # =======================================================================

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

    # 将上游所有的 rules (嗅探规则) 彻底合并
    # 这些是饭太硬等核心仓库实现“免广、秒播”的核心灵魂
    unique_rules = [{"name": "lz", "hosts": ["lz"], "regex": ["#EXT-X-DISCONTINUITY"]},
                    {"name": "ff", "hosts": ["ff"], "regex": ["#EXT-X-DISCONTINUITY"]}]

    for r in upstream_rules if 'upstream_rules' in locals() else []:
        r_name = r.get("name")
        if r_name and not any(ur.get("name") == r_name for ur in unique_rules):
            unique_rules.append(r)

    DEFAULT_SPIDER = "https://cdn.jsdelivr.net/gh/CatVod/CatVodSpider@main/jar/custom_spider.jar"

    master_config = {
        "spider": DEFAULT_SPIDER,
        "wallpaper": "https://bing.img.run/1920x1080.php",
        "sites": clean_sites,
        "lives": unique_lives,
        "parses": unique_parses,
        "rules": unique_rules,
        "note": "本配置由 TVBox 资源全量整合引擎自动生成。致谢开源贡献者：FongMi、gaotianliuyun、Yoursmile7、liu673cn、Lightconer、zzzypro。"
    }

    with open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(master_config, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 生成整合主配置文件: tvbox.json ({len(clean_sites)} 个纯净站点)", flush=True)

    build_multi_store(clean_sites)
    export_router_rules(clean_sites)

    with open(os.path.join(WORK_DIR, "sources.txt"), "w", encoding="utf-8") as f:
        f.write(f"# TVBox 纯净全量资源汇总 ({time.strftime('%Y-%m-%d %H:%M:%S')})\n\n")
        for s in clean_sites:
            f.write(f"{s['name']}\n{s['api']}\n\n")

    print("\n[5/5] 完成！所有产物已同步写入仓库。\n", flush=True)

if __name__ == "__main__":
    main()
