---
title: "11.C31 Dropbox Courier：百萬 RPS 規模的 gRPC 遷移"
date: 2026-07-03
description: "gRPC 當框架層集中可靠性的載體、遷移成本與 TLS 握手踩雷的規模判讀訊號"
weight: 31
tags: ["backend", "api-design", "case-study", "grpc"]
---

這個案例的核心責任是提供內部 RPC 選型的規模上限案例。

## 觀察

Dropbox 從 HTTP/1.1 加 protobuf 的自製 RPC 遷移到 gRPC、動機是保留既有 protobuf、取得 multiplexing 與雙向 streaming；在 gRPC 上疊了 mTLS 服務身分、per-method 統計、強制 deadline 傳播、LIFO queue 熔斷。踩雷紀錄：大規模重啟時 TLS 握手成本迫使 RSA 2048 換 ECDSA P-256、且 HTTP/1.1 與 gRPC 要拆成不同 server 處理。

## 判讀

gRPC 在 Dropbox 的價值是「框架層集中加 infra-wide 可靠性」的載體、不是序列化效能本身 — 選型判準應該看組織要不要這一層集中點。「migration 比初始開發久得多」與 TLS 握手踩雷適合當規模判讀訊號。

## 對應大綱

styles/grpc/「內部 RPC 的選型位置」（anchor）、11.2 風格選型（操作可及性軸、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Courier: Dropbox migration to gRPC（Dropbox tech blog）](https://dropbox.tech/infrastructure/courier-dropbox-migration-to-grpc)
