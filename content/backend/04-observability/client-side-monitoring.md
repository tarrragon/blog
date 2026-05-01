---
title: "4.10 Client-side / Synthetic / RUM"
date: 2026-05-01
description: "補 server-side 看不到的 user perceived 訊號"
weight: 10
---

## 大綱

- 為何 server-side 觀測不夠：DNS、CDN、網路、瀏覽器、地區差異 server 看不到
- RUM（Real User Monitoring）：真實用戶端訊號、地理 / device / network 維度
- Synthetic monitoring：定點探測、SLO probe、第三方依賴監控
- Core Web Vitals 與 backend SLI 的對應關係
- 行動端與桌面端的訊號差異
- 跟 [4.6 SLI/SLO](/backend/04-observability/sli-slo-signal/) 的整合：user-journey-centric SLI 需要 client side metric
- vendor 取捨：Datadog RUM / Sentry / New Relic Browser / Catchpoint / Pingdom
- 反模式：SLO 只看 server 200 率、edge / CDN 故障 server 無感、synthetic probe 路徑跟真實用戶不同

## 判讀訊號

- 用戶在社群回報慢、server-side latency 看起來正常
- CDN / edge 故障時內部 dashboard 全綠
- 行動弱網場景無 visibility、僅有 wifi 桌面端訊號
- synthetic probe 從 datacenter 內部跑、不代表真實 ISP 路徑
- 客戶投訴定位耗時長、無 client 端 trace / RUM session

## 交接路由

- 04.6 SLI/SLO：user-journey-centric SLI 的訊號來源
- 05 部署：CDN / edge 配置變更影響 RUM 訊號
- 08.10 stakeholder 通訊：客戶感知影響量化
