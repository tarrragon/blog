---
title: "7.1 攻擊者視角（紅隊）與攻擊面驗證"
date: 2026-04-24
description: "從攻擊者角度盤點暴露面、邊界、濫用路徑與資料外洩風險"
weight: 71
---

紅隊子分類的核心目標是建立一條可操作的風險判讀路徑：先盤點攻擊面，再檢查流程濫用、資料外洩、資源濫用與設定風險。這裡的紅隊定位為攻擊者視角的風險檢查與設計驗證。章節內容使用技術文章格式，聚焦情境判讀、代價分析與設計取捨，名詞定義則統一放在 knowledge cards。

## 暫定分類

| 分類                     | 內容方向                                                              |
| ------------------------ | --------------------------------------------------------------------- |
| Attack surface           | public API、admin route、webhook、diagnostic endpoint、upload         |
| Trust boundary           | auth boundary、tenant boundary、network boundary、internal capability |
| Abuse case               | export abuse、invite abuse、reset abuse、trial abuse                  |
| Data exposure path       | response、log、search index、support tool、backup                     |
| Resource abuse           | rate limit bypass、bot traffic、expensive operation、queue saturation |
| Misconfiguration surface | debug flag、open CORS、default credential、cloud policy               |

## 選型入口

紅隊分析優先問「攻擊者最先會找哪裡」。如果一個功能能被枚舉、被猜測、被重放、被跨 tenant 存取、被帶出內網、被放大流量或被錯誤設定打開，這個功能就應該被優先放進攻擊者視角檢查清單。

## 與安全主模組的關係

本子分類與資安主模組形成互補，並從相反方向驗證防護是否成立。資安主模組從「應該如何保護」出發；紅隊子分類從「哪裡會被打穿」出發，兩者共用同一批卡片，只是觀察角度不同。

## 章節列表

| 章節                                               | 主題                         | 目標                                             |
| -------------------------------------------------- | ---------------------------- | ------------------------------------------------ |
| [7.R0](red-team-basics-and-attack-flow/)           | 紅隊基礎與常見攻擊流程       | 建立共同詞彙與流程判讀框架                       |
| [7.R1](attack-surface-boundary/)                   | 攻擊面與信任邊界             | 確認哪些入口與資源先被看見                       |
| [7.R2](abuse-paths/)                               | 入口濫用與權限突破           | 確認合法功能是否能被惡意組合                     |
| [7.R3](exposure-and-exfiltration/)                 | 資料暴露與外洩路徑           | 確認資料會從哪些路徑流出                         |
| [7.R4](resource-abuse/)                            | 資源濫用與可用性破壞         | 確認哪些操作會被放大成壓力                       |
| [7.R5](misconfiguration-and-hidden-entrypoints/)   | 設定錯誤與隱藏入口           | 確認哪些預設值或 debug 面會暴露能力              |
| [7.R6](incident-stories-by-attack-stage/)          | 事故故事：按攻擊流程拆解弱點 | 用公開事故理解不同環節的失效模式與取捨           |
| [7.R7](cases/)                                     | 事故案例庫（可引用）         | 讓服務章節可引用「缺少哪個 workflow 會重演事故」 |
| [7.R8](control-failure-patterns/)                  | 控制面失效樣式               | 把攻擊結果回推成可重用的失效樣式語言             |
| [7.R9](adversary-cost-and-campaign-cadence/)       | 攻擊者成本與行動節奏         | 用成本與收益排序優先防守環節                     |
| [7.R10](detection-evasion-and-observability-gaps/) | 偵測迴避與觀測缺口           | 從攻擊者角度補強觀測盲區判讀                     |
| [7.R11](problem-cards/)                            | 流程濫用問題卡片             | 用原子卡片拆解高風險流程失效樣式                 |

本子分類會先建立判讀順序與控制面，再往後延伸到具體驗證方式與實作策略。

案例庫與 incident workflow 的雙向路由可參考 [8.8 事故報告轉 workflow](/backend/08-incident-response/incident-report-to-workflow/) 與 [案例引用地圖](cases/case-reference-map/)。
