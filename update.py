#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TVBox 资源全量整合更新引擎 (三阶段解耦防污染架构版)
=============================================================================
完全遵循用户的三阶段物理防线策略：
  阶段 1: 整合与去重（不改变原有任何节点的内置属性，保留所有爬虫包和扩展字段）。
  阶段 2: 提取纯净采集站（只清洗 18+ 黑名单词，不强加 Category，由 TVBox 自行加载全量分类）。
  阶段 3: 构建完美门面站点（由用户提供的最高层人工调优节点镇守 sites[0]，保证 100% 秒出分类大门）。
=============================================================================
"""

import json
import os
import re
import ssl
import sys
import time
import subprocess
import urllib.parse
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
CF_PROXY = os.environ.get("CF_PROXY", "")  # Cloudflare Worker 代理地址

# =========================================================
# 【零层配置】用户提供的最高层门面节点（镇守 sites[0]）
# 此节点由用户亲手调优，拥有绝对完美 categories 列表
# =========================================================
ROOT_TOP_SITE = {
    "key": "OK资源",
    "name": "OK资源",
    "type": 2,
    "api": "https://api.okzyw.net/api.php/provide/vod/?ac=list",
    "searchable": 1,
    "quickSearch": 1,
    "filterable": 0,
    "categories": [
        "电影", "国产剧", "欧美剧", "韩剧", "日剧", "泰剧", "港剧", "台剧",
        "海外剧", "netflix自制剧", "综艺", "动漫", "爽文短剧", "影视解说", "体育赛事"
    ]
}

# 18+ 黑名单词库，用于阶段 2 纯净清洗
SEX_KEYWORDS = [
    "x站", "18+", "色情", "伦理", "成人", "福利", "三级", "激情", "av",
    "杏吧", "极品x", "免费x", "嘿嘿", "火速", "红楼", "优优", "天美",
    "香蕉", "番茄", "黑料", "黄色仓库", "小鸡", "细胞", "大地", "奶香香",
    "桃花", "ck伦理", "大奶子", "搜av", "奥斯卡", "jkun", "滴滴", "豆豆",
    "精品x", "鲨鱼", "辣椒", "森林", "155", "色猫", "乐播", "玉兔",
    "老色p", "老色批", "番号", "sex", "adult", "porn", "91", "黄",
    "久草", "大x子", "老色x", "写真"
]

UPSTREAM_REPO_ENDPOINTS = [
    ("youhun", "https://raw.githubusercontent.com/youhunwl/TVAPP/main/index.json"),
    ("feimao", "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/feimao.json"),
    ("4k", "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/4k.json"),
    ("wangerxiao", "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/wangerxiao.json"),
    ("ouge", "https://cdn.jsdelivr.net/gh/Lightconer/tvbox-ysc-config@main/output/ouge.json"),
    ("CatVodSpider", "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/json/config.json"),
    ("gaotianliuyun", "https://raw.githubusercontent.com/gaotianliuyun/gao/master/js.json"),
    ("Yoursmile7", "https://raw.githubusercontent.com/Yoursmile7/TVBox/main/XC.json"),
    ("liu673cn", "https://raw.githubusercontent.com/liu673cn/box/main/m.json"),
    ("xiaolong69", "https://raw.githubusercontent.com/xiaolong69/tv/main/1.json"),
    ("xyq", "https://raw.githubusercontent.com/xyq254245/xyqonlinerule/main/XYQTVBox.json"),
    ("guot55", "https://raw.githubusercontent.com/guot55/YGBH/main/vip2.json"),
    ("dxawi", "https://dxawi.github.io/0/0.json"),
    ("mymine", "https://raw.githubusercontent.com/mymine/CatVodSpider/main/json/config.json"),
    ("cluntop", "https://raw.githubusercontent.com/cluntop/tvbox/main/tvbox.json"),
    ("okay", "https://raw.githubusercontent.com/songlees355-wq/okay/main/tvbox.json")
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
                except Exception:
                    return raw_data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def is_garbled_name(name):
    if not name: return True
    if re.search(r'[рҹв”еҗҲйӣҶзҒ«]', name):
        return True
    return False

def curl(url, timeout=10, via_proxy=False):
    actual_url = f"{CF_PROXY}?u={urllib.parse.quote(url, safe='')}" if (via_proxy and CF_PROXY) else url
    try:
        r = subprocess.run(["curl", "-s", "-L", "--connect-timeout", str(timeout),
                           "--max-time", str(timeout*2), "-A", "Mozilla/5.0", actual_url],
                          capture_output=True, timeout=timeout*2+5)
        return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""

def parse_json(raw):
    if not raw: return None
    raw = raw.lstrip('﻿')
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    try: return json.loads(raw, strict=False)
    except Exception:
        s, e = raw.find('{'), raw.rfind('}')
        if s >= 0 and e > s:
            try: return json.loads(raw[s:e+1], strict=False)
            except Exception: pass
    return None

def resolve_spider(spider, source_url):
    if not spider: return ""
    if spider.startswith("http"): return spider
    if spider.startswith("./"):
        p = urlparse(source_url)
        return f"{p.scheme}://{p.netloc}{spider[1:]}"
    return spider

def resolve_url(base, path):
    if path.startswith("http"): return path
    if path.startswith("/"): return f"{urlparse(base).scheme}://{urlparse(base).netloc}{path}"
    return urljoin(base, path)

def extract_m3u8(t):
    return re.findall(r'(https?://[^\s"\'<>#\$]+?\.m3u8)', t)

def get_segments(media, media_url):
    urls = []
    lines = media.strip().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and i+1 < len(lines):
            nxt = lines[i+1].strip()
            if nxt and not nxt.startswith("#"):
                urls.append(resolve_url(media_url, nxt))
    return urls

def build_url(base, params):
    return base.rstrip("/") + ("&" if "?" in base else "?") + params

def clean_api_url(api):
    if not api: return ""
    api = str(api).strip()
    api = re.sub(r'[\?&]ac=(list|detail|videolist|vod).*$', '', api, flags=re.I)
    return api

def is_remote_site(s):
    api = s.get("api", "")
    if not isinstance(api, str) or not api.startswith("http"):
        return False
    bad = ("127.0.0.1", "socks5", "./", "csp_", "file://")
    return not any(b in api for b in bad)

def test_play_speed(api, stype, use_proxy=False):
    """真实分片播放测速引擎 (来自 tvyuan)"""
    base = clean_api_url(api)
    body = curl(build_url(base, "ac=list"), 15, via_proxy=use_proxy)
    if not body or len(body) < 50: return 0, 0, "列表失败"

    vids = []
    if stype == 0:
        vids = re.findall(r'<id>(\d+)</id>', body)[:3]
    else:
        try:
            j = json.loads(body, strict=False)
            vids = [str(v["vod_id"]) for v in (j.get("list") or [])[:3]]
        except Exception:
            return 0, 0, "解析失败"
    if not vids: return 0, 0, "无ID"

    for vid in vids:
        detail = curl(build_url(base, f"ac=detail&ids={vid}"), 15, via_proxy=use_proxy)
        if not detail: continue
        m3u8s = []
        if stype == 0:
            m3u8s = extract_m3u8(detail)
        else:
            try:
                dj = json.loads(detail, strict=False)
                for v in (dj.get("list") or []):
                    m3u8s.extend(extract_m3u8(v.get("vod_play_url", "")))
            except Exception:
                continue
        if not m3u8s: continue

        for play in m3u8s[:2]:
            t0 = time.time()
            master = curl(play, 15, via_proxy=use_proxy)
            ttfb = int((time.time() - t0) * 1000)
            if not master: continue
            media_url = None
            if "#EXT-X-STREAM-INF" in master:
                for i, line in enumerate(master.strip().split("\n")):
                    if "STREAM-INF" in line:
                        sub = master.strip().split("\n")[i+1].strip() if i+1 < len(master.strip().split("\n")) else ""
                        if sub and not sub.startswith("#"):
                            media_url = resolve_url(play, sub); break
            elif "#EXTINF" in master: media_url = play
            if not media_url: continue
            t1 = time.time()
            media = curl(media_url, 15, via_proxy=use_proxy)
            mms = int((time.time() - t1) * 1000)
            if "#EXTINF" not in media: continue
            segs = get_segments(media, media_url)
            if not segs: continue

            tb, tt, ok = 0, 0, 0
            for s in segs[:8]:
                if ok >= 3: break
                seg_url = f"{CF_PROXY}?u={urllib.parse.quote(s, safe='')}" if (use_proxy and CF_PROXY) else s
                r = subprocess.run(["curl", "-s", "-o", "/dev/null",
                                   "-w", "%{http_code},%{size_download},%{time_total}",
                                   "--connect-timeout", "8", "--max-time", "20", seg_url],
                                  capture_output=True, timeout=25)
                parts = r.stdout.decode().strip().split(",")
                code = parts[0] if parts else "000"
                sz = int(float(parts[1])) if len(parts) > 1 and parts[1] else 0
                dl = float(parts[2]) if len(parts) > 2 and parts[2] else 99
                if code.startswith("2") and sz > 1000: tb += sz; tt += dl; ok += 1
            if ok >= 2:
                speed = int((tb / 1024) / tt) if tt > 0 else 0
                return ttfb + mms, speed, "OK"
    return 0, 0, "全部失败"

def check_source_lat(item):
    name, url = item
    try:
        t0 = time.time()
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                           "--connect-timeout", "5", "--max-time", "10",
                           "-L", "-A", "Mozilla/5.0", url],
                          capture_output=True, timeout=15)
        code = r.stdout.decode().strip()
        if code.startswith(("2", "3")):
            lat = int((time.time() - t0) * 1000)
            return (name, url, lat)
    except Exception: pass
    return None

def test_api_speed_task(item):
    api, (src_name, stype) = item
    for attempt in range(2):
        use_proxy = (attempt == 1 and CF_PROXY)
        ttfb, speed, st = test_play_speed(api, stype, use_proxy=use_proxy)
        if st == "OK":
            return (ttfb, speed, api, stype)
    return None

def export_router_rules(sites):
    print("  [策略导出] 导出 PassWall / Clash 直连与代理策略...")
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

def main():
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] 开始 TVBox 全量资源整合 (多重物理隔离防污染版)...")

    # 1. 获取所有上游配置库
    html = curl("https://tvbox.clbug.com/user.php", 20)
    src_urls = re.findall(r'data-url="([^"]+)"', html)
    src_names = re.findall(r'<td class="td-name">([^<]+)</td>', html)
    sources = [(n.strip(), u.strip().replace("&amp;", "&"))
               for n, u in zip(src_names, src_urls)
               if u.strip() and not u.strip().startswith("#")]

    zzzy_html = fetch_text("https://www.zzzypro.com/")
    if zzzy_html:
        part = zzzy_html.split("❶影视资源")[1] if "❶影视资源" in zzzy_html else zzzy_html
        if "❷X站资源" in part: part = part.split("❷X站资源")[0]
        for raw_url, name in re.findall(r'<a[^>]+data-url=["\']([^"\']+)["\'][^>]*>.*?<strong>([^<]+)</strong>', part, re.I):
            name, raw_url = name.strip(), raw_url.strip().rstrip("/")
            if not is_blacklisted(name) and not is_blacklisted(raw_url):
                api_url = f"{'https://' if not raw_url.startswith('http') else ''}{raw_url}/api.php/provide/vod/"
                sources.append((name, api_url))

    for gname, gurl in UPSTREAM_REPO_ENDPOINTS:
        sources.append((gname, gurl))

    print(f"  [阶段一] 合并 {len(sources)} 个全网配置源...")

    available = []
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(check_source_lat, s) for s in sources]
        for f in as_completed(futures):
            res = f.result()
            if res: available.append(res)
    available.sort(key=lambda x: x[2])
    print(f"  └─ 存活配置源: {len(available)} 个")

    # 2. 【阶段一：物理原样保留】提取全网节点并不做任何属性破坏
    all_sites, all_lives, all_parses = [], [], []
    site_keys, live_keys, parse_keys = set(), set(), set()
    spider_jars = {}
    collect_sources = {}

    for name, url, lat in available:
        data = parse_json(curl(url, 15))
        if not data: continue

        spider = data.get("spider", "")
        if spider:
            abs_spider = resolve_spider(spider, url)
            spider_jars[abs_spider] = spider_jars.get(abs_spider, 0) + 1

        for s in (data.get("sites") or []):
            key = s.get("key", "")
            raw_name = s.get("name", key)
            api = s.get("api", "")
            if not key or is_blacklisted(raw_name) or is_blacklisted(str(api)):
                continue

            clean_n = re.sub(r'^\[.*?\]\s*', '', raw_name).strip()
            if is_garbled_name(clean_n): continue

            unique_key = f"{key}_{lat}"
            if unique_key in site_keys: continue
            site_keys.add(unique_key)

            s["key"] = unique_key
            s["name"] = f"[{lat}ms|{name}] {clean_n}"
            s["_lat"] = lat

            # 绑定上游原厂 Spider，绝不乱碰其他原厂属性
            if spider and "jar" not in s and "spider" not in s:
                s["jar"] = resolve_spider(spider, url)

            all_sites.append(s)

            st = s.get("type", -1)
            # 记录纯 HTTP 的远程采集站，备选第二阶段清洗池
            if st in (0, 1) and is_remote_site(s) and api not in collect_sources:
                collect_sources[api] = (name, st)

        for l in (data.get("lives") or []):
            u = l.get("url", "")
            if u and u not in live_keys: live_keys.add(u); all_lives.append(l)
        for p in (data.get("parses") or []):
            u = p.get("url", "")
            if u and u not in parse_keys: parse_keys.add(u); all_parses.append(p)

    # 3. 【阶段二：纯净清洗采集站】高并发测速
    print(f"  [阶段二] 开始 {len(collect_sources)} 个纯采集站并发测速清洗...")
    collect_results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(test_api_speed_task, item) for item in collect_sources.items()]
        for f in as_completed(futures):
            res = f.result()
            if res: collect_results.append(res)
    collect_results.sort(key=lambda x: (-x[1], x[0]))

    # 4. 生成 tvbox_full.json (包含所有爬虫和提取的原属性，未受任何污染)
    best_spider = max(spider_jars, key=spider_jars.get) if spider_jars else "https://raw.githubusercontent.com/FongMi/CatVodSpider/main/jar/custom_spider.jar"
    full_json = {"spider": best_spider, "sites": all_sites, "lives": all_lives, "parses": all_parses}
    with open(os.path.join(WORK_DIR, "tvbox_full.json"), "w", encoding="utf-8") as f:
        json.dump(full_json, f, ensure_ascii=False, indent=2)
    print(f"  └─ 全量配置版 (tvbox_full.json): {len(all_sites)} 站点 原样保留")

    # 5. 生成 tvbox_multi.json (多仓列表)
    multi_stores = [
        {"sourceName": f"[{lat}ms] {name}", "sourceUrl": url} for name, url, lat in available
    ]
    multi_urls = [
        {"name": f"[{lat}ms] {name}", "url": url} for name, url, lat in available
    ]
    multi = {
        "urls": multi_urls,
        "stores": multi_stores,
        "storeHouse": multi_stores
    }
    with open(os.path.join(WORK_DIR, "tvbox_multi.json"), "w", encoding="utf-8") as f:
        json.dump(multi, f, ensure_ascii=False, indent=2)
    print(f"  └─ 多仓配置版 (tvbox_multi.json): {len(available)} 个仓库")

    # 6. 【阶段三：自建完美门面兜底】生成主单仓 tvbox.json
    # 用户给定的最稳定解析与过滤基础底座
    DEFAULT_IJK = [
        {"group": "软解码", "options": [{"category": 4, "name": "opensles", "value": "0"}, {"category": 4, "name": "overlay-format", "value": "842225234"}, {"category": 4, "name": "framedrop", "value": "1"}, {"category": 4, "name": "soundtouch", "value": "1"}, {"category": 4, "name": "start-on-prepared", "value": "1"}, {"category": 1, "name": "http-detect-range-support", "value": "0"}, {"category": 1, "name": "fflags", "value": "fastseek"}, {"category": 2, "name": "skip_loop_filter", "value": "48"}, {"category": 4, "name": "reconnect", "value": "1"}, {"category": 4, "name": "max-buffer-size", "value": "5242880"}, {"category": 4, "name": "enable-accurate-seek", "value": "0"}, {"category": 4, "name": "mediacodec", "value": "0"}, {"category": 4, "name": "mediacodec-auto-rotate", "value": "0"}, {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "0"}, {"category": 4, "name": "mediacodec-hevc", "value": "0"}]},
        {"group": "硬解码", "options": [{"category": 4, "name": "opensles", "value": "0"}, {"category": 4, "name": "overlay-format", "value": "842225234"}, {"category": 4, "name": "framedrop", "value": "1"}, {"category": 4, "name": "soundtouch", "value": "1"}, {"category": 4, "name": "start-on-prepared", "value": "1"}, {"category": 1, "name": "http-detect-range-support", "value": "0"}, {"category": 1, "name": "fflags", "value": "fastseek"}, {"category": 2, "name": "skip_loop_filter", "value": "48"}, {"category": 4, "name": "reconnect", "value": "1"}, {"category": 4, "name": "max-buffer-size", "value": "5242880"}, {"category": 4, "name": "enable-accurate-seek", "value": "0"}, {"category": 4, "name": "mediacodec", "value": "1"}, {"category": 4, "name": "mediacodec-auto-rotate", "value": "1"}, {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "1"}, {"category": 4, "name": "mediacodec-hevc", "value": "1"}]}
    ]

    DEFAULT_ADS = [
        "mimg.0c1q0l.cn", "www.googletagmanager.com", "www.google-analytics.com", "mc.usihnbcq.cn", "mg.g1mm3d.cn", "mscs.svaeuzh.cn", "cnzz.hhttm.top", "tp.vinuxhome.com", "cnzz.mmstat.com", "www.baihuillq.com", "s23.cnzz.com", "z3.cnzz.com", "c.cnzz.com", "stj.v1vo.top", "z12.cnzz.com", "img.mosflower.cn", "tips.gamevvip.com", "ehwe.yhdtns.com", "xdn.cqqc3.com", "www.jixunkyy.cn", "sp.chemacid.cn", "hm.baidu.com", "s9.cnzz.com", "z6.cnzz.com", "um.cavuc.com", "mav.mavuz.com", "wofwk.aoidf3.com", "z5.cnzz.com", "xc.hubeijieshikj.cn", "tj.tianwenhu.com", "xg.gars57.cn", "k.jinxiuzhilv.com", "cdn.bootcss.com", "ppl.xunzhuo123.com", "xomk.jiangjunmh.top", "img.xunzhuo123.com", "z1.cnzz.com", "s13.cnzz.com", "xg.huataisangao.cn", "z7.cnzz.com", "xg.huataisangao.cn", "z2.cnzz.com", "s96.cnzz.com", "q11.cnzz.com", "thy.dacedsfa.cn", "xg.whsbpw.cn", "s19.cnzz.com", "z8.cnzz.com", "s4.cnzz.com", "f5w.as12df.top", "ae01.alicdn.com", "www.92424.cn", "k.wudejia.com", "vivovip.mmszxc.top", "qiu.xixiqiu.com", "cdnjs.hnfenxun.com", "cms.qdwght.com"
    ]

    SIMPLE_LIMIT = 20
    collect_sites = [ROOT_TOP_SITE]  # 绝对雷打不动的 0 层完美门面节点镇守第一位！

    for ttfb, speed, api, stype in collect_results[:SIMPLE_LIMIT]:
        clean_name = api.split("/")[2]
        # 回溯寻找原生数据
        for s in all_sites:
            clean_api = clean_api_url(s.get("api", ""))
            if clean_api == api or s.get("api") == api:
                clean_name = re.sub(r'^\[.*?\]\s*', '', s.get("name", clean_name))
                break

        clean_api_base = clean_api_url(api)
        stable = "稳" if speed > 500 else "中" if speed > 100 else "慢"
        final_type = 0 if ("xml" in clean_api_base.lower() or "at/xml" in clean_api_base.lower()) else stype

        new_site = {
            "key": f"site_{len(collect_sites)}_{clean_name}",  # 保证 Key 绝对不冲突覆盖
            "name": f"[{speed}KB/s|{ttfb}ms|{stable}] {clean_name}",
            "type": final_type,
            "api": clean_api_base,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 0
        }
        # 绝不去画蛇添足强塞 categories，让 TVBox 底层自动去抓原生分类
        collect_sites.append(new_site)

    collect_json = {
        "spider": "", "wallpaper": "https://bing.img.run/1920x1080.php",
        "sites": collect_sites, "lives": all_lives[:10], "parses": all_parses[:10],
        "ijk": DEFAULT_IJK, "ads": DEFAULT_ADS
    }
    with open(os.path.join(WORK_DIR, "tvbox.json"), "w", encoding="utf-8") as f:
        json.dump(collect_json, f, ensure_ascii=False, indent=2)

    print(f"  [阶段三] 完美门面兜底成功! 主单仓共 {len(collect_sites)} 个高速节点")

    # 导出路由器直连代理规则
    export_router_rules(collect_sites)
    with open(os.path.join(WORK_DIR, "sources.txt"), "w", encoding="utf-8") as f:
        f.write(f"# {ts}\n\n")
        for name, url, lat in available: f.write(f"[{lat}ms] {name}\n{url}\n\n")

    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 更新完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
