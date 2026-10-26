# 生信知识库

这是从本地知识库生成的静态阅读站点，由 GitHub Pages 托管。

> 当前站点为临时无口令公开版本。`docs/` 下已发布的笔记、索引和配图均为明文，任何访客都可以直接读取。构建仍会排除私有内容、草稿、收件箱和日志。

站点地址：<https://han-z02.github.io/bioinfo-knowledge-base/>

## 内容板块

- 文献整理
- 口腔生信研究
- 生信教程与工具
- AI 与自动化

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
