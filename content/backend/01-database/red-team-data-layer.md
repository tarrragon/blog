---
title: "1.5 攻擊者視角（紅隊）：資料層弱點判讀"
date: 2026-04-24
description: "從資料存取邊界、外洩路徑與修復代價，盤點 database 的主要弱點"
weight: 5
---

資料層紅隊判讀的核心目標是確認「誰能讀到什麼資料、資料會從哪裡流出、錯誤狀態如何回復」。這裡的紅隊指攻擊者視角的風險檢查：從可被濫用的路徑反向檢查資料邊界。database 一旦承擔 [source of truth](/backend/knowledge-cards/source-of-truth/)，弱點就同時影響正確性、隱私與可恢復性。

## 【判讀】資料層弱點的主要軸線

資料層弱點可分成三條軸線：存取邊界、狀態邊界、資料流邊界。存取邊界看 [authorization](/backend/knowledge-cards/authorization/) 與 [tenant boundary](/backend/knowledge-cards/tenant-boundary/)；狀態邊界看 [transaction](/backend/knowledge-cards/transaction/) 與 [isolation level](/backend/knowledge-cards/isolation-level/)；資料流邊界看查詢結果、匯出、備份、觀測與支援工具的資料暴露路徑。

## 【可觀察訊號】何時要提高紅隊檢查優先級

下列訊號出現時，資料層弱點通常會放大成系統風險：

- 角色與租戶模型快速增加，且查詢條件跨多個權限層
- migration 頻率提高，且 schema 與讀寫流程同時變更
- 匯出、對帳、客服查詢與搜尋索引共用同一批敏感欄位
- 事故修復高度依賴人工 SQL 與臨時腳本

## 【失敗代價】資料層弱點的代價型態

資料層弱點會把單點錯誤轉成長尾影響。越權查詢會直接造成資料洩漏；交易邊界混亂會造成部分寫入與狀態偏移；資料外洩進 [log](/backend/knowledge-cards/log/) 或備份會拉長處理週期。這些問題的共同代價是修復路徑長、稽核負擔高、信任成本上升。

## 【最低控制面】進入服務實體前要先定義

資料層在討論具體服務前，先定義四個控制面最穩定：

1. 權限模型：資料存取與角色、租戶、操作情境的對應關係。
2. 交易與一致性模型：哪些操作必須同成敗、哪些可以延遲一致。
3. 資料分級與遮罩模型：哪些欄位可回傳、可觀測、可匯出。
4. 恢復模型：錯誤資料如何比對、回復、追蹤與稽核。

## 【關聯卡片】

- [Attack Surface](/backend/knowledge-cards/attack-surface/)
- [Trust Boundary](/backend/knowledge-cards/trust-boundary/)
- [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)
- [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)
- [Audit Log](/backend/knowledge-cards/audit-log/)
