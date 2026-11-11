---
title: "Dark Launch"
date: 2026-05-12
description: "新功能上線但暫不開放 UI 入口、走 production traffic 但對用戶不可見的發布模式"
weight: 235
---

Dark launch 的核心概念是「程式碼上線、走 production traffic、但用戶看不到 UI 入口」。跟 [shadow traffic](/backend/knowledge-cards/shadow-traffic/) 不同 — dark launch 是 *真正寫入 production*、shadow 只是複製比對。可先對照 [Feature Flag](/backend/knowledge-cards/feature-flag/)。

## 跟其他概念的關係

Dark launch 用 feature flag 控制 UI 暴露、後端走 production traffic（從內部 API、cron job、employee-only access 等觸發）。目的是先驗證後端在 production 規模下穩定、再開放給用戶。跟 [shadow traffic](/backend/knowledge-cards/shadow-traffic/) 的差別是「shadow 不寫入真實狀態、dark launch 寫入但用戶看不到」。可先對照 [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/)。

## 可觀察訊號與例子

需要 dark launch 的訊號是「新功能後端有風險、想先 production-validate 再 ui-launch」。對應案例：[SeatGeek Virtual Waiting Room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 從第三方換到自建、必然有 dark launch 階段驗證 token 配發機制。

## 判斷條件與後果

Dark launch 期間後端會寫入 production，而用戶看不到入口，這兩點決定了它的結束條件、觀測對象與容量。沒有 exit criteria（穩定多久、誤差在多少以內就開放 UI）時，沒有一個值代表這個階段可以結束，dark launch 無限延長或憑感覺收尾。流量來自內部 API、cron job 或員工帳號，用戶 metric 量不到真實使用，這段期間判讀的對象是後端 metric。後端有 side effect（DB write、external API call）時，這些寫入與呼叫佔用的是正式容量，沒有算進容量規劃時，正式開放之前資料庫的寫入容量與外部 API 的呼叫額度就已經被 dark launch 用掉一部分。
