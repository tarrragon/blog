---
title: "Spotify：Backstage Service Catalog 與 Reliability Metadata"
date: 2026-06-23
description: "用 service catalog 治理分散團隊的可靠性資訊：ownership、SLO 狀態、依賴圖與 runbook 的單一入口。"
weight: 42
tags: ["backend", "reliability", "case-study"]
---

Service catalog 在可靠性工程中的責任是讓每個服務的 reliability metadata 有單一查詢入口。事故發生時，團隊能在同一個地方找到 owner、SLO 狀態、依賴圖與 runbook，而不是在 wiki、Slack 與個人筆記之間來回搜尋。

## 問題場景

Squad-based 組織結構讓團隊能獨立交付，但也讓服務數量快速增長。當服務超過數百個，metadata 開始散落在不同系統：ownership 記在 wiki、SLO 記在 monitoring 平台、runbook 記在文件庫、依賴關係靠口頭傳遞。事故時花時間找 owner 和 runbook 的成本直接拉長 [MTTR](/backend/knowledge-cards/mttr/)。Spotify 用 Backstage 作為 service catalog，把這些 metadata 收攏到同一個入口。

## 決策機制

| 機制               | 核心問題                   | 交付結果         |
| ------------------ | -------------------------- | ---------------- |
| Service ownership  | 這個服務歸誰管             | 強制 owner team  |
| SLO metadata       | 這個服務的可靠性承諾是什麼 | catalog 內嵌 SLO |
| Dependency graph   | 這個服務依賴誰、誰依賴它   | 可查詢依賴圖     |
| Runbook linkage    | 出事時該看哪份 runbook     | 一鍵連結         |
| Metadata freshness | catalog 資料是否仍然準確   | 過期警告機制     |

Service ownership 是最基礎的一層。每個服務在 catalog 中必須有明確的 owner team，沒有 owner 的服務標記為 orphan 並進入清理追蹤。ownership 不只是名義歸屬，而是事故時的第一接手責任。

SLO metadata 讓 catalog 不只是目錄，而是可靠性狀態的即時入口。團隊能在 catalog 頁面直接看到服務目前的 [error budget](/backend/knowledge-cards/error-budget/) 消耗狀態，判斷該服務的變更風險。

Dependency graph 的價值在事故時最明顯。當一個服務異常時，catalog 能回答「還有誰會被影響」和「這個問題可能從哪裡傳過來」，讓事故指揮能快速判斷 [blast radius](/backend/knowledge-cards/blast-radius/)。

## 可觀測訊號

| 訊號                     | 判讀重點                         | 對應章節                                                            |
| ------------------------ | -------------------------------- | ------------------------------------------------------------------- |
| Orphan service count     | 無 owner 服務是否持續增加        | [6.21](/backend/06-reliability/reliability-debt-backlog/)           |
| Metadata freshness       | catalog 資料是否仍然準確         | [6.18](/backend/06-reliability/reliability-metrics-governance/)     |
| Dependency coverage      | 依賴圖是否涵蓋關鍵路徑           | [6.14](/backend/06-reliability/dependency-reliability-budget/)      |
| MTTR vs catalog coverage | catalog 覆蓋率是否與恢復速度相關 | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |

## 常見陷阱

Catalog 最常見的失效模式是變成靜態文件。若 metadata 靠人工維護但沒有 freshness check，catalog 會隨時間漂移 — owner 換了團隊但 catalog 沒更新、SLO 調整了但 catalog 還是舊值、依賴關係變了但 graph 沒有同步。事故時從 catalog 拿到過期資訊，比沒有 catalog 更危險，因為團隊會信任它。維持 catalog 價值的關鍵是自動化校驗：定期掃描 orphan service、比對 SLO metadata 與 monitoring 平台的實際值、用 runtime trace 驗證依賴圖的準確性。

## 下一步路由

- [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)：catalog 的依賴圖是 dependency budget 的資料來源
- [6.18 reliability metrics governance](/backend/06-reliability/reliability-metrics-governance/)：catalog coverage 與 metadata freshness 本身是可靠性指標
- [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)：readiness checklist 可從 catalog 自動拉取
- [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/)：orphan service 與過期 metadata 是 reliability debt

## 引用源

- [Backstage.io](https://backstage.io/)：Spotify 開源的 developer portal 框架
- [Spotify Engineering: What is Backstage?](https://backstage.spotify.com/)：Backstage 的設計理念與架構
