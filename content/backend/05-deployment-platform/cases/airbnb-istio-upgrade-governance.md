---
title: "5.C7 Airbnb：Istio 升級治理"
date: 2026-05-07
description: "service mesh 升級在大規模環境下如何保持高可用。"
weight: 7
---

這個案例的核心責任是把平台元件升級從一次性作業轉成可重播流程。

## 觀察

Airbnb 在大量叢集與工作負載下持續升級 Istio，重點在升級節奏與可用性守護。

## 判讀

基礎平台元件升級若缺乏分批治理，會形成全域風險放大器。

## 策略

1. 用分批升級與回退窗口控制風險。
2. 將升級驗證標準固定化。
3. 把升級事件接入 incident command 節奏。

## 下一步路由

回 [5.2](/backend/05-deployment-platform/kubernetes-deployment/) 與 [8.6](/backend/08-incident-response/ic-handoff-long-incident/)。

## 引用源

- [Seamless Istio Upgrades at Scale](https://airbnb.tech/infrastructure/seamless-istio-upgrades-at-scale/)
