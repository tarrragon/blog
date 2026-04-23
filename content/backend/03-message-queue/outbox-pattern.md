---
title: "3.3 outbox pattern 與發佈一致性"
date: 2026-04-23
description: "把 transaction 與 event publish 分離"
weight: 3
---

這一章處理 transaction 與訊息發佈之間的一致性問題，後續可以再延伸到 polling、relay 與 failure recovery。

## 大綱

- transaction outbox 的基本流程
- relay worker
- publish 成功與失敗補償
- duplicate publish 的處理方式
