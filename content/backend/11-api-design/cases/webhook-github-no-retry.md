---
title: "11.C61 GitHub webhooks：不自動重試的反向承諾"
date: 2026-07-04
description: "at-least-once 不是所有 vendor 都給：GitHub 明文只試一次、失敗靠 consumer 自建排程補投；逼你讀 vendor 明文而非假設"
weight: 61
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 webhook 承諾光譜另一端的反例：投遞保證不是預設。

## 觀察

GitHub webhooks 官方 docs 明文（文件中重述兩次）：「GitHub does not automatically redeliver failed webhook deliveries」。失敗條件：server down、或「takes longer than 10 seconds to respond」。補救靠手動 redeliver、或自寫排程查 REST API 找 `status` 非 `OK` 的投遞再重送。簽章：`X-Hub-Signature-256`、request body 的 HMAC hex digest、SHA-256、以 secret 為 key（legacy SHA-1 的 `X-Hub-Signature` 不建議）。去重/追溯 header：`X-GitHub-Delivery`（每次投遞的 GUID）、`X-GitHub-Event`、`X-GitHub-Hook-ID`。建立 webhook 時發 `ping` event 做設定確認。

## 判讀

GitHub 揭露的是承諾光譜的另一端 —— at-least-once 不是所有 vendor 都給。GitHub 只保證試一次、重試責任整包丟回 consumer（自建排程補投）。這打破「webhook 等於自動重試」的直覺、正好逼讀者去讀每個 vendor 的明文承諾、而非假設一個通用行為。`X-GitHub-Delivery` GUID 仍給 consumer 去重的鉤子 —— 即使沒自動重投、手動重投也會重複。

## 對應大綱

styles/realtime/「webhook 對外承諾」（投遞保證不是預設、要讀 vendor 明文的對照錨；簽章方案跨 vendor 差異）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Webhook events and payloads（GitHub 官方 docs）](https://docs.github.com/en/webhooks/webhook-events-and-payloads) — headers / ping / 簽章、一手 vendor 官方 docs。
- [Handling failed webhook deliveries（GitHub 官方 docs）](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries) — 不自動重試 / 10 秒 timeout、一手。

## 二手來源與狀態標注

「不自動重試」是 GitHub 目前政策、可能改；10 秒為其特定 timeout。
