# TVBox Master 全量深度聚合与大一统纯净源

本仓库为独立的 TVBox 配置文件与直连规则自动生成引擎，运行于 GitHub Actions 云端，每小时定时自动运行，实现全网影视源的**大一统去重与纯净整合**。

---

### 🌟 核心设计理念

1. **底层大一统去重**：
   - 各种多仓/品牌仓（如饭太硬、肥猫、王二小、潇洒、欧歌等）内部有高达 80%~90% 的底层采集接口是完全重复的。
   - 本引擎通过底层 API Endpoint 主域名进行**物理级去重与存活测速**，将所有重复站点自动合并为一个干净的主频道，不再让冗余的品牌前缀污染界面，真正实现“大一统”。

2. **18+ / 色情内容彻底清除**：
   - 双重词库黑名单剔除机制，严格隔离并拦截任何低俗/色情/X站接口及分类，确保输出 100% 健康正规。

3. **路由直连提取 (PassWall / Clash)**：
   - 自动提取存活站点 API 与 CDN 域名，生成 `domains_direct.txt`（PassWall/SmartDNS 白名单）与 `clash_rules.yaml`（Clash 规则集），**强制所有视频流量走国内直连 IP，解决国外代理导致播放慢/失败的问题**。

4. **100% 走 GitHub 镜像/直链**：
   - 所有依赖的爬虫（Spider JAR/JS）与配置文件强制使用 GitHub 直链 (`raw.githubusercontent.com` / `cdn.jsdelivr.net`)。

---

### 🔗 成果订阅地址

- **大一统主单仓订阅 (推荐)**：`https://raw.githubusercontent.com/<你的用户名>/tvbox-master-aggregator/main/tvbox.json`
- **兼容多仓订阅**：`https://raw.githubusercontent.com/<你的用户名>/tvbox-master-aggregator/main/tvbox_multi.json`
- **PassWall 域名直连白名单**：`https://raw.githubusercontent.com/<你的用户名>/tvbox-master-aggregator/main/domains_direct.txt`
- **Clash 规则集**：`https://raw.githubusercontent.com/<你的用户名>/tvbox-master-aggregator/main/clash_rules.yaml`

---

### ❤️ 致谢与数据源说明 (Credits & Acknowledgments)

本项目能够实现数据的大一统与自动更新，离不开以下开源项目、维护者以及资源站点的无私奉献，在此表达诚挚的感谢：

- **FongMi / CatVodSpider** (`https://github.com/FongMi/CatVodSpider`)
- **gaotianliuyun** (`https://github.com/gaotianliuyun/gao`)
- **Yoursmile7 / TVBox** (`https://github.com/Yoursmile7/TVBox`)
- **liu673cn / box** (`https://github.com/liu673cn/box`)
- **Lightconer / tvbox-ysc-config** (`https://github.com/Lightconer/tvbox-ysc-config`)
- **youhunwl / TVAPP** (`https://github.com/youhunwl/TVAPP`)
- **tvyuan / tvbox-dc / my-tvbox / ziyuanzhan** 等开源参考库
- **zzzypro.com** 与 **clbug.com** 影视资源导航平台

*注：本仓库仅对上述公开数据进行连通性检测、黑名单筛选与域名规则提取，版权归各原作者与接口提供方所有。*
