---
title: "Datadog：2023 多區觀測中斷事件"
date: 2026-05-07
description: "監控平台自身退化時，如何避免客戶誤判系統健康狀態。"
weight: 21
---

這起案例的核心責任是處理「監控系統本身失效」的盲區。當觀測平台中斷，事故判讀需要立即切換備援證據來源。

## 判讀訊號

| 訊號                        | 判讀重點               | 回寫章節                                                               |
| --------------------------- | ---------------------- | ---------------------------------------------------------------------- |
| telemetry gap               | 缺失是否影響決策       | [8.18](/backend/08-incident-response/incident-intake-evidence-triage/) |
| customer-side false normal  | 客戶是否誤以為服務正常 | [8.10](/backend/08-incident-response/stakeholder-communication/)       |
| fallback evidence readiness | 備援證據能否即時接手   | [4.20](/backend/04-observability/observability-evidence-package/)      |

## 邊界判讀

這個案例的邊界是「觀測資料缺失時的事故判讀」。主要風險是把缺失資料誤判為服務恢復，導致決策建立在錯誤安全感上。

## 下一步路由

事故流程要預留「觀測失明」分支，並在復盤回寫 [8.22](/backend/08-incident-response/incident-evidence-write-back/)。同時補 [4.20](/backend/04-observability/observability-evidence-package/) 的備援證據來源。
