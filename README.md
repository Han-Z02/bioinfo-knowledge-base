# 生信知识库

这是从本地知识库生成的静态阅读站点，由 GitHub Pages 托管。

> 当前站点为无口令公开版本，已于 2026-10-28 完成公开模式清理。`docs/` 下已发布的笔记、索引和配图均为明文，任何访客都可以直接读取。构建仍会排除私有内容、草稿、收件箱和日志。

站点地址：<https://han-z02.github.io/bioinfo-knowledge-base/>

## 内容板块

- 文献整理：44 篇
- 口腔生信研究：16 篇
- 生信教程与工具：36 篇
- AI 与自动化：22 篇

当前共发布 118 篇笔记、146 个 HTML 页面。

## 公开入口：生信图册

<https://han-z02.github.io/bioinfo-knowledge-base/gallery/>

图册站点：<https://han-z02.github.io/bioinfo-figure-gallery/>

## 恢复加密访问

配置修改完成后，在本地知识库运行 `npm run site:sync`，会按原流程重新构建并发布加密版本，恢复口令入口。

### 全站导航入口（口令取消后新增）

2026-10-27 口令被临时取消后，`docs/` 的页面变为**明文**（不再有 `<script id="kb-payload">`），
于是可以把「图册」直接加进每页导航：

| 页面类型 | 注入位置 | 链接前缀 | 数量 |
|---|---|---|---|
| 首页 / 板块页（有 `<nav class="site-nav">`） | 导航末尾追加「生信图册」 | 按深度自适应 | 约 40 页 |
| 笔记页（只有 `<div class="toolbar">`） | 工具栏追加「图册」按钮 | `../../` | 约 110 页 |

注入的标签带 `data-gallery-entry` 标记，用来做幂等与回滚。

> ⚠️ **若口令恢复，这些链接会随页面一起被重新加密而消失**，那时只剩
> `docs/gallery/index.html` 这个独立明文入口页有效。恢复口令后需要重新评估。

### 重新生成 docs 后要重跑

```bash
cd /home/hanze/hz/hz_代码教程/10_画图网站hz/01_RAE逆向准备
python3 scripts/inject-wiki-gallery.py --wiki /path/to/bioinfo-knowledge-base

# 回滚已注入的链接：
python3 scripts/inject-wiki-gallery.py --wiki ... --revert
```

脚本幂等：内容没变时不会改动文件；重复跑只会报「跳过：已注入 N」。

## 公开版发布前检查

先对本地知识库源 Markdown 做一次泄漏扫描。脚本只报告文件和行号，不打印敏感值：

```bash
python3 scripts/scan_source_secrets.py --source /path/to/local-wiki
```

重新生成 `docs/` 后，先优化搜索索引和图片加载、补 canonical/sitemap/robots，再运行站点自检：

```bash
python3 scripts/optimize_site.py
python3 scripts/curate_tags.py
python3 scripts/curate_home.py
python3 scripts/build_sitemap.py
python3 scripts/check_site.py
```

`optimize_site.py` 会把 `search.html` 中的全文索引外置为
`docs/search-index.json`，让搜索页只在首次输入时加载索引；同时为笔记图片补
`loading="lazy"`/`decoding="async"`、刷新 CSS/JS 版本号，并用 manifest 时间校正首页生成时间。
该脚本可重复运行。

`curate_tags.py` 为当前无标签的 13 篇笔记补充可检索标签，并同步更新
manifest、搜索索引、笔记页和板块卡片；如果后续在源知识库中维护标签，可跳过此脚本。

`curate_home.py` 会把 5 个库索引页从首页“最近更新”中排除，并从搜索索引补齐
最新 10 篇内容笔记，避免导航页长期占据更新列表。

`build_sitemap.py` 会为除 `404.html` 外的页面写入 canonical，并重建
`docs/sitemap.xml`。`check_site.py` 会检查：

- manifest、页面和搜索索引的笔记数量及 URL 是否一致；
- 搜索页是否已外置索引，以及搜索索引是否超过大小预算；
- 站内链接、canonical、sitemap、robots 是否完整；
- 是否残留口令门、`site-lock`、加密 payload 或 `noindex`；
- 是否残留手机号、公网 IP 地址、共享账号凭据、本地用户绝对路径；
- 是否出现“未命名笔记”“中文标题”或重复标题等发布质量问题；
- 多图页面是否遗漏图片懒加载。

仓库内的 `.github/workflows/site-check.yml` 会在 push/PR 时自动运行同一套
Python/JavaScript 静态检查。CI 只检查已生成站点；源 Markdown 仍须在构建前单独扫描。

本地预览：

```bash
python3 -m http.server 8000 -d docs
```

## 公开内容安全

2026-10-28 的公开审计已从当前发布版本中做了以下处理：

- 下线 3 篇空笔记/临时草稿和 1 篇重复剪藏；
- 为 7 篇低信息标题补充可读标题；
- 脱敏共享账号凭据、手机号、公网服务地址和本地用户绝对路径；
- 移除已失效的“锁定”按钮、解锁会话逻辑和加密版文案；
- 删除空的「API 与接入」子栏目。

修改当前文件不会删除 Git 历史中的旧内容。若历史提交曾包含真实凭据，应立刻轮换或作废该凭据；如需从历史中彻底清除，必须单独评估并重写 Git 历史。
