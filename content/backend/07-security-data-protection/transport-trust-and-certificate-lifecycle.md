---
title: "7.5 傳輸信任與憑證生命週期"
date: 2026-04-24
description: "大綱稿：以問題驅動方式整理傳輸信任鏈、會話完整性與憑證節奏"
weight: 75
---

本章的責任是定義傳輸信任問題節點，讓跨邊界通訊先完成信任判讀，再進入實體配置。

## 本章寫作邊界

本章聚焦信任鏈治理、會話收斂、憑證生命周期與第三方傳導。案例在問題被觸發時提供佐證。

## 大綱（待填充）

1. 傳輸信任模型與邊界
2. 會話完整性與重放判讀
3. 憑證生命周期治理
4. 管理平面傳輸分層
5. 第三方信任鏈重評估
6. 交接路由到 05/06/08

## 問題節點（案例觸發式）

| 問題節點 | 判讀訊號 | 風險後果 | 前置控制面 | 交接路由 |
| --- | --- | --- | --- | --- |
| 會話收斂節奏落後 | 修補後異常 session 延續 | 事件關閉窗口延長 | [session-invalidation](../knowledge-cards/session-invalidation/)、[timeout](../knowledge-cards/timeout/) | `08 + 05` |
| 憑證輪替覆蓋不足 | 輪替完成率偏低、失效窗口過長 | 信任鏈可利用窗口維持 | [website-certificate-lifecycle](../knowledge-cards/website-certificate-lifecycle/)、[certificate-revocation](../knowledge-cards/certificate-revocation/) | `05 + 06` |
| 管理平面傳輸混層 | 管理流量與業務流量共用邊界 | 高權限邊界可被橫向利用 | [management-plane](../knowledge-cards/management-plane/)、[trust-boundary](../knowledge-cards/trust-boundary/) | `05 + 08` |
| 第三方信任重評估延遲 | 外部事件後內部憑證收斂滯後 | 傳導風險停留在生產路徑 | [token-revocation](../knowledge-cards/token-revocation/)、[incident-severity](../knowledge-cards/incident-severity/) | `08` |

## 下一步路由

- 連線與憑證配置：`05-deployment-platform`
- 輪替與驗證節奏：`06-reliability`
- 事件收斂流程：`08-incident-response`
