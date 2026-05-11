---
title: "3.C7 LinkedIn：Kafka 自動修復治理"
date: 2026-05-07
description: "Kafka 維運從人工處置轉向自動修復的案例。"
weight: 7
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是把 queue 可靠性從人力值班轉成自動化機制。

## 觀察

LinkedIn 在 Kafka 維運中導入自動化治理，降低人工介入與恢復時間波動。

## 判讀

當叢集規模超過人力可及範圍，自動修復與治理工具會成為必要能力。

## 策略

1. 明確定義可自動修復的故障類型。
2. 將自動修復與人工升級條件分離。
3. 把修復過程納入可觀測證據鏈。

## 下一步路由

回 [3.2](/backend/03-message-queue/durable-queue/) 與 [8.16](/backend/08-incident-response/runbook-lifecycle/)。

## 引用源

- [Automating Kafka Self-Healing at LinkedIn](https://engineering.linkedin.com/blog)
