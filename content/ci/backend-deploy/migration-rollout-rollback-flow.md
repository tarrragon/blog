---
title: "後端 migration、rollout 與 rollback 流程"
date: 2026-05-21
description: "說明後端 CI/CD 如何把程式、資料 migration、流量切換與 rollback 拆成可驗證的發布流程"
tags: ["CI", "CD", "backend", "migration", "rollback"]
weight: 1
---

後端部署流程的核心責任是讓程式、資料與流量在相容窗口內推進。後端服務通常會同時依賴 database、queue、cache、外部 API 與 runtime config；CI/CD 需要把 build 成功、migration 安全、readiness 可信、rollback 可執行分成不同 gate。

## 流程定位

後端部署的主要風險是有狀態依賴。前端 artifact 可以直接回退上一份靜態檔，後端服務一旦寫入新資料、消費 queue message 或呼叫外部 side effect，rollback 就不再只是換回舊 image。發布流程要先定義新舊版本如何短暫共存，再決定 migration 與流量切換順序。

| 階段                                                        | 責任                          | 判讀訊號                                |
| ----------------------------------------------------------- | ----------------------------- | --------------------------------------- |
| Build                                                       | 產生 binary、package 或 image | 版本是否可追到 commit                   |
| Contract test                                               | 驗證 API、queue、DB 相容性    | 新舊 schema / message 是否可共存        |
| [Migration](/ci/knowledge-cards/migration/)                 | 推進資料結構與資料狀態        | 是否可漸進、可重試、可停止              |
| [Rollout strategy](/ci/knowledge-cards/rollout-strategy/)   | 分批接流量                    | readiness、error rate、latency 是否可信 |
| [Rollback strategy](/ci/knowledge-cards/rollback-strategy/) | 縮小錯誤版本影響              | 程式、資料、queue 與 config 是否可回復  |

Build 階段負責產生可部署服務。服務版本要能從 runtime 反查 commit、workflow run、image digest 與 migration 版本，讓事故時能快速定位哪一次變更進入環境。

Contract test 階段負責驗證跨邊界相容。API response、database schema、queue message 與 config key 都是契約；只測 service 內部函式，通常抓不到新舊版本並存時的破壞性變更。

[Migration](/ci/knowledge-cards/migration/) 階段負責推進資料狀態。安全 migration 通常採 expand-and-contract：先加相容欄位或表、部署可讀新舊格式的程式、回填資料，最後移除舊格式。直接在同一次 release 刪欄位與切程式，會讓 rollback 失去空間。

[Rollout strategy](/ci/knowledge-cards/rollout-strategy/) 階段負責控制新版本接到的流量。Rolling、canary 與 blue-green 都需要可信 readiness；readiness 應檢查服務能否接流量，而不只是 process alive。

[Rollback strategy](/ci/knowledge-cards/rollback-strategy/) 階段負責定義失敗時的處理路由。後端 rollback 常見做法是 app rollback、config rollback、traffic rollback 或 forward fix；資料已被新程式寫入時，forward fix 往往比直接資料回滾安全。

## Migration 順序

Migration 順序的責任是保留相容窗口。資料結構變更應讓至少兩個相鄰程式版本能共存，避免部署中途任何一端先完成都造成服務不可用。

1. 新增向前相容 schema，例如新增 nullable column 或新表。
2. 部署可同時讀舊欄位與新欄位的程式。
3. 執行 backfill 或 background migration。
4. 切換讀取來源或寫入路徑。
5. 觀察穩定後移除舊欄位、舊 index 或舊 message 格式。

這個順序的價值是可停止。若第 3 步回填異常，可以暫停 backfill，不必立即回退 app；若第 4 步切換後錯誤率升高，可以先切回舊讀取路徑，再評估資料修補。

## Rollout 判讀

Rollout 判讀要同時看技術指標與業務副作用。服務能啟動不代表能安全接流量；API error、queue lag、database lock、第三方 API 錯誤與核心業務漏斗都可能是發布問題。

| 訊號              | 判讀                          | 下一步                         |
| ----------------- | ----------------------------- | ------------------------------ |
| readiness 未通過  | 新版本尚未能接流量            | 暫停 rollout，查 config / 依賴 |
| error rate 上升   | 新版本或相依服務契約出錯      | 降低流量或切回舊版本           |
| migration lock 久 | schema 變更影響正常查詢       | 停止 migration，改成分段方案   |
| consumer lag 上升 | worker 消費速度或 message 壞  | 暫停新版 worker 或降速         |
| rollback 後仍錯   | 資料或外部 side effect 已變動 | 進入 forward fix / repair 流程 |

這些訊號要先接到發布流程。若指標只存在 dashboard 裡、workflow 不知道如何判讀，團隊仍會在事故當下靠人工臨場決策。

## 常見反模式

反模式的共同問題是把後端部署當成單一 deploy 動作。後端發布的本質是多個相依狀態的協調流程。

| 反模式                            | 風險                          | 替代做法                       |
| --------------------------------- | ----------------------------- | ------------------------------ |
| app 與 destructive migration 同步 | rollback 後舊程式失去讀取契約 | expand-and-contract            |
| readiness 只檢查 process alive    | 流量進入尚未準備好的服務      | 檢查依賴、config 與初始化狀態  |
| rollback 只切 image tag           | 資料與 queue side effect 留下 | 定義 app / data / config 路由  |
| migration 沒有 dry run            | 發布時才發現權限或鎖表問題    | staging 或 shadow 環境先跑驗證 |

## 下一步路由

- 後端部署總覽：回 [後端部署 CI/CD](../)。
- Migration 術語：讀 [Migration](/ci/knowledge-cards/migration/)。
- Gate 原理：讀 [CI gate 與 workflow 邊界](../../ci-gate-workflow-boundary/)。
