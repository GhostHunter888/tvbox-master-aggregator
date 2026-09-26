# TVBox Multi-Source Aggregation and Automated Cleaning Engine

This repository is an independent TVBox configuration and routing rule generation system. Running on GitHub Actions cloud, it achieves multi-source dynamic collection, automated deduplication, category normalization, and routing strategy extraction.

---

## 📖 System Architecture & Core Features

### 1. Multi-Source Integration & Deduplication
- Automatically parses multi-channel interface data and extracts underlying CMS collection endpoints.
- Implements a domain-based deduplication algorithm to eliminate cross-channel redundant sites and achieve unified resource merging.
- Performs high-concurrency connectivity testing and latency evaluation on upstream sites to automatically generate optimized priority lists.

### 2. Content Safety Filtering
- Built-in keyword filtering mechanism to comprehensively identify and intercept non-compliant, low-quality, or adult content sources and channel categories, ensuring output data compliance.

### 3. Routing Strategy & Rule Extraction
- Automatically extracts active site APIs and related CDN domains to generate proxy-compatible rule files:
  - **`domains_direct.txt`**: Domain direct whitelist for PassWall, SmartDNS, MosDNS, etc.
  - **`clash_rules.yaml`**: `DOMAIN-SUFFIX` format strategy configuration for Clash.

### 4. Standardized Dependencies
- External dependencies referenced in configurations (such as Spider crawler modules) uniformly use official GitHub Raw and CDN mirror services to ensure access reliability and stability.

---

## 🔗 Configuration Subscription URLs

- **Full Integrated Configuration**: `https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox.json`
- **Compatible Multi-Store Configuration**: `https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/tvbox_multi.json`
- **PassWall Direct Domain Whitelist**: `https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/domains_direct.txt`
- **Clash Ruleset**: `https://raw.githubusercontent.com/haygcao/tvbox-master-aggregator/main/clash_rules.yaml`

---

## 🤝 Credits & Acknowledgments

The automated integration and updating of this system rely on data support from the following open-source projects and resource navigation platforms, with sincere gratitude:

- **FongMi / CatVodSpider** (`https://github.com/FongMi/CatVodSpider`)
- **gaotianliuyun** (`https://github.com/gaotianliuyun/gao`)
- **Yoursmile7 / TVBox** (`https://github.com/Yoursmile7/TVBox`)
- **liu673cn / box** (`https://github.com/liu673cn/box`)
- **Lightconer / tvbox-ysc-config** (`https://github.com/Lightconer/tvbox-ysc-config`)
- **youhunwl / TVAPP** (`https://github.com/youhunwl/TVAPP`)
- **zzzypro.com** & **clbug.com** resource platforms

*Note: This repository only provides automated data extraction, testing, and rule generation services. Relevant data property rights belong to the original authors or providers.*
