---
title: "3.C2 VMware Tanzu CloudHealth：Kafka 轉 Amazon MSK"
date: 2026-05-07
description: "自管 Kafka 遷移到託管平台時的治理重點。"
weight: 2
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是把 broker 遷移拆成平台責任、運維責任與資料責任三層。

## 觀察

CloudHealth 由自管 Kafka 遷移到 Amazon MSK，過程涵蓋 topic、存取控制、觀測與遷移執行節奏。

## 判讀

這類轉換的實際風險通常不在服務名稱，而在 ACL、topic policy、client 相容性與 cutover 節奏。

## 策略

1. 先建立新叢集治理基線（ACL、觀測、部署）。
2. 分批 topic 遷移並持續監測 lag/錯誤。
3. 把回退與流量切換條件寫成明確門檻。

## 下一步路由

回 [3.1 broker basics](/backend/03-message-queue/broker-basics/) 與 [6.8 release gate](/backend/06-reliability/release-gate/)。

## 引用源

- [VMware CloudHealth Kafka to MSK](https://aws.amazon.com/blogs/big-data/how-vmware-tanzu-cloudhealth-migrated-from-self-managed-kafka-to-amazon-msk/)
