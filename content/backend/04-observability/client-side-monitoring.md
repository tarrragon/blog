---
title: "4.10 Client-side / Synthetic / RUM"
date: 2026-06-22
description: "補 server-side 看不到的 user perceived 訊號"
weight: 10
tags: ["backend", "observability"]
---

## 大綱

- Server-side 觀測的盲區
- RUM（Real User Monitoring）：真實用戶端訊號
- Synthetic monitoring：主動探測
- Core Web Vitals 與 backend SLI 的整合
- Client trace 跟 server trace 的串接
- Vendor 定位
- 反模式

## 概念定位

Client-side、Synthetic 與 RUM 訊號是把使用者實際感知納入觀測系統的資料來源，責任是補上 server-side 指標看不到的網路、瀏覽器、地區與裝置差異。

服務端 200 率正常只代表 backend 有回應。使用者是否真的能完成操作，還要看 DNS 解析、CDN 快取、ISP 路由、瀏覽器渲染與 client-side JavaScript 執行。這些環節每一個都可能讓使用者的體驗跟 server-side dashboard 顯示的完全不同。

跟 [monitoring 模組](/monitoring/) 的分工：monitoring 模組聚焦「非 server 端 runtime 的監控體系」（SDK 設計、collector 架構、rule engine）；本章聚焦「backend 觀測系統如何整合 client-side 訊號」。交叉點是事件格式跟 transport。

## Server-side 觀測的盲區

Server-side 觀測能看到「request 到達 server 之後發生了什麼」，看不到「request 到達 server 之前」跟「response 離開 server 之後」的環節。

| 環節                 | Server 能看到嗎 | 影響                                 |
| -------------------- | --------------- | ------------------------------------ |
| DNS 解析             | 看不到          | DNS 異常讓使用者完全到不了 server    |
| CDN / edge 故障      | 看不到          | CDN 返回 stale 或 error、server 無感 |
| ISP 路由異常         | 看不到          | 特定地區使用者延遲暴增               |
| TLS handshake        | 部分看得到      | Certificate 問題讓部分 client 連不上 |
| Browser rendering    | 看不到          | TTFB 正常但 LCP / CLS 很差           |
| Client-side JS error | 看不到          | 功能壞了但 API call 正常             |
| 弱網 / offline       | 看不到          | Request timeout 或完全沒發出         |

這些盲區意味著 server-side 的「一切正常」跟使用者的「用不了」可以同時存在。

## RUM（Real User Monitoring）

RUM 在使用者的瀏覽器或 app 中嵌入監控 SDK，收集真實使用者的效能跟錯誤資料。跟 synthetic monitoring 的差異是 RUM 看的是真實流量，能反映真實的地理分布、裝置差異跟網路條件。

### 核心指標

**頁面效能**：First Contentful Paint（FCP）、Largest Contentful Paint（LCP）、Cumulative Layout Shift（CLS）、Interaction to Next Paint（INP）。這四個指標（Core Web Vitals 系列）是 Google 定義的使用者體驗量化標準。

**JS error**：未捕獲的 exception、promise rejection、resource loading failure。RUM SDK 自動攔截（`window.onerror`、`unhandledrejection`），帶 stack trace、browser info、page URL。

**API call 效能**：從 client 端量測的 API latency（包含 DNS + TCP + TLS + server processing + response download）。跟 server-side 量測的差異就是網路延遲跟 client 處理時間。

### 切分維度

RUM 資料的價值在於可以按維度切分：地區（哪個國家 / 城市慢）、裝置（mobile vs desktop、iOS vs Android）、網路型態（4G vs wifi vs 3G）、瀏覽器（Chrome vs Safari vs Firefox）。

切分後的資料能回答 server-side 回答不了的問題：「為什麼巴西的使用者比美國慢 3 倍？」（CDN 沒覆蓋巴西）、「為什麼 Safari 的 error rate 比 Chrome 高？」（某個 JS API 在 Safari 的行為不同）。

### 取樣與成本

RUM 的事件量跟使用者流量成正比。高流量網站的 RUM 資料量可能很大（每秒數千筆 page view + error + resource timing），成本隨之上升。

RUM 的取樣策略跟 server-side trace sampling 類似：可以全收（低流量網站）、按比例取樣（高流量）、或按條件取樣（error 全收、正常 page view 取樣）。取樣後的資料仍能看到趨勢跟 percentile，但個別 session 的完整 replay 需要該 session 被取樣到。

## Synthetic Monitoring

Synthetic monitoring 用自動化的 [probe](/backend/knowledge-cards/probe/) 從外部網路定期發起請求，測量 availability 跟 latency。跟 RUM 的差異是 synthetic 是主動探測（沒有真實使用者也能跑），能 24/7 持續監控。

### 適用場景

**Availability 探測**：每分鐘從多個地區對關鍵頁面或 API endpoint 發 request，確認可達性。DNS 異常、CDN 故障、TLS 過期 — 這些 server-side 看不到的問題，synthetic probe 能第一時間抓到。

**SLO probe**：用 synthetic probe 量測關鍵 user journey 的端到端 latency（login → homepage → checkout），作為 SLO 的 client-side 量測點。

**Third-party 依賴監控**：探測 payment gateway、SSO provider、CDN 的可用性。這些外部依賴故障時 server-side 只能看到 timeout 或 error code，synthetic probe 能從使用者的角度看到完整影響。

### 常見陷阱

Synthetic probe 的探測路徑必須跟真實使用者一致。Probe 從 datacenter 內部發 request、走內部 DNS、不經過 CDN — 這種 probe 量到的 latency 跟 availability 不代表真實使用者的體驗。

Probe 應該從外部網路、經過公開 DNS、經過 CDN / edge、用真實 browser（headless Chrome）渲染頁面。Catchpoint、Pingdom、Datadog Synthetic 都提供從多個公開地理位置發 probe 的能力。

## Core Web Vitals 與 Backend SLI 的整合

Core Web Vitals（LCP、CLS、INP）是 client-side 的使用者體驗指標。Backend SLI（availability、latency p99）是 server-side 的服務健康指標。兩者各自反映不同層面、需要整合看才能得到完整圖像。

整合方式是在 dashboard 上並排顯示：backend SLI panel 旁邊放 RUM 的 LCP / INP panel。當 backend latency 正常但 LCP 退化，問題在 frontend rendering 或 CDN；當 backend latency 升高且 LCP 同步退化，問題在 backend。

[4.6 SLI/SLO 設計](/backend/04-observability/sli-slo-signal/) 的 user-journey-centric SLI 應該同時考慮 server-side 跟 client-side 的量測點。只看 server-side 的 SLI 會低估使用者實際感知的延遲。

## Client Trace 跟 Server Trace 的串接

RUM SDK 跟 backend 的 trace 串接讓一個 user action 的完整路徑可追蹤 — 從 button click 到 browser 發 API request 到 backend 處理到 response rendering。

串接方式是 RUM SDK 在發起 API request 時注入 [trace context](/backend/knowledge-cards/trace-context/) header（W3C `traceparent`）。Backend 的 trace instrumentation 提取 header、建立 child span。完整的 trace waterfall 從 browser span 開始、經過 backend span、到 database span。

串接的條件是 RUM SDK 跟 backend SDK 使用相同的 trace context format。OTel 生態（browser SDK + backend SDK）天然支援；混用 vendor 時需要確認 header format 一致。

## Vendor 定位

| Vendor            | RUM | Synthetic | 特點                              |
| ----------------- | --- | --------- | --------------------------------- |
| Datadog RUM       | 有  | 有        | 跟 APM trace 整合、session replay |
| Sentry            | 有  | 無        | Error tracking 為主、效能次之     |
| New Relic Browser | 有  | 有        | 全棧觀測整合                      |
| Catchpoint        | 無  | 有        | Synthetic 專精、全球 probe 網路   |
| Pingdom           | 無  | 有        | 簡單 availability probe           |
| Grafana Faro      | 有  | 無        | 開源、Grafana 生態整合            |

選擇要點：已有 APM vendor 的團隊優先用同 vendor 的 RUM（trace 串接最自然）。只需要 availability probe 的用 Pingdom 或 Synthetic 功能。需要 session replay（重現使用者操作序列）的選 Datadog RUM 或 Sentry。

## 核心判讀

判讀 client-side monitoring 時，先看訊號是否代表真實使用者，再看 synthetic probe 是否覆蓋關鍵旅程。

重點訊號包括：

- RUM 是否能按地區、裝置、網路型態與瀏覽器切分
- Synthetic probe 是否從外部網路與真實入口進入
- Core Web Vitals 是否能和 backend SLI 並排比較
- Client trace / session 是否能和 server trace 串接

## 判讀訊號

- 使用者回報慢但 server-side latency 正常
- CDN / edge 故障時內部 dashboard 全綠
- 行動弱網場景無 visibility、僅有 wifi 桌面端訊號
- Synthetic probe 從 datacenter 內部跑、路徑跟真實使用者不同
- 客戶投訴定位耗時長、無 client 端 trace / RUM session

## 反模式

| 反模式                      | 表面現象                           | 修正方向                                |
| --------------------------- | ---------------------------------- | --------------------------------------- |
| SLO 只看 server 200 率      | CDN / DNS 故障時 SLO 一切正常      | 加 synthetic probe 跟 RUM 作為 SLI 來源 |
| Synthetic probe 走內部網路  | Probe latency 跟真實使用者差距大   | Probe 從外部公開網路、經 DNS / CDN 路徑 |
| RUM 無取樣策略              | 高流量時 RUM 成本失控              | 按條件取樣（error 全收、正常取樣）      |
| Client trace 跟 server 斷裂 | 看不到 browser → server 的完整路徑 | RUM SDK 注入 W3C trace context header   |
| 只看 overall LCP            | 全球平均看起來好但特定地區體驗極差 | 按地區 / 裝置 / 網路切分 RUM 資料       |

## 交接路由

- [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/)：user-journey-centric SLI 需要 client-side 量測點
- [4.3 tracing](/backend/04-observability/tracing-context/)：client trace 跟 server trace 的 context 串接
- [05 部署](/backend/05-deployment-platform/)：CDN / edge 配置變更影響 RUM 訊號
- [08 incident response](/backend/08-incident-response/)：客戶感知影響量化
- [Monitoring 模組](/monitoring/)：非 server 端的監控體系設計
- [4.24 Client-to-Server 觀測串接](/backend/04-observability/client-server-trace-integration/)：從 browser click 到 server span 的完整 trace 鏈路實作
