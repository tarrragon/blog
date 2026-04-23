---
title: "模組七：重構實戰"
date: 2026-04-22
description: "用 Go 的 package、interface、state 與測試邊界重構逐漸變大的服務"
weight: 7
---

Go 重構的核心目標是讓邊界更清楚、測試更直接、資料競爭更少。抽象只在它能降低耦合或保護行為時才有價值；本模組用一般 Go 服務範例說明如何在程式仍可運行的前提下，從平面檔案結構逐步走向更清楚的 package、interface、state 與 adapter 邊界。

重構章節的主軸是「壓力出現後再拆分」。小型 Go 程式可以保持簡單；當 handler 過重、狀態外洩、測試困難、事件語意混亂或外部依賴變多時，再逐步引入 domain-oriented package 與 ports/adapters。這種順序比一開始套用完整分層架構更符合 Go 的工程習慣。

## 章節列表

| 章節                        | 主題                           | 關鍵收穫                                            |
| --------------------------- | ------------------------------ | --------------------------------------------------- |
| [7.1](handler-boundary/)    | 把 handler 邏輯拆成可測單元    | 分離協定處理與業務邏輯                              |
| [7.2](interface-boundary/)  | 用 interface 隔離外部依賴      | 建立小而穩定的測試替身                              |
| [7.3](dedup-refactor/)      | 事件去重邏輯的重構策略         | 保留語義鍵，降低重複流程                            |
| [7.4](state-boundary/)      | 狀態管理的安全邊界             | 用複製與鎖保護共享資料                              |
| [7.5](domain-packages/)     | 以 domain 重新整理 package     | 讓 account、job、event、workflow 這類語意邊界可見   |
| [7.6](hexagonal-migration/) | 逐步遷移到 ports/adapters 架構 | 用 ports/adapters 控制依賴方向                      |
| [7.7](composition-root/)    | composition root 與依賴組裝    | 把具體 adapter、config 與 usecase wiring 留在入口層 |
| [7.8](pressure-driven-refactor/) | 壓力出現後的重構路線      | 按壓力逐步拆邊界，讓服務變大仍可維護               |

## 本模組的重構判斷

- **先保行為，再搬結構**：每次重構都要有測試或可觀察行為保護。
- **package 代表語意邊界**：清楚的 domain 名稱能讓責任可見；`utils`、`common` 這類技術分類容易把不同概念混在一起。
- **interface 由使用端定義**：usecase 需要什麼能力，就定義什麼 port。
- **state 要有擁有者**：共享 map、slice、projection 必須集中寫入並保護 copy boundary。
- **架構不是目錄模板**：ports/adapters 的重點是依賴方向，不是固定資料夾名稱。

## 章節粒度說明

重構章節刻意維持「一章一條遷移路線」。每章會先說明壓力訊號，再給局部重構策略、測試保護、設計檢查與延伸範圍。這種安排讓讀者能照著章節做小步遷移；完整架構模板應在遷移壓力明確後再引入。

如果只想查單一概念，可以依照下列對照閱讀：

| 重構問題                             | 優先閱讀                                               |
| ------------------------------------ | ------------------------------------------------------ |
| handler 太厚                         | [把 handler 邏輯拆成可測單元](handler-boundary/)       |
| 外部依賴難測                         | [用 interface 隔離外部依賴](interface-boundary/)       |
| 事件重複或來源變多                   | [事件去重邏輯的重構策略](dedup-refactor/)              |
| 共享狀態外洩                         | [狀態管理的安全邊界](state-boundary/)                  |
| 檔案平面結構失去語意                 | [以 domain 重新整理 package](domain-packages/)         |
| 依賴方向需要穩定                     | [逐步遷移到 ports/adapters 架構](hexagonal-migration/) |
| 抽出 port 後不知道在哪裡 new adapter | [composition root 與依賴組裝](composition-root/)       |

## 本模組使用的範例主題

- 事件處理流程重構
- 共享狀態重構
- 查詢介面邊界
- feature gate 邏輯
- domain package 切分
- inbound/outbound adapter 遷移
- composition root 與依賴組裝

## 學習時間

預計 2.5 小時
