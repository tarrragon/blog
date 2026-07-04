---
title: "4.C19 Watchdog / dead man's switch：訊號消失即告警"
date: 2026-07-04
description: "永遠觸發的告警交給獨立失效域的外部偵測器、它消失才代表告警管線本身死了；搭配 blackbox 外部探測互補"
weight: 19
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供 out-of-band 存活訊號的典型做法：把「監控活著」變成一個持續心跳。

## 觀察

kube-prometheus 標配的 Watchdog alert 定義：「This is an alert meant to ensure that the entire alerting pipeline is functional. This alert is always firing」。runbook 說明：這個永遠 firing 的告警若停止觸發、代表告警管線本身斷了（alertmanager 錯配、認證失敗、連線問題）、由外部系統（如 PagerDuty Dead Man's Snitch）據此收到通知。互補的另一種 out-of-band 是外部主動探測：Prometheus blackbox exporter「allows blackbox probing of endpoints over HTTP, HTTPS, DNS, TCP, ICMP and gRPC」、從外部 vantage point 打 endpoint、資料來源與被測系統解耦。

## 判讀

正常監控是「壞了才告警」；Watchdog 反轉為「一直告警、消失才是壞」—— 因為監控系統自己死了時、它發不出「我死了」的告警、只能靠一個獨立失效域的外部偵測器判斷心跳消失。這跟 blackbox 的外部探測互補：一個是「內部心跳消失」、一個是「外部主動探測」、兩者的存活判斷都不依賴被測系統自己上報。設計含義：關鍵告警鏈要有一個活在生產棧之外的證人。

## 對應大綱

觀測共命運章「out-of-band 訊號」段（heartbeat 消失 + 外部探測）。

## 引用源

- [Watchdog alert runbook（prometheus-operator）](https://runbooks.prometheus-operator.dev/runbooks/general/watchdog/) — kube-prometheus stack 標配 rule 的權威說明。已 WebFetch 驗證。
- [blackbox_exporter（Prometheus 官方）](https://github.com/prometheus/blackbox_exporter) — 一手。已 WebFetch 驗證。

## 二手來源與狀態標注

Watchdog 是 kube-prometheus-stack 內建 rule、非 Prometheus core docs 條目；外部偵測端（Dead Man's Snitch / PagerDuty）屬 vendor、本卡只取「消失即告警」原則、不背書特定 vendor。blackbox exporter 若跟監控 infra 同域則失效域未必真獨立、要真 out-of-band 需部署在獨立失效域。
