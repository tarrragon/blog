---
title: "8.21 Incident Workflow Automation Boundary"
date: 2026-05-02
description: "定義哪些事故流程適合自動化，哪些決策需要保留人工確認"
weight: 21
---

## 大綱

- automation boundary 的責任：把可自動化的事故工作與需要人工判斷的決策分開
- 適合自動化：channel creation、role reminder、template update、status sync、evidence collection、ticket creation
- 需要人工確認：severity upgrade、customer impact statement、rollback execution、security disclosure、compensation
- guardrail：approval、dry run、rollback condition、audit log、rate limit
- 風險：自動化誤升級、誤通知、錯誤 rollback、過度信任 enrichment
- 跟 vendor / IR platform 的關係：工具支援流程，決策邊界仍需由團隊定義
- 跟 07 的交接：高風險自動化需要權限、稽核與安全例外治理
- 反模式：把所有 incident workflow 都交給 bot；bot 產生錯誤 status update；自動化沒有停止條件

Incident workflow automation boundary 的價值是把速度與責任同時保住。事故流程中有大量可標準化動作，適合自動化；但分級、回退、對外說法與資安披露仍需要情境判斷，必須保留人類決策責任。

## 概念定位

Incident workflow automation boundary 是事故流程自動化的決策邊界，責任是讓工具減少手動摩擦，同時保留高風險決策的人類確認。

這一頁處理的是自動化取捨。事故流程有大量可預期動作，但 severity、rollback、對外說法與資安披露都帶有情境判斷與責任風險。

邊界定義越清楚，工具越有價值。當團隊先定義好「可自動化動作」與「需人工確認動作」，bot 才能專注減少摩擦，而不會擴大決策風險。

## 核心判讀

判讀 automation boundary 時，先看動作是否可逆，再看錯誤自動化的影響範圍。

重點訊號包括：

- 自動化動作是否只建立容器、收集資料或提醒角色
- 高風險動作是否有 approval 與 audit log
- bot 產出的資訊是否標示 confidence 與來源
- workflow 是否有 stop condition 與 manual override
- 自動化是否支援 IC，並保留 IC 的決策責任

| 動作類型       | 自動化適配 | 安全護欄               |
| -------------- | ---------- | ---------------------- |
| 流程容器建立   | 高         | 頻道命名規範、角色模板 |
| 證據彙整與同步 | 高         | 來源標示、信心標示     |
| 分級與回退決策 | 低         | 人工核准、雙重確認     |
| 對外狀態更新   | 中         | 審核流程、回退機制     |
| 高風險操作觸發 | 低         | 權限隔離、audit log    |

## 判讀訊號

- bot 自動開 incident，但沒有人確認 severity
- status page 被 template 自動更新，內容與實際影響不一致
- rollback 被自動觸發後，團隊才發現資料 migration 還在進行
- enrichment 資料來源過期，但被當成事實使用
- 自動化成功率高，但事故期間沒有人知道如何停用

典型場景是 bot 能快速建立 incident channel、拉齊角色與初版模板，這些都能穩定節省時間；但若 bot 直接執行 rollback 或發布對外影響描述，錯誤成本會急遽上升。邊界的責任就是把這條線畫清楚。

## 交接路由

- 08.1 severity trigger：定義哪些升級可自動建議、哪些需人工確認
- 08.2 incident command roles：讓 bot 支援角色提醒與交接
- 08.4 incident communication：保護對外通訊的人類確認邊界
- 08.19 incident decision log：自動化動作也要留下決策紀錄
- 07.14 security exception / tripwire：高風險自動化接安全例外治理
- 05 deployment platform：rollback / rollout automation 的實作邊界
