---
title: "Stripe：Canary Deploy 與 Progressive Rollout 治理"
date: 2026-06-23
description: "金流場景如何用交易指標驅動放行節奏：延遲確認、duplicate 偵測與自動回退。"
weight: 42
tags: ["backend", "reliability", "case-study"]
---

金流場景的 canary deploy 核心責任是讓每一批放量都能用交易指標判斷是否安全。progressive rollout 的節奏由交易成功率、duplicate charge 偵測與退款異常等金流特有指標驅動。本文從金流場景的通用壓力推導 progressive rollout 設計，以 Stripe 公開的 deploy 與 idempotency 實踐作為背景脈絡。

## 問題場景

金流變更的風險帶有延遲性。交易失敗可能在結帳時才被發現，退款申請可能在數天後才出現，對帳差異可能在日終結算才暴露。若 canary 只觀察幾分鐘的 error rate，延遲暴露的問題會在全量放行後才浮現。

這種延遲特性讓金流場景需要比一般功能更長的觀察窗與更多元的判讀指標。放行決策要等交易生命週期的關鍵階段都走過，才能確認變更安全。

## 決策機制

| 機制                        | 核心問題                              | 控制方式                                                       |
| --------------------------- | ------------------------------------- | -------------------------------------------------------------- |
| Canary traffic control      | 每批流量比例與觀察窗如何設定          | 1% → 5% → 25% → 100%，觀察窗依交易確認延遲調整                 |
| Transaction-specific checks | 交易指標是否涵蓋結帳到對帳的完整鏈路  | checkout success rate、capture rate、duplicate、refund anomaly |
| Automatic rollback trigger  | 交易異常時是否能即時回退              | 指標超門檻自動回退，不等人工判斷                               |
| Staged config vs code       | config 變更與 code 變更的風險是否相同 | timeout / retry 等 config 變更走獨立且更短的 rollout 節奏      |

Canary traffic 的觀察窗設計是這個機制的關鍵。1% 階段至少觀察到一個完整的交易確認週期（通常 30 分鐘到數小時），5% 階段需要覆蓋一個對帳週期，25% 階段需要確認退款率無異常。每批之間的 go/no-go 判斷依據是全部交易指標都在 baseline 範圍內，任一指標偏離即暫停擴批。

Config 變更（如 provider timeout 或 retry 次數）與 code 變更走不同 rollout 路線。config 變更影響面通常更可預測、回退更快（秒級生效），但風險在於小幅調整也可能放大 retry storm 或觸發 cascade timeout。

## 可觀測訊號

| 訊號                       | 判讀重點                      | 對應章節                                                       |
| -------------------------- | ----------------------------- | -------------------------------------------------------------- |
| checkout success rate      | canary 批次是否維持交易承諾   | [6.8](/backend/06-reliability/release-gate/)                   |
| canary vs baseline latency | 延遲偏移是否超過可接受範圍    | [6.13](/backend/06-reliability/performance-regression-gate/)   |
| payment duplicate rate     | 重試是否產生重複扣款          | [6.12](/backend/06-reliability/idempotency-replay/)            |
| rollback trigger count     | 自動回退是否頻繁觸發          | [6.23](/backend/06-reliability/verification-evidence-handoff/) |
| refund anomaly rate        | 退款比率是否偏離歷史 baseline | [8.19](/backend/08-incident-response/incident-decision-log/)   |

## 常見陷阱

把金流 canary 跟一般 feature rollout 用同一套觀察窗，會漏掉延遲暴露的問題。金流的 feedback loop 從結帳到退款可能跨越數天，短窗觀察拿到的 pass 訊號只代表即時指標正常，無法涵蓋對帳與退款階段的風險。

另一個常見問題是 config 變更被視為低風險而跳過 canary。timeout 或 retry 設定的微幅調整看似無害，但在高流量下可能觸發 retry storm 或改變 provider 端的行為，影響幅度可能大於 code 變更。

## 下一步路由

先回到 [6.8 Release Gate](/backend/06-reliability/release-gate/) 定義金流場景的放行政策，再到 [6.17 Feature Flag Governance](/backend/06-reliability/feature-flag-governance/) 設計 progressive rollout 的 flag lifecycle。實作示範見 [6.25 Provider Dependency Release Gate](/backend/06-reliability/provider-dependency-release-gate/)。

## 引用源

- [Designing robust and predictable APIs with idempotency](https://stripe.com/blog/idempotency)：idempotency key 設計，支撐 canary 回退後的重試安全
- [How Stripe's document databases supported 99.999% uptime with zero-downtime data migrations](https://stripe.com/blog/how-stripes-document-databases-supported-99.999-uptime-with-zero-downtime-data-migrations)：zero-downtime migration 的 staged rollout 思路

本文的 progressive rollout 機制（觀察窗設計、交易指標門檻、自動回退）從金流場景的通用壓力推導，並非 Stripe 公開的具體 deploy pipeline 描述。
