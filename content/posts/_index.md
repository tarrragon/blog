---
title: "文章列表"
slug: "posts"
type: "posts"
layout: "list"
description: "blog 規範文件、Hugo/Markdown 操作經驗、AI 協作與工程心得的集散地"
tags: ["posts", "hugo", "markdown", "blog"]
---

這個資料夾收錄 blog 本身的**規範文件**、**設計/架構筆記**，以及不屬於特定語言教材區（`content/backend/`、`content/go/`、`content/python/` 等）的雜項技術筆記。

內容大致分三類：

**規範與契約** — agent / 工具鏈行為的單一真實來源，被 `AGENTS.md` 或其他 config 引用：

- [Blog Markdown 寫作規範與 mdtools 檢查](/posts/markdown-writing-spec/) — 排版規則、反釣魚校驗、卡片雙向完整性的工具化契約
- [Blog 文章模板設計：作者品質閘門與正文分工](/posts/blog-article-template-design/) — 文章模板的 blog-specific SSoT，供人類作者、Claude Code 與 Codex 共用
- [什麼是 AST — 從字串到語法樹的視角轉換](/posts/what-is-ast/) — 為什麼 blog 選 AST-based linter 而非 regex
- [mdtools：Go + goldmark 的 markdown 工具鏈設計](/posts/mdtools-design/) — 子命令架構、語言選擇 tripwire、pre-commit 與 CI 整合
- [教學模組的 Backlog 段格式規範](/posts/backlog-format-spec/) — 模組未完成工作的段名、四欄與不進表的三類內容

**Hugo 與 Markdown 操作經驗** — 具體寫作與渲染問題的事故紀錄。

**AI 協作與工程心得** — CI 自動除錯、技術寫作結構、專案經營相關反思。

底下自動列出本資料夾的所有文章，依日期排序。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                   | 類型   | 前置條件                                                                        | 規模 |
| -------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------- | ---- |
| 判斷「slug 必填」要不要做成 mdtools 規則                                               | 跨模組 | 無（前置的 slug 補齊已完成、四個 permalink section 存量歸零，誤報成本可評估了） | 小   |
| skill-mirror 加 --check：走 mapping table 比對 principle 卡與它的 report / record 本體 | 跨模組 | 無                                                                              | 小   |
| skill-mirror Step 4 改成遞迴，讓 references/principles/ 也能有 content 鏡像            | 跨模組 | 先決定 principle 卡要不要對外公開                                               | 小   |
| description 的四種觸發句型進 mdtools 警告層，配路徑豁免清單                            | 跨模組 | 無                                                                              | 中   |
| principle-mirror-check 接進 pre-commit 或 CI                                           | 跨模組 | skill-mirror --check 完成                                                       | 小   |
