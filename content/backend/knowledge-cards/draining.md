---
title: "Draining"
date: 2026-04-24
description: "說明服務如何先停止接收新流量，再讓既有工作完成"
weight: 131
---

Draining 的核心概念是「先把新的 request 停掉，再讓已經進來的工作在期限內完成或交回」。它是負載切換與停止流程中的保護動作，常出現在 rolling update、縮容、故障切換與 graceful shutdown。

## 概念位置

Draining 位在 load balancer、deployment platform、application 與 in-flight work 之間。它介於流量入口與工作完成之間，目標是避免切換瞬間把正在處理的請求硬切掉。

## 可觀察訊號

系統需要 draining 的訊號是：

- instance 要下線或被替換
- 長連線或背景工作不能被直接中斷
- 切流時需要避免新請求進入舊實例

## 接近真實網路服務的例子

Kubernetes rolling update 前先讓 instance 進入 draining、load balancer 在切流前停止導入新連線、worker 停止接收新 job 但完成目前處理，都是 draining 的應用。

## 設計責任

設計時要定義何時開始 draining、draining 多久、超時後怎麼強制終止，以及如何觀察 in-flight request、consumer ack 與長連線狀態。Draining 的目的不是無限等待，而是把切換風險壓到可接受範圍。

## 英文術語對照
- Connection draining
- Traffic draining
