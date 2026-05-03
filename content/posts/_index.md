---
title: "文章列表"
slug: "posts"
type: "posts"
layout: "list"
---

這個資料夾收錄 blog 本身的**規範文件**、**設計/架構筆記**，以及不屬於特定語言教材區（`content/backend/`、`content/go/`、`content/python/` 等）的雜項技術筆記。

內容大致分三類：

**規範與契約** — agent / 工具鏈行為的單一真實來源，被 `AGENTS.md` 或其他 config 引用：

- [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/) — 排版規則、反釣魚校驗、卡片雙向完整性的工具化契約
- [Blog 文章模板設計：作者品質閘門與正文分工](/posts/blog-article-template-design/) — 文章模板的 blog-specific SSoT，供人類作者、Claude Code 與 Codex 共用
- [什麼是 AST — 從字串到語法樹的視角轉換](/posts/what-is-ast/) — 為什麼 blog 選 AST-based linter 而非 regex
- [mdtools：Go + goldmark 的 markdown 工具鏈設計](/posts/mdtools-design/) — 子命令架構、語言選擇 tripwire、pre-commit 與 CI 整合

**Hugo 與 Markdown 操作經驗** — 具體寫作與渲染問題的踩坑紀錄。

**AI 協作與工程心得** — CI 自動除錯、技術寫作結構、專案經營相關反思。

底下自動列出本資料夾的所有文章，依日期排序。
