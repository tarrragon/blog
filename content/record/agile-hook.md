---
title: "hook使用心得"
date: 2025-10-09
draft: false
description: "基於敏捷重構方法論追加hook的心得"
tags: ["AI協作心得","hook"]
---

##

雖然我已經有在設計hook，但是有些東西靠自己想還是不夠，今天看到社群文章的提醒，才發現我低估了hook能做的事情

## 參考資料

- [蒼時弦也 的 FB](https://www.facebook.com/share/p/1DYpdCmUPy/)
- [Cash Wu 的 blog](https://blog.cashwu.com/blog/2025/claude-code-hooks-advanced-agentic-coding)
- [claude 的 hook 文件](https://docs.claude.com/zh-TW/docs/claude-code/hooks)

## 實作流程

要求claude code 閱讀 [敏捷開發方法論](agile-programing-methodology.md)，然後再要求 ai 使用 context7 查詢 hook 的文件說明，然後分析我們的流程需要哪些 hook ，再讓 ai 實作

## 實作內容

- 主線程職責檢查 (PostToolUse)
- 階段完成驗證 (Stop Hook)
- 任務分派準備度 (PreToolUse Task)
- 三重文件一致性使用 $CLAUDE_PROJECT_DIR
- 代理人回報追蹤使用 $CLAUDE_PROJECT_DIR
