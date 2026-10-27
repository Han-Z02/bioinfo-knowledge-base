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

## 公开版发布后检查

重新生成 `docs/` 后，先补 canonical、sitemap 和 robots 指令，再运行站点自检：

```bash
python3 scripts/build_sitemap.py
python3 scripts/check_site.py
```

`build_sitemap.py` 会为除 `404.html` 外的页面写入 canonical，并重建
`docs/sitemap.xml`。`check_site.py` 会检查：

- manifest、页面和搜索索引的笔记数量及 URL 是否一致；
- 站内链接、canonical、sitemap、robots 是否完整；
- 是否残留口令门、`site-lock`、加密 payload 或 `noindex`；
- 是否残留手机号、公网 IP 地址、共享账号凭据、本地用户绝对路径；
- 是否出现“未命名笔记”“中文标题”或重复标题等发布质量问题。

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
