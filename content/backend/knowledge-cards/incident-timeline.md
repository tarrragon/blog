---
title: "Incident Timeline"
date: 2026-06-22
description: "說明事故時間線如何支援判斷、溝通與復盤"
weight: 153
tags: ["backend", "observability", "incident-response"]
---

Incident timeline 的核心概念是「按時間順序記錄事故中的觀測、決策與操作」。時間線是事故的共同事實來源，讓團隊可以對齊發生順序與影響變化。

## 概念位置

Timeline 連接 [alert](/backend/knowledge-cards/alert/) 觸發（事故何時被偵測到）、[on-call](/backend/knowledge-cards/on-call/) 回應（何時開始處理）、操作紀錄（做了什麼）、影響變化（使用者影響何時改善 / 惡化）跟 [post-incident review](/backend/knowledge-cards/post-incident-review/)（復盤時重建因果鏈）。

Timeline 也是 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 的時間軸基礎 — decision log 記錄「在這個時間點、基於這個觀測、做了這個決策」，timeline 提供「這個時間點」的上下文。

## 使用情境

系統需要 incident timeline 的訊號是事故後大家對「先發生什麼」說法不同。若沒有一致時間軸，復盤時很難判斷哪個操作真正帶來改善、哪個決策在當時是合理的。

## 設計責任

Timeline 要包含時間戳（UTC、精確到分鐘）、訊號來源（哪個 [dashboard](/backend/knowledge-cards/dashboard/) / [alert](/backend/knowledge-cards/alert/) / 人為觀察）、操作內容（restart / rollback / scale）、決策理由與結果驗證。記錄方式應簡潔且可在高壓下維持更新 — 事故中寫 timeline 的成本太高會導致沒人寫。Slack channel pinned message 或事故管理工具的自動 timeline 是常見實作。
