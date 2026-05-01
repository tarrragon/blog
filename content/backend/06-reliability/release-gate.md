---
title: "6.8 Release Gate 與變更節奏"
date: 2026-05-01
description: "把驗證、migration、相容性納入放行判準"
weight: 8
---

## 大綱

- release gate 的核心責任：把放行決策從個人判斷變成可驗證條件
- gate 類別：CI 通過、SLO 健康、error budget 餘額、migration 可逆、相容性檢查
- 變更節奏：deploy frequency、batch size、change failure rate（DORA 四指標）
- freeze 條件：error budget 耗盡、事故進行中、高風險時段
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的耦合：error budget 是 gate 的一個條件
- 跟 [05 部署](/backend/05-deployment-platform/) 的交接：gate 通過後 rollout 策略接手
- 反模式：gate 流於形式、freeze 無 owner、緊急修復繞過 gate 變常態

## 判讀訊號

- gate 只看 CI green、不看 SLO / error budget / migration 可逆性
- emergency bypass 從例外變週常
- freeze 條件無 owner、沒人知道誰能解凍
- change failure rate 沒量、無法評估 gate 是否有效
- migration 沒做向後相容檢查、rollback 後資料不一致

## 交接路由

- 05 部署：canary / progressive delivery 實作
- 06.6 SLO：error budget 餘額查詢
- 06.10 contract testing：契約通過作為放行條件
- 06.11 migration safety：可逆性檢查
- 06.13 perf regression gate：退化作為 freeze 條件
- 07 資安：高風險變更的權限約束
- 08 事故閉環：事故進行中 freeze 觸發
- 06.17 feature flag：rollout 的細粒度控制層
- 06.18 reliability metrics：CFR 是 gate 健康度
