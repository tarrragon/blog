---
title: "Probe"
tags: ["探針", "Probe"]
date: 2026-04-23
description: "說明平台如何透過 probe 判斷服務狀態與接流量條件"
weight: 131
---

Probe 的核心概念是「平台主動探測服務狀態的訊號」。它常見於 readiness probe 與 liveness probe，也可能擴展到 startup probe。 可先對照 [Producer](/backend/knowledge-cards/producer/)。

## 跟其他概念的關係

Probe 位在 platform 與 application 之間，讓調度系統知道 instance 是否可接流量、是否仍存活，或是否仍在啟動中。 可先對照 [Producer](/backend/knowledge-cards/producer/)。

## 可觀察訊號

系統需要 probe 的訊號是啟動、擴容、故障、健康檢查與回收流程需要自動化判斷。沒有 probe，平台只能用硬編碼規則猜測服務狀態。

## 接近真實網路服務的例子

Kubernetes 會用 probe 決定 instance 是否加入流量池。Readiness probe 檢查能否接流量；liveness probe 檢查 process 是否卡死；startup probe 則可保護啟動較慢的服務。

## 判斷條件與後果

平台直接拿 probe 的結果決定 instance 是否接流量、是否重啟，所以 probe 的結果只該反映它自己負責的狀態。Probe 做了昂貴查詢或深度業務判斷時，probe 本身會因為負載升高或下游變慢而逾時，平台把仍然能服務的 instance 移出流量池或重啟它；檢查的內容涵蓋共用的下游時，下游一故障，所有 instance 的 probe 同時失敗，一個依賴的故障變成整個服務沒有 instance 接流量。簡單、快速、只檢查自身狀態的 probe，失敗時才代表這個 instance 本身無法接流量或已經卡死。
