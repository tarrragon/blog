---
title: "8.23 Control Plane Decision Log and Write-back 實作示範"
date: 2026-05-08
description: "以 rule/config rollout 事故示範 decision log 與 write-back 如何形成可回放閉環。"
weight: 23
tags: ["backend", "incident-response", "decision-log", "implementation"]
---

Control plane decision log and write-back 的核心責任是讓規則或配置事故的事中判斷可回放、事後修正可追蹤。

## 服務路徑與事件邊界

示範事件是全域 rule rollout 後 CPU 激增與錯誤率上升。這類事故的難點在決策序列是否清楚、偵測本身反而容易：先限流、先回退、還是先分區隔離。

事中決策欄位固定用 `Timestamp`、`Decision`、`Context`、`Evidence`、`Owner`、`Expected effect`、`Rollback condition`。write-back 再補 `target artifact`、`closure signal`、`review date`。

## 實作步驟

1. 建立 incident intake：彙整告警、dashboard、客訴與 deploy event。
2. 啟動 decision log：每個會改變路由的動作都記錄欄位。
3. 每 10-15 分鐘更新一次 expected effect 是否達成。
4. 事故收斂後建立 write-back 條目：對應到 runbook、gate、signal 或 ownership 缺口。
5. 在下一次 readiness review 檢查 closure signal 是否達成。

## 判讀訊號

| 訊號                           | 判讀重點                       | 對應動作                           |
| ------------------------------ | ------------------------------ | ---------------------------------- |
| 事故頻道討論很多但決策記錄很少 | 已決事項與討論事項混在一起     | 強制 decision log 欄位化           |
| 回退後暫時恢復但再次抖動       | rollback condition 不完整      | 補充次級門檻與觀察窗               |
| 通訊內容與內部判斷不一致       | evidence 版本不同步            | 以 decision log 為唯一對外事實來源 |
| write-back 列很多但無人關閉    | owner 與 review date 缺失      | 補責任人與 closure signal          |
| 同類事故重複發生               | 回寫只寫故事，沒進入上游控制面 | 把項目映射到 4.20/6.8/6.23         |

## 常見誤區

把 decision log 當成事後整理會失去事故價值。事故當下不記，事後只能用記憶補洞，容易產生 hindsight 偏差。

把 write-back 當成待辦清單也會失效。沒有 `closure signal` 的改善項目很快會退化成長期債務。

## 案例回寫

這條路徑可用 [Cloudflare 2023 Workers KV Deployment Tool Misconfiguration](/backend/08-incident-response/cases/cloudflare/2023-workers-kv-deployment-tool-misconfiguration/) 回寫。先看控制面變更如何擴散，再回到本章檢查決策欄位與回寫欄位是否能完整重放事故節奏。

這個案例主要支撐的是「控制面決策可回放」判讀，不直接支撐 provider dependency gate 門檻；放行策略回到 6.25/6.8。

## 跨模組路由

1. 與 8.19 的交接：欄位語言與 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 對齊。
2. 與 8.22 的交接：回寫欄位與 [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/) 對齊。
3. 與 6.24 的交接：控制面事故停損條件回到 [Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/)。
4. 與 4.20 的交接：證據來源統一到 observability evidence package。

## 下一步路由

要把控制面事故前移到資安治理，接著讀 [7.27 Credential Rotation with Scoped Evidence 實作示範](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)。
