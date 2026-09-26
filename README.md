# TVBox 资源全量整合与策略定时更新引擎

本项目为一个独立的 TVBox 接口配置与路由规则生成系统。通过运行于 GitHub Actions 云端，实现多数据源的**动态采集、自动化去重、分类归一化与路由策略提取**。

---

## 📖 系统架构与核心特性

### 1. 多源接口整合与去重 (Integration & Deduplication)
- 自动化解析多渠道接口数据，提取底层 CMS 采集站 Endpoint。
- 采用基于主域名的去重算法，剔除跨渠道重复站点，实现接口资源的统一归并。
- 对上游站点进行高并发连通性测试与延迟评估，自动生成优化后的优先级列表。

### 2. 内容安全过滤 (Content Filtering)
- 内置词库过滤机制，全面识别并拦截违规、低俗或不合规的内容源与频道分类，确保输出数据的规范性。

### 3. 路由策略与规则提取 (Routing Rule Extraction)
- 自动提取存活站点 API 及相关 CDN 域名，生成适配不同代理环境的规则文件：
  - **`domains_direct.txt`**：适用于 PassWall、SmartDNS、MosDNS 等系统的域名直连白名单。
  - **`clash_rules.yaml`**：适用于 Clash 规则集的 `DOMAIN-SUFFIX` 格式策略配置。

### 4. 依赖资源标准化 (Standardized Dependencies)
- 接口配置中引用的外部依赖（如 Spider 爬虫模块）统一使用 GitHub 官方 Raw 与 CDN 镜像服务，保证访问的可靠性与稳定性。

---

## 🔗 配置订阅地址范例

- **全量整合配置**：`https://raw.githubusercontent.com/<username>/<repository>/main/tvbox.json`
- **兼容仓配置**：`https://raw.githubusercontent.com/<username>/<repository>/main/tvbox_multi.json`
- **PassWall 域名直连白名单**：`https://raw.githubusercontent.com/<username>/<repository>/main/domains_direct.txt`
- **Clash 规则集**：`https://raw.githubusercontent.com/<username>/<repository>/main/clash_rules.yaml`

---

## 🤝 数据源与致谢 (Credits & Acknowledgments)

本系统的自动整合与更新依赖于以下开源项目与资源导航平台的数据支持，特此表达致谢：

- **FongMi / CatVodSpider** (`https://github.com/FongMi/CatVodSpider`)
- **gaotianliuyun** (`https://github.com/gaotianliuyun/gao`)
- **Yoursmile7 / TVBox** (`https://github.com/Yoursmile7/TVBox`)
- **liu673cn / box** (`https://github.com/liu673cn/box`)
- **Lightconer / tvbox-ysc-config** (`https://github.com/Lightconer/tvbox-ysc-config`)
- **youhunwl / TVAPP** (`https://github.com/youhunwl/TVAPP`)
- **zzzypro.com** 与 **clbug.com** 资源平台

*说明：本仓库仅提供自动化数据提取、检测及规则生成服务，相关数据产权归属于原作者或提供方。*
