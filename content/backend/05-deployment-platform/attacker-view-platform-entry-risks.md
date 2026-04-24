---
title: "5.5 攻擊者視角（紅隊）：平台與入口弱點判讀"
date: 2026-04-24
description: "從隱藏入口、設定漂移與切換風險，盤點 deployment platform 的主要弱點"
weight: 5
---

平台與入口的攻擊者視角（紅隊）判讀目標是確認「服務怎麼被看見、怎麼被接流量、失效時怎麼擴散」。部署平台同時承擔可用性與安全邊界，弱點常出現在交付流程與設定面，而不是單一業務邏輯。

## 【情境】哪些交付路徑要先做弱點盤點

下列情境出現時，平台層弱點通常優先級較高：

- 多環境、多區域、頻繁發版
- 入口層同時含 public API、管理介面與 webhook
- 自動擴容與滾動更新已上線
- 組態與密鑰透過多來源下發

## 【判讀流程】平台與入口檢查順序

1. 看入口面：檢查 [load balancer](../knowledge-cards/load-balancer/)、[service discovery](../knowledge-cards/service-discovery/) 與 [internal endpoint](../knowledge-cards/internal-endpoint/) 暴露範圍。
2. 看生命週期：檢查 [readiness](../knowledge-cards/readiness/)、[health check](../knowledge-cards/health-check/)、[draining](../knowledge-cards/draining/) 與 [graceful shutdown](../knowledge-cards/graceful-shutdown/) 合約是否一致。
3. 看設定面：檢查 [runtime config](../knowledge-cards/runtime-config/)、[feature flag](../knowledge-cards/feature-flag/) 與 [secret management](../knowledge-cards/secret-management/) 是否有漂移與過寬權限。
4. 看交付面：檢查 [rolling update](../knowledge-cards/rolling-update/)、回滾條件與 [release gate](../knowledge-cards/release-gate/) 是否能阻擋高風險變更。

## 【風險代價】平台弱點會跨服務擴散

平台層錯誤常直接影響整批服務。readiness 與流量切換不一致會造成短時間大面積失敗；設定漂移會讓同版本行為不一致；隱藏入口暴露會把單點防護缺口擴大成系統風險。這類問題通常需要跨團隊協作，修復成本高且時間長。

## 【設計取捨】交付速度與邊界治理

交付速度越快，平台保護機制越需要前移。過度精簡審查可換到短期效率，但會提升高風險設定直接進入生產的機率。穩定做法是保留最小必要 gate，把高風險檢查自動化，減少人工判斷負擔。

## 【最低控制面】進入實作前要先定義

- 入口暴露清單與責任人
- 生命週期訊號合約與驗證規則
- 設定變更審查與漂移告警
- 發版、回滾、切換的停損條件
