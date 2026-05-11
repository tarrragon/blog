---
title: "Microsoft：變更治理與可靠性門檻"
date: 2026-05-07
description: "透過分層變更管理與發布閘門，降低大型 SaaS 平台的系統性回歸風險。"
weight: 51
tags: ["backend", "reliability", "case-study"]
---

Microsoft 案例的核心責任是把變更管理制度化。對大型 SaaS 而言，事故常由多個低風險變更疊加而成，治理重點在於發布節奏與風險分層。

## 問題場景

高頻變更環境中，單一變更看起來都可接受，但累積後會突破可靠性預算。若缺少一致 gate，團隊難以提早收斂。

## 決策機制

| 機制     | 核心問題           | 交付結果 |
| -------- | ------------------ | -------- |
| 變更分層 | 哪些變更需要高門檻 | 風險分級 |
| 漸進發布 | 何時擴大、何時停止 | 放行節奏 |
| 復盤回寫 | 事故教訓如何制度化 | 持續改善 |

## 可觀測訊號

| 訊號                       | 判讀重點         | 對應章節                                                      |
| -------------------------- | ---------------- | ------------------------------------------------------------- |
| release rollback frequency | 變更品質是否退化 | [6.8](/backend/06-reliability/release-gate/)                  |
| freeze trigger count       | 凍結是否過晚     | [6.6](/backend/06-reliability/slo-error-budget/)              |
| incident recurrence        | 同型事件是否重複 | [8.13](/backend/08-incident-response/repeated-incident-toil/) |

## 下一步路由

把風險分層寫進 [6.19](/backend/06-reliability/reliability-readiness-review/)，並將復盤項目回寫 [6.21](/backend/06-reliability/reliability-debt-backlog/)。
