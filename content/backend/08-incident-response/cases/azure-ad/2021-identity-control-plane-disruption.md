---
title: "Azure AD：2021 身分控制面中斷事件"
date: 2026-05-07
description: "身分服務失效時，如何評估跨產品影響與收斂優先序。"
weight: 41
---

這起案例的核心責任是處理身份控制面故障對下游產品的連鎖影響。身份系統事故通常擴散快、影響廣，分級與通訊需要提前對齊。

## 判讀訊號

| 訊號                    | 判讀重點           | 回寫章節                                                               |
| ----------------------- | ------------------ | ---------------------------------------------------------------------- |
| auth failure surge      | 影響是否跨產品擴散 | [8.1](/backend/08-incident-response/incident-severity-trigger/)        |
| token issuance lag      | 控制面是否壅塞     | [8.18](/backend/08-incident-response/incident-intake-evidence-triage/) |
| dependency blast radius | 下游受影響範圍     | [8.15](/backend/08-incident-response/vendor-dependency-incident/)      |

## 邊界判讀

這個案例的邊界是「身份控制面」對下游產品鏈的連鎖影響。主要風險是事件分級只看單一產品，忽略共用身份依賴的擴散速度。

## 下一步路由

先做影響分層，再同步外部通訊與回復節奏，並將判讀欄位回寫 [8.20](/backend/08-incident-response/customer-impact-assessment/) 與 [8.19](/backend/08-incident-response/incident-decision-log/)。
