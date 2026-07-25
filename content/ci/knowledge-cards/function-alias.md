---
title: "Function Alias"
date: 2026-05-21
description: "說明 serverless function alias 如何把穩定入口指向特定版本並支援流量切換與回復"
tags: ["CD", "serverless", "function", "knowledge-card"]
weight: 25
---

Function Alias 的核心概念是「用穩定名稱指向不可變函式版本」。它讓 [Rollout Strategy](/ci/knowledge-cards/rollout-strategy/) 可以套用在 serverless function 上，並讓 [Rollback Strategy](/ci/knowledge-cards/rollback-strategy/) 具備快速切換入口。

## 概念位置

Function Alias 位在 function version、traffic weight、[event source](/ci/knowledge-cards/event-source/) 與 invocation entrypoint 之間，常見於 Lambda alias 或其他 serverless 平台的版本別名。

## 可觀察訊號

- 新舊 function version 需要短暫共存。
- 部分流量需要導向新版本做 canary。
- 事故時需要把入口切回上一個版本。

## 接近真實服務的例子

HTTP function 的 `prod` alias 先把 5% 流量導向 version 42。若錯誤率穩定，逐步提高權重；若錯誤率升高，alias 切回 version 41。

## 設計責任

Function Alias 要定義版本命名、流量權重、觀測指標、事件來源綁定與回復條件，讓函式發布具備可控入口。
