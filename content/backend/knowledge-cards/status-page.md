---
title: "Status Page"
tags: ["狀態頁", "Status Page"]
date: 2026-05-02
description: "說明事故期間對外狀態頁如何承接可用性承諾"
weight: 313
---


Status page 的核心概念是「把事故影響、處理節奏與回復進度公開成單一對外契約」。它和 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/) 與 [incident severity](/backend/knowledge-cards/incident-severity/) 一起決定外部看到的真實版本。

## 概念位置

Status page 位在 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/)、[stakeholder mapping](/backend/knowledge-cards/stakeholder-mapping/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。它把內部節奏轉成客戶可讀的更新，並把 ETA、影響範圍與下一次更新時間固定下來。

## 可觀察訊號與例子

系統需要 status page 的訊號是事故已經影響外部使用者，但內部的戰情室節奏還不能直接交給客戶。常見例子包括區域性 outage、身份平台失效、外部供應商中斷與多租戶服務退化。

## 設計責任

Status page 要定義更新頻率、發佈責任、嚴重度標示、影響範圍與下一次更新承諾。它不是公關模板，而是外部信任的最小承諾面。
