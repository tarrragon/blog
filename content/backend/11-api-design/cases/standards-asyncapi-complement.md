---
title: "11.C53 AsyncAPI：刻意相容 OpenAPI 的補位策略"
date: 2026-07-03
description: "站在既有標準肩上補 event-driven 缺口：以相容性換採用曲線、描述格式的邊界即治理邊界"
weight: 53
tags: ["backend", "api-design", "case-study", "standards"]
---

這個案例的核心責任是記錄「補位式標準化」策略：不另起爐灶、以相容換採用。

## 觀察

官方文件自述 AsyncAPI 起於 OpenAPI specification 的 adaptation、刻意維持相容並重用 OpenAPI schema；結構差異為 Paths 對 Channels、HTTP verbs 對 Publish / Subscribe、加入 Correlation Id 與 protocol bindings 等 protocol-agnostic 概念；3.0 進一步把 operations 從 channels 拆離。補位論證：「systems don't have just REST APIs or events, but a mix of both」、支援跨同步 / 非同步的 schema 重用與多協議。

## 判讀

AsyncAPI 明確承認 OpenAPI 的生態位、只填 event-driven 空白 — 以相容性換採用曲線。教學意義：描述格式的邊界即治理邊界 — 組織同時有 REST 加 event 時、規範治理需要兩份 spec 格式但一套 schema 來源。

## 對應大綱

styles/standards/「OpenAPI 與 AsyncAPI 生態」（anchor）、03 訊息佇列模組交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Coming from OpenAPI（AsyncAPI docs）](https://www.asyncapi.com/docs/tutorials/getting-started/coming-from-openapi)
