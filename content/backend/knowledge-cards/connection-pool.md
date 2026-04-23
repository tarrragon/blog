---
title: "Connection Pool"
date: 2026-04-23
description: "說明連線池如何限制下游資源並影響服務容量"
weight: 17
---

Connection pool 的核心概念是「重用並限制到下游服務的連線」。資料庫、Redis、broker 與 HTTP client 都可能使用連線池；連線池決定同時有多少工作能進入下游。

## 概念位置

連線池是 application 並發與下游容量的閘門。Pool 太小會讓 request 等待；pool 太大會把壓力轉移到資料庫或外部服務，造成 timeout、排隊與資源耗盡。

## 可觀察訊號與例子

系統需要檢查 connection pool 的訊號是 latency 升高但 CPU 不高，或高峰時大量 request 等待資料庫。活動期間 checkout 變慢，可能是 database pool 已滿，也可能是資料庫本身查詢變慢。

## 設計責任

Pool 設定要搭配 timeout、查詢耗時、instance 數量與下游最大連線數。Runbook 應能看到 pool in-use、idle、wait count、timeout 與下游 error rate。
