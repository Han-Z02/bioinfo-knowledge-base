# 生信知识库

这是个人知识库的加密静态阅读层，由 GitHub Pages 托管。

站点地址：https://han-z02.github.io/bioinfo-knowledge-base/

仓库中的 HTML、笔记索引和笔记内图片均为密文。请使用维护者提供的团队共享密码访问；密码不会保存在本仓库中。

公开静态加密不能替代服务器端身份认证。请勿提交原始 Markdown、明文导出或密码文件。

## 公开入口：生信图册

`docs/gallery/index.html` 是**唯一的明文页面**（不含 `kb-payload`，`gate.js` 不会接管）：

- <https://han-z02.github.io/bioinfo-knowledge-base/docs/gallery/>（或站点根下 `/gallery/`）
- 内容：图册 9 个分类卡片 + 空间转录组 6 个平台直达链接
- 目标：<https://han-z02.github.io/bioinfo-figure-gallery/>

用途是把「知识库（加密，放笔记与流程）」和「图册（公开，放图例与可跑代码）」串起来。
两者**不合并**：图册若加密，MCP 取不到参考图、外人也看不了图例。

### 重新生成 docs 后要重跑一次

`gallery/index.html` 不是 Obsidian 生成物，重新跑 `build_github_pages.mjs` 可能把它清掉。重建后执行：

```bash
cd /home/hanze/hz/hz_代码教程/10_画图网站hz/01_RAE逆向准备
python3 scripts/inject-wiki-gallery.py --wiki /path/to/bioinfo-knowledge-base
```

脚本幂等，内容没变时不会改动文件。

### 为什么没有往每页顶部加「图册」链接

`docs/` 下**所有**页面（含 `404.html`、`search.html`）都是密文页：正文与导航被整体加密进
`<script id="kb-payload">`，HTML 源码里没有明文 `<nav>`。没有可靠位置能注入链接，
硬改会破坏加密结构与校验。所以用「新增一个明文入口页」的方式，而不是改现有页。
