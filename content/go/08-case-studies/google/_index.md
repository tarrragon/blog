---
title: "8.1 Google：大規模微服務與索引服務"
date: 2026-04-23
description: "看 Go 如何支撐 Google 的大規模微服務與資料索引"
weight: 1
---

Google 的官方案例最適合用來理解 Go 的原始定位：這門語言不是為了漂亮語法，而是為了解決大型工程團隊在多核心、網路、模組化與依賴管理上的問題。Google Core Data Solutions 團隊把原本的單體 C++ 索引堆疊拆成多個微服務，並把多數索引服務改寫成 Go。

## 你應該看什麼

- [Using Go at Google](https://go.dev/solutions/google/)
- [How Google’s Core Data Solutions Team Uses Go](https://go.dev/solutions/google/coredata)
- [Go at Google: Language Design in the Service of Software Engineering](https://go.dev/talks/2012/splash.article)

## 這個案例告訴我們什麼

1. Go 很適合大型服務拆分之後的邊界管理。
2. built-in concurrency 對高併發索引與資料處理很重要。
3. Go 的簡單語法與明確依賴，能讓大團隊維持可讀性。

## 可對照的公開原始碼

- [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)

Kubernetes 不是 Google 內部產品，但它很好地呈現了 Google 文化裡常見的 Go 工程模式：大型 codebase、明確 package 邊界、cmd 入口與大量服務協調。

