---
title: "驗證導向的 CLI 工具文章：官方 docs 查核放過的落差類型"
date: 2026-06-15
description: "CLI 工具教學的指令正確性不能只靠官方文件查核、要實機驗證時回來。官方文件驗的是「文件說的是否正確」、驗不了「文件沒說的是否存在」。"
tags: ["writing-methodology", "cli", "verification", "docker", "retrospective"]
---

本文記錄驗證導向生產流程背後的 evidence — 為什麼官方文件查核不夠、實機驗證抓到了什麼。操作步驟維護在 `.claude/skills/verification-driven-cli/`。

## 官方文件查核放過的五類落差

`content/cli/` 五類終端機工具文章（監控 / 圖表 / 多工器 / 檔案管理 / SQL 客戶端）在實機驗證時抓到、純靠 docs 查核會放過的落差：

### 1. 旗標改名

`zellij web` 文件寫有 `--bind`，實際 0.43.1 是分開的 `--ip` 與 `--port`。讀者照文件下指令會得到 unknown flag error、但不知道正確旗標是什麼。

### 2. 設定鍵 migrate

`lazygit` 的 pager 設定文件寫 `git.paging.pager`，新版 0.62.2 改成 `git.pagers`（list）。舊鍵啟動時會被自動 migrate、改寫設定檔 — 讀者照舊文件設定後發現設定檔被工具自己改掉。

### 3. 隱含 schema prefix

`dblab` 的查詢編輯器要 schema 限定（`SELECT * FROM public.products`），裸 `products` 會報 relation 不存在。原因是編輯器連線的 search_path 不含 public — 文件沒提。

### 4. 平台特定 segfault

`nvtop` 在 Apple Silicon mac 裝得起來，但 snapshot 模式直接 segfault。GPU 後端不穩。裝成功不代表能用 — 文件只說「支援 macOS」。

### 5. Driver 差異

同一個 Postgres，`lazysql`（Go pq driver）連無 SSL 的 DB 要 `?sslmode=disable`，`pgcli` / `harlequin`（Python psycopg）不用。同樣的連線字串在不同工具會有不同行為、文件各自不提對方。

## 共通模式

這五類落差有個共通點：讀者照文件走會撞牆、卻在文件裡找不到答案。實機跑一次就現形，而且現形的正是文章最該寫的內容 — gotcha 段落省下讀者各自撞一次的時間。

官方文件的 fact-check 只能驗證「文件說的是否正確」，驗不了「文件沒說的是否存在」。實機驗證補的是後者。

## 相關連結

- Verification-driven CLI skill（`.claude/skills/verification-driven-cli/`）— 操作步驟
- [終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/) — 用此流程生產的工具文章
- [#199 一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/) — 本文精簡的依據
