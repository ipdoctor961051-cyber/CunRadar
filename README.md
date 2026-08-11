# 📡 CunRadar

**AI 驱动的个人信息雷达** — 自动追踪互联网上重要的人、项目和内容变化，生成每日信息日报。

不是监控工具，而是帮你从信息洪流中筛选出真正值得关注的更新。

---

## 功能

| 功能 | 说明 |
|------|------|
| 🎬 **YouTube 频道追踪** | 订阅 YouTube 频道，自动获取最新视频 |
| 📺 **B站 UP 主追踪** | 关注 B站 UP 主更新 |
| 📝 **博客 / RSS 订阅** | 任何支持 RSS 的博客或新闻源 |
| 💻 **GitHub 项目追踪** | 关注指定仓库的 commits |
| 🔥 **GitHub Trending** | 每日 GitHub 热门仓库排行榜（前 N 名） |
| 🤖 **AI 智能摘要** | 使用 DeepSeek 模型，自动生成今日技术动态摘要 |
| 📄 **HTML 日报** | 生成响应式网页报告，自动部署到 Cloudflare Pages |
| 📱 **Telegram 推送** | 每日定时推送到 Telegram 频道/群组 |

---

## 快速开始（本地测试）

### 1. 克隆仓库

```bash
git clone https://github.com/cunzhangcrypto/CunRadar.git
cd CunRadar
```

### 2. 安装依赖

```bash
pip install -e .
```

> 依赖包括：`requests`、`PyYAML`、`feedparser`、`beautifulsoup4`、`lxml`

### 3. 配置关注列表

编辑 `config/config.yaml`，添加你想追踪的博主、项目和博客：

```yaml
follow:
  youtube:
    - name: "Web3村长"
      channel_id: "UC5MbekhrH8iyFBQLbccBSRg"

  bilibili:
    - name: "Web3村长Official"
      uid: 1224034462

  rss:
    - name: "村长博客"
      url: "https://cunzhangblog.com/rss.xml"

  github:
    - name: "CunRadar"
      repo: "cunzhangcrypto/CunRadar"

  github_trending:
    enabled: true
    language: ""
    limit: 5
```

> 如果你的仓库是公开的，建议通过下文「隐私保护」的方式传入关注列表。

### 4. 配置密钥

```bash
cp .env.example .env
```

编辑 `.env`，填入实际的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

> 如果不需要 Telegram 推送，可以留空。

### 5. 运行

```bash
python -m cunradar
```

---

## 部署架构

CunRadar 由三个免费平台协作运行：

| 做什么 | 平台 | 是否免费 |
|-------|------|---------|
| 📥 数据采集 + AI 摘要 | GitHub Actions（定时运行） | ✅ 公共仓库无限额度 |
| 🗄️ 去重数据库 | GitHub Actions Cache | ✅ 公共仓库无限额度 |
| 🌐 HTML 日报展示 | Cloudflare Pages（自定义域名） | ✅ 免费计划够用 |

---

## 部署步骤

### 1. 在 Cloudflare 创建 Pages 项目

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 **Workers & Pages → Pages → Create project**
3. 项目名称填入 `cunradar`（可自定义）
4. **不要连接 git 仓库**，选择直接创建空项目即可

### 2. 在 GitHub 上创建仓库

创建一个新仓库（公开仓库才能享受无限额度），例如 `CunRadar`。

### 3. 推送代码

```bash
git init
git add .
git commit -m "init: CunRadar - AI-powered Personal Information Radar"
git branch -M main
git remote add origin https://github.com/你的用户名/CunRadar.git
git push -u origin main
```

### 4. 配置 GitHub Secrets

在仓库的 **Settings → Secrets and variables → Actions → Secrets** 中添加：

| Secret 名称 | 必须 | 说明 |
|-------------|------|------|
| `CLOUDFLARE_API_TOKEN` | ✅ 是 | Cloudflare API Token，用于部署到 Pages |
| `DEEPSEEK_API_KEY` | ✅ 是 | DeepSeek API 密钥，用于生成 AI 摘要 |
| `TELEGRAM_BOT_TOKEN` | ❌ 否 | Telegram Bot Token，不需要推送可不填 |
| `TELEGRAM_CHAT_ID` | ❌ 否 | Telegram 频道/群组 ID |

**Cloudflare API Token 获取步骤：**

1. 进入 [Cloudflare Dashboard → My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. 点击 **Create Token**
3. 选择 **Cloudflare Pages → Edit** 模板
4. 确认后复制 Token，添加到 GitHub Secrets

### 5. 配置 GitHub Variables

在 **Settings → Secrets and variables → Actions → Variables** 中添加：

| Variable 名称 | 说明 |
|---------------|------|
| `CUNRADAR_PUBLIC_URL` | 日报的公开访问地址，如 `https://cunradar.pages.dev` |
| `CUNRADAR_PROJECT_NAME` | Cloudflare Pages 项目名，默认 `cunradar` |
| `FOLLOW_CONFIG` |（可选）JSON 格式的关注列表，优先级高于 config.yaml |

设置后，Telegram 日报中的「完整日报」链接会指向这个地址。

### 6. 设置自定义域名（推荐）

1. 进入 Cloudflare Pages → 你的项目 → **Custom domains**
2. 点击 **Set up a custom domain**
3. 输入你的域名（如 `radar.czlab.com`）
4. Cloudflare 会自动配置 DNS 和 SSL 证书
5. 完成后将 `CUNRADAR_PUBLIC_URL` 更新为你的自定义域名

### 7. 触发运行

进入 **Actions → CunRadar Daily → Run workflow** 手动触发一次。

- GitHub Actions 会自动：运行采集 → 生成日报 → 部署到 Cloudflare Pages → 缓存数据库
- 以后每天按设定的时间自动运行

---

### 运行时间说明

GitHub Actions 使用 UTC 时间。编辑 `.github/workflows/daily.yml` 修改 cron 表达式：

```yaml
schedule:
  - cron: "0 0 * * *"    # 北京时间 08:00
```

| 北京时间 | UTC 时间 |
|---------|---------|
| 08:00   | `0 0 * * *` |
| 20:00   | `0 12 * * *` |
| 09:30   | `30 1 * * *` |
| 06:00   | `0 22 * * *` |

---

## 隐私保护

如果你想公开分享代码但不想暴露自己关注了哪些博主，可以通过环境变量传入关注列表，**优先级高于** `config/config.yaml`。

### 本地开发

在 `.env` 中添加（单行 JSON，博主之间用逗号分隔）：

```env
# 只关注一个博主
FOLLOW_CONFIG={"youtube":[{"name":"Web3村长","channel_id":"UC5MbekhrH8iyFBQLbccBSRg"}],"bilibili":[{"name":"Web3村长Official","uid":1224034462}],"rss":[{"name":"村长博客","url":"https://cunzhangblog.com/rss.xml"}],"github":[{"name":"CunRadar","repo":"cunzhangcrypto/CunRadar"}],"github_trending":{"enabled":true,"language":"","limit":5}}

# 多个博主（注意中间有逗号）
FOLLOW_CONFIG={"youtube":[{"name":"Web3村长","channel_id":"UC5MbekhrH8iyFBQLbccBSRg"},{"name":"Fireship","channel_id":"UCsBjURrPoezykLs9EqgamOA"}],"bilibili":[{"name":"Web3村长Official","uid":1224034462}],"rss":[{"name":"村长博客","url":"https://cunzhangblog.com/rss.xml"},{"name":"36氪","url":"https://36kr.com/feed"}],"github":[{"name":"CunRadar","repo":"cunzhangcrypto/CunRadar"}],"github_trending":{"enabled":true,"language":"","limit":5}}
```

> `.env` 已在 `.gitignore` 中，不会被提交到仓库。

### 线上部署

在 GitHub 仓库的 **Settings → Secrets and variables → Actions → Variables** 中添加：

| Variable 名称 | 说明 |
|---------------|------|
| `FOLLOW_CONFIG` | JSON 格式的关注列表（同上方格式） |

---

## 项目结构

```
CunRadar/
├── .github/workflows/
│   └── daily.yml          # GitHub Actions 定时工作流
├── config/
│   └── config.yaml        # 关注列表 & 应用配置
├── public/
│   ├── favicon.ico        # 网站图标
│   ├── logo.png           # Logo
│   └── robots.txt         # SEO
├── cunradar/
│   ├── __main__.py        # 主入口 & 流程编排
│   ├── config.py          # 配置加载器
│   ├── ai/                # AI 摘要生成
│   ├── collectors/        # 各平台采集器
│   │   ├── youtube.py
│   │   ├── bilibili.py
│   │   ├── rss.py
│   │   ├── github.py
│   │   └── base.py
│   ├── storage/           # SQLite 去重存储
│   ├── report/            # HTML 日报生成
│   └── notification/      # Telegram 推送
├── .env.example           # 环境变量模板
├── pyproject.toml         # 项目配置
└── README.md
```

---

## 自定义

### 时间窗口

默认只统计过去 24 小时内发布的内容。可在 `config/config.yaml` 中修改：

```yaml
app:
  max_item_age_hours: 48   # 改为 48 小时
```

### 首次运行兜底

当关注的博主在时间窗口内没有新内容时，CunRadar 会自动取该博主最近一条内容作为基线写入日报和数据库，确保后续运行能够正确识别新增内容。GitHub Trending 不受此影响。

---

## 技术栈

- **语言**：Python ≥ 3.12
- **AI**：DeepSeek API
- **存储**：SQLite
- **部署**：GitHub Actions + Cloudflare Pages
- **通知**：Telegram Bot API

---

## 平台安全限制

各平台的接口有一定调用频率限制，仅供参考：

| 平台 | 方式 | 建议关注上限 | 说明 |
|------|------|-------------|------|
| **B站** | 搜索 API | 50 个 UP 主以内 | 搜索接口，频率不高不会触发风控 |
| **YouTube** | RSS Feed | 无实际限制 | Google 免费服务，100+ 也没问题 |
| **RSS / 博客** | HTTP 请求 | 无实际限制 | 取决于目标网站，与订阅量关系不大 |
| **GitHub 项目** | GitHub API | 5000 次/小时 | 有 GITHUB_TOKEN 额度用不完 |
| **GitHub Trending** | 页面抓取 | 1 次/天 | 一次请求拉取排行，不存在上限问题 |

**实际瓶颈** 在于 GitHub Actions 的 **15 分钟超时**。按最慢的 B站（每个 UP 主约 2 秒延迟）计算，15 分钟可覆盖约 450 个 UP 主，远超过正常人的关注量。

---

## 可视化管理后台

`admin/` 包含一个 Cloudflare Worker + D1 管理后台，可用于管理关注源、查看运行状态并手动触发日报。
敏感的管理密码、GitHub Token 和配置读取 Token 必须通过 Worker Secrets 保存，不会写入浏览器或仓库。

部署说明见 [`admin/README.md`](admin/README.md)。

---

## License

[MIT](LICENSE)

Copyright (c) 2026 [村长实验室 czlab.com](https://czlab.com)

---

## 链接

- [村长实验室 czlab.com](https://czlab.com)
- [村长博客 cunzhangblog.com](https://cunzhangblog.com)
