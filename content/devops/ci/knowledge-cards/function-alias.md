---
title: "Function Alias"
date: 2026-05-21
description: "說明 serverless function alias 如何把穩定入口指向特定版本並支援流量切換與回復"
tags: ["CD", "serverless", "function", "knowledge-card"]
weight: 25
aliases: ["/ci/knowledge-cards/function-alias/"]
---

Function Alias 的核心概念是「用穩定名稱指向不可變函式版本」。它讓 [Rollout Strategy](/devops/ci/knowledge-cards/rollout-strategy/) 可以套用在 serverless function 上，並讓 [Rollback Strategy](/devops/ci/knowledge-cards/rollback-strategy/) 具備快速切換入口。

## 跟其他概念的關係

Function Alias 位在 function version、traffic weight、[event source](/devops/ci/knowledge-cards/event-source/) 與 invocation entrypoint 之間，常見於 Lambda alias 或其他 serverless 平台的版本別名。

## 可觀察訊號

- 新舊 function version 需要短暫共存。
- 部分流量需要導向新版本做 canary。
- 事故時需要把入口切回上一個版本。

## 接近真實服務的例子

HTTP function 的 `prod` alias 先把 5% 流量導向 version 42。若錯誤率穩定，逐步提高權重；若錯誤率升高，alias 切回 version 41。

## 判斷條件與後果

Function Alias 讓回退只需要改一個指向，前提是呼叫方與 event source 都綁在 alias 上。event source 直接綁在某個 version 時，alias 切回 version 41，那條事件來源仍然觸發 version 42，回退只涵蓋了經由 alias 進來的流量。alias 用流量權重分出 canary 時，錯誤率沒有依版本分開觀測，就分辨不出錯誤來自新版還是舊版；回復條件（錯誤率到多少就切回）沒有事先寫下時，是否切回在事故當下才討論，入口停在壞版本上的時間跟著拉長。
