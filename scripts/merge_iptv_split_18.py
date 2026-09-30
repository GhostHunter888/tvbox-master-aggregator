#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 独立任务六：美英学英语 IPTV 直播源整合与 not_suitable/ 18+ 隔离导出器
=============================================================================
重点更新：
  1. 遍历克隆在 repos/ 下的所有参考仓库中的 .m3u, .txt 直播源文件；
  2. 提取国内央视/卫视/地方台 + iptv-org 美/英/加/澳等国际英语学习频道；
  3. 彻底扩充 18+ 敏感词库 (含 色, 色播, 成人, 阴, 撸, 少女, 侄女, 妻, 草榴, 萝莉, av, 色情, 鉴黄, 黄色, 香肠, 香蕉)；
  4. 根目录 live.txt 100% 纯净，隔离目录 not_suitable/live.txt 独立收录 18+ 频道。
=============================================================================
"""

import json
import os
import re
import ssl
import urllib.request

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SEX_KEYWORDS = [
    "x站", "18+", "色情", "伦理", "成人", "福利", "三级", "激情", "av",
    "杏吧", "极品x", "免费x", "嘿嘿", "火速", "红楼", "优优", "天美",
    "香蕉", "番茄", "黑料", "黄色仓库", "小鸡", "细胞", "大地", "奶香香",
    "桃花", "ck伦理", "大奶子", "搜av", "奥斯卡", "jkun", "滴滴", "豆豆",
    "精品x", "鲨鱼", "辣椒", "森林", "155", "色猫", "乐播", "玉兔",
    "老色p", "老色批", "番号", "sex", "adult", "porn", "91", "黄",
    "久草", "大x子", "老色x", "写真",
    "①⑧", "🔞", "18/", "小师妹", "奶茶", "探探", "pgx", "小师妹资源", "奶茶资源", "探探资源", "pgx资源",
    "18av", "4kav", "18jtv", "2048", "777wuye", "8x8x", "91porn", "91crdj", "asmrhoney", "adult",
    "mamazipai", "missav", "mitaoav", "nanrenbense", "owoav", "seba", "sebo", "shaofu", "sinparty",
    "xhamster", "yiqicao", "youav", "zhengmeiav", "色播", "风欲", "萝莉av", "xxx", "nsfw",
    "色", "阴", "撸", "少女", "侄女", "妻", "草榴", "萝莉", "鉴黄", "黄色", "香肠"
]

def fetch_text(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            raw_data = resp.read()
            try:
                return raw_data.decode("utf-8")
            except UnicodeDecodeError:
                return raw_data.decode("gbk", errors="ignore")
    except Exception:
        return ""

def is_blacklisted(text):
    if not text: return False
    lower_text = str(text).lower()
    return any(kw in lower_text for kw in SEX_KEYWORDS)

def process_iptv_and_split_18():
    print("  [06_merge_iptv] 开始美英学英语 IPTV 整合与 not_suitable/ 隔离处理...", flush=True)

    ns_dir = os.path.join(WORK_DIR, "not_suitable")
    os.makedirs(ns_dir, exist_ok=True)

    clean_live_groups = {
        "央视频道": [
            ("CCTV-1 综合", "http://111.63.117.15:6060/000000001000/1000000001000019246/index.m3u8"),
            ("CCTV-2 财经", "http://111.63.117.15:6060/000000001000/1000000001000019247/index.m3u8"),
            ("CCTV-3 综艺", "http://111.63.117.15:6060/000000001000/1000000001000019248/index.m3u8"),
            ("CCTV-4 中文国际", "http://111.63.117.15:6060/000000001000/1000000001000019249/index.m3u8"),
            ("CCTV-5 体育", "http://111.63.117.15:6060/000000001000/1000000001000019250/index.m3u8"),
            ("CCTV-6 电影", "http://111.63.117.15:6060/000000001000/1000000001000019251/index.m3u8"),
            ("CCTV-13 新闻", "http://111.63.117.15:6060/000000001000/1000000001000019258/index.m3u8")
        ],
        "卫视频道": [
            ("湖南卫视", "http://111.63.117.15:6060/000000001000/1000000001000019260/index.m3u8"),
            ("浙江卫视", "http://111.63.117.15:6060/000000001000/1000000001000019261/index.m3u8"),
            ("东方卫视", "http://111.63.117.15:6060/000000001000/1000000001000019262/index.m3u8"),
            ("江苏卫视", "http://111.63.117.15:6060/000000001000/1000000001000019263/index.m3u8")
        ],
        "英语学习/美英频道": [
            ("US - ABC News Live (美国ABC新闻)", "https://content.uplynk.com/channel/3324f2467c414329b3b08f413926e446.m3u8"),
            ("US - CBS News HD (美国CBS新闻)", "https://cbsn-us.cbsnstream.cbsnews.com/main/master.m3u8"),
            ("US - Bloomberg TV HD (彭博财经)", "https://liveproduced.bloomberg.com/live/BTV_US/playlist.m3u8"),
            ("US - NASA TV HD (美国宇航局)", "https://nasa-vh.akamaihd.net/i/NASA_101@319270/master.m3u8"),
            ("US - PBS Kids (美国少儿英语)", "https://livestream.pbskids.org/out/v1/55b3d9d3000d43a68d06ee29f3d53b21/index.m3u8"),
            ("UK - BBC News HD (英国BBC新闻)", "http://158.101.222.193:88/georgia_play.php?id=bbcnews"),
            ("UK - Sky News HD (英国天空新闻)", "https://skynews-live.skynews.com/1280/skynews-live.m3u8"),
            ("UK - EuroNews English (欧洲英语台)", "https://euronews-euronews-website-main-1-gb.samsung.wurl.tv/manifest.m3u8")
        ]
    }

    adult_live_channels = [
        ("18+ 成人精选 01", "http://127.0.0.1/live/18_01.m3u8"),
        ("18+ 成人精选 02", "http://127.0.0.1/live/18_02.m3u8")
    ]

    # 1. 从磁盘 repos/ 目录下克隆的所有仓库中，深度遍历盘点直播源文件 (.m3u, .txt)
    repos_dir = os.path.join(WORK_DIR, "repos")
    if os.path.exists(repos_dir):
        for root, _, files in os.walk(repos_dir):
            for fname in files:
                if fname.endswith(".m3u") or fname.endswith(".m3u8") or fname.endswith(".txt"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                            lines = text.splitlines()
                            curr_name = ""
                            for line in lines:
                                line = line.strip()
                                if line.startswith("#EXTINF"):
                                    m_name = re.search(r',([^,]+)$', line)
                                    if m_name: curr_name = m_name.group(1).strip()
                                elif line.startswith("http") and curr_name:
                                    if is_blacklisted(curr_name) or is_blacklisted(line):
                                        adult_live_channels.append((curr_name, line))
                                    else:
                                        if any(tag in curr_name.upper() for tag in ["US", "UK", "BBC", "CNN", "CBS", "ABC", "FOX", "DISCOVERY", "NATIONAL"]):
                                            if len(clean_live_groups["英语学习/美英频道"]) < 40:
                                                clean_live_groups["英语学习/美英频道"].append((curr_name, line))
                                    curr_name = ""
                                elif "," in line and line.startswith("http"):
                                    parts = line.split(",")
                                    cname, url = parts[0].strip(), parts[1].strip()
                                    if is_blacklisted(cname) or is_blacklisted(url):
                                        adult_live_channels.append((cname, url))
                    except Exception: pass

    # 2. 从 iptv-org 在线库抓取补全
    iptv_m3u_raw = fetch_text("https://iptv-org.github.io/iptv/index.m3u")
    if iptv_m3u_raw:
        lines = iptv_m3u_raw.split("\n")
        curr_name = ""
        curr_group = ""
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                match_name = re.search(r',([^,]+)$', line)
                curr_name = match_name.group(1).strip() if match_name else "Unknown"
                match_group = re.search(r'group-title="([^"]+)"', line)
                curr_group = match_group.group(1).strip() if match_group else "International"
            elif line.startswith("http") and curr_name:
                url = line
                if is_blacklisted(curr_name) or is_blacklisted(curr_group) or is_blacklisted(url):
                    adult_live_channels.append((curr_name, url))
                else:
                    if any(tag in curr_name.upper() for tag in ["US", "UK", "BBC", "CNN", "CBS", "ABC", "FOX", "DISCOVERY", "NATIONAL GEOGRAPHIC", "BLOOMBERG"]):
                        clean_cname = re.sub(r'[\r\n\t]', '', curr_name)
                        clean_cname = re.sub(r'^\s*,\s*', '', clean_cname)
                        if len(clean_live_groups["英语学习/美英频道"]) < 40:
                            clean_live_groups["英语学习/美英频道"].append((f"US/UK - {clean_cname}", url))
                curr_name = ""

    # 3. 输出 100% 纯净的根目录 live.txt
    with open(os.path.join(WORK_DIR, "live.txt"), "w", encoding="utf-8") as f:
        for g_title, ch_list in clean_live_groups.items():
            f.write(f"{g_title},#genre#\n")
            seen_u = set()
            for cname, url in ch_list:
                if url not in seen_u:
                    seen_u.add(url)
                    f.write(f"{cname},{url}\n")
            f.write("\n")

    print(f"  ├─ 成功生成 100% 纯净根目录直播源: live.txt (含美英学英语频道)")

    # 4. 输出隔离目录 not_suitable/live.txt
    with open(os.path.join(ns_dir, "live.txt"), "w", encoding="utf-8") as f:
        f.write("特定需求频道,#genre#\n")
        seen_u = set()
        for cname, url in adult_live_channels:
            if url not in seen_u:
                seen_u.add(url)
                f.write(f"{cname},{url}\n")

    print(f"  ├─ 成功生成隔离目录直播源: not_suitable/live.txt")

    # 5. 生成隔离目录 not_suitable/tvbox.json
    tvbox_path = os.path.join(WORK_DIR, "tvbox.json")
    if os.path.exists(tvbox_path):
        try:
            with open(tvbox_path, "r", encoding="utf-8") as f:
                tvbox_data = json.load(f)

            ns_sites = []
            for s in tvbox_data.get("sites", []):
                s_name = str(s.get("name", ""))
                s_api = str(s.get("api", ""))
                if is_blacklisted(s_name) or is_blacklisted(s_api):
                    ns_sites.append(s)

            ns_tvbox = dict(tvbox_data)
            ns_tvbox["sites"] = ns_sites
            ns_tvbox["note"] = "本文件放置于隔离目录 not_suitable/，仅供特定需求单独调取。"

            with open(os.path.join(ns_dir, "tvbox.json"), "w", encoding="utf-8") as f:
                json.dump(ns_tvbox, f, ensure_ascii=False, indent=2)

            print(f"  └─ 成功生成隔离目录点播配置: not_suitable/tvbox.json")
        except Exception as e:
            print(f"  └─ 生成 not_suitable/tvbox.json 时出错: {e}")

if __name__ == "__main__":
    process_iptv_and_split_18()
