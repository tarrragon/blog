---
title: "11.C38 Stripe 冪等設計哲學：retry 是 client-server 協作"
date: 2026-07-03
description: "三種失敗點的 replay 行為分析、client 端 backoff + jitter 責任；冪等只做 server 半邊會放大故障"
weight: 38
tags: ["backend", "api-design", "case-study", "idempotency"]
---

這個案例的核心責任是說明冪等是 client-server 的協作協議、server 端 replay 快取只解一半。

## 觀察

Stripe 用 `Idempotency-Key` header 讓 POST 取得 exactly-once 語意；文章拆三種失敗點（連線建立前、執行中、回應遺失）並說明各自的 replay 行為；client 端責任是 exponential backoff 加 jitter（Ruby SDK 內建）、避免 thundering herd。

## 判讀

冪等的教學重點是協作性：server 提供 replay 快取、client 不帶 backoff 的 retry 仍會把故障放大。三種失敗點的分類可直接對應 API 層冪等章的錯誤時序分析骨架。

## 對應大綱

11.8 API 層冪等設計（anchor）、11.9 對外流量語意（retry / backoff）交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Designing robust and predictable APIs with idempotency（Stripe blog）](https://stripe.com/blog/idempotency)
