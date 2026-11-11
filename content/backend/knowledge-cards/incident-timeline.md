---
title: "Incident Timeline"
date: 2026-06-22
description: "說明事故時間線如何支援判斷、溝通與復盤"
weight: 154
tags: ["backend", "observability", "incident-response"]
---

Incident timeline 的核心概念是「按時間順序記錄事故中的觀測、決策與操作」。時間線是事故的共同事實來源，連接 [alert](/backend/knowledge-cards/alert/) 觸發到 [post-incident review](/backend/knowledge-cards/post-incident-review/) 復盤，讓團隊可以對齊發生順序與影響變化。

## 跟其他概念的關係

Timeline 連接 [alert](/backend/knowledge-cards/alert/) 觸發（事故何時被偵測到）、[on-call](/backend/knowledge-cards/on-call/) 回應（何時開始處理）、操作紀錄（做了什麼）、影響變化（使用者影響何時改善 / 惡化）跟 [post-incident review](/backend/knowledge-cards/post-incident-review/)（復盤時重建因果鏈）。

Timeline 也是 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 的時間軸基礎 — decision log 記錄「在這個時間點、基於這個觀測、做了這個決策」，timeline 提供「這個時間點」的上下文。

## 使用情境

系統需要 incident timeline 的訊號是事故後大家對「先發生什麼」說法不同。若沒有一致時間軸，復盤時很難判斷哪個操作真正帶來改善、哪個決策在當時是合理的。

## 判斷條件與後果

Timeline 的每一筆缺了哪個欄位，復盤時就缺了哪一段因果。時間戳沒有統一成 UTC、精確到分鐘時，多個來源的事件排不出先後；缺訊號來源（哪個 [dashboard](/backend/knowledge-cards/dashboard/)、[alert](/backend/knowledge-cards/alert/) 或人為觀察）時，判斷不了團隊當時是被什麼觸發的；缺操作內容（restart、rollback、scale）與決策理由時，看得到指標改善，卻說不出是哪一個操作帶來的；缺結果驗證時，分不出操作是生效了，還是剛好碰上自然恢復。記錄成本是另一個條件：事故中寫一筆 timeline 的成本太高時，處置中的人不會停下來寫，紀錄出現空窗，所以常見的實作是 Slack channel 的 pinned message，或事故管理工具自動產生的 timeline。
