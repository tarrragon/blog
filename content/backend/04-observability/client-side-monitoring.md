---
title: "4.10 Client-side / Synthetic / RUM"
date: 2026-05-01
description: "補 server-side 看不到的 user perceived 訊號"
weight: 10
---

## 大綱

- 為何 server-side 觀測不夠：DNS、CDN、網路、瀏覽器、地區差異 server 看不到
- RUM（Real User Monitoring）：真實用戶端訊號、地理 / device / network 維度
- Synthetic monitoring：定點 [probe](/backend/knowledge-cards/probe/)、SLO probe、第三方依賴監控
- Core Web Vitals 與 backend SLI 的對應關係
- 行動端與桌面端的訊號差異
- 跟 [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/) 的整合：user-journey-centric SLI 需要 client side metric
- vendor 取捨：Datadog RUM / Sentry / New Relic Browser / Catchpoint / Pingdom
- 反模式：SLO 只看 server 200 率、edge / CDN 故障 server 無感、synthetic probe 路徑跟真實用戶不同

## 概念定位

Client-side、Synthetic 與 RUM 訊號是把使用者實際感知納入觀測系統的資料來源，責任是補上 server-side 指標看不到的網路、瀏覽器、地區與裝置差異。

這一頁處理的是 user perceived 訊號。服務端 200 率正常，只代表 backend 有回應；使用者是否真的能完成操作，還要看 DNS、CDN、edge、ISP、browser 與 client runtime。

## 核心判讀

判讀 client-side monitoring 時，先看訊號是否代表真實使用者，再看 synthetic probe 是否覆蓋關鍵旅程。

重點訊號包括：

- RUM 是否能按地區、裝置、網路型態與瀏覽器切分
- synthetic probe 是否從外部網路與真實入口進入
- Core Web Vitals 是否能和 backend SLI 對應
- client trace / session 是否能和 server trace 串接

## 判讀訊號

- 用戶在社群回報慢、server-side latency 看起來正常
- CDN / edge 故障時內部 dashboard 全綠
- 行動弱網場景無 visibility、僅有 wifi 桌面端訊號
- synthetic probe 從 datacenter 內部跑、不代表真實 ISP 路徑
- 客戶投訴定位耗時長、無 client 端 trace / RUM session

## 交接路由

- 04.6 SLI/SLO：user-journey-centric SLI 的訊號來源
- 05 部署：CDN / edge 配置變更影響 RUM 訊號
- 08.10 [stakeholder](/backend/knowledge-cards/stakeholder-mapping/) 通訊：客戶感知影響量化
