---
title: "GoReplay"
date: 2026-05-15
description: "用 production HTTP traffic capture 與 replay 驗證真實請求形狀的效能工程工具"
weight: 20
tags: ["backend", "performance", "capacity", "vendor", "goreplay", "traffic-replay"]
---

GoReplay 的核心責任是捕捉 production HTTP traffic，並把真實請求形狀重播到 staging、shadow environment 或新版本。它適合驗證 synthetic load 難以建模的 endpoint mix、header、payload size、burst pattern 與 long-tail 行為，重點在把 production reality 轉成可控 replay artifact。

## 定位

GoReplay 適合在 synthetic workload 可信度偏低時使用。當 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 很難準確描述使用者路徑、payload 分布或 endpoint mix，GoReplay 可以從 production traffic 擷取真實樣本，再用 rate limit、filter、rewrite 與 output target 控制重播範圍。

這個定位讓 GoReplay 接到 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 的 shadow traffic。它的價值在於保留 production 請求形狀；它的風險在於 PII、credential、side effect、下游容量與 capture host overhead 都要被治理。

## 適用場景

架構遷移驗證適合 GoReplay。DB、cache、search、API gateway 或 framework 重寫時，可以把真實 HTTP traffic replay 到新路徑，觀察 latency、error、resource saturation 與 response diff。

Long-tail workload 校正適合 GoReplay。Synthetic scenario 通常覆蓋主路徑，GoReplay 可以揭露少見 endpoint、特殊 header、巨大 payload、冷門 tenant 與尖峰 cohort。

事故後修補驗證適合 GoReplay。若事故由特定請求形狀觸發，capture sample 可以在修補環境重播，確認 latency、error 或 resource usage 是否回到可接受範圍。

## 選型判準

| 判準             | GoReplay 的價值                                   | 需要補的能力                      |
| ---------------- | ------------------------------------------------- | --------------------------------- |
| 真實 traffic     | endpoint mix、payload、header 分布接近 production | PII / credential 遮罩與權限治理   |
| HTTP replay      | 對 HTTP API 路徑直接有效                          | 非 HTTP protocol 與加密流量處理   |
| Filter / rewrite | 可控制 host、path、header、rate                   | side effect 隔離與 sandbox target |
| Capture artifact | 可保存樣本做回歸驗證                              | retention、存取控制與樣本代表性   |

真實 traffic 價值來自分布保真。它能捕捉 synthetic script 容易漏掉的 query parameter、header、payload size 與 endpoint mix，但 capture sample 也會帶入 production 資料治理責任。

Filter / rewrite 價值來自安全邊界。Replay 前要改寫 target、移除 credential、遮罩 PII、限制 rate，並把寫入類請求導到 sandbox 或 dry-run path。

## 跟其他方式的取捨

GoReplay 和 k6 / Gatling / Locust 的主要差異是流量來源。GoReplay 取 production sample，保真度高；scripted load test 取人工模型，可控性高。

GoReplay 和 service mesh mirroring 的主要差異是部署位置。GoReplay 在 host / network capture 層工作，適合沒有 mesh 的服務；service mesh mirroring 在 sidecar / proxy 層工作，適合已經落地 mesh 的平台。

GoReplay 和 AWS VPC Traffic Mirroring 的主要差異是應用語意。GoReplay 對 HTTP replay 更直接；VPC Traffic Mirroring 在網路層複製封包，侵入性低但應用層 rewrite、遮罩與 replay 控制需要額外處理。

## 操作成本

GoReplay 的主要成本是資料安全。Production request 可能包含 token、cookie、PII、payment payload、internal IDs 與 tenant 資料，capture、保存、重播與刪除都要有明確 owner。

Replay 成本來自下游副作用。POST、PUT、DELETE、webhook、email、payment、notification 與 queue publish 都要導到 sandbox、mock 或 idempotent dry-run，避免 replay 造成重複交易或通知。

Capture 成本來自主機資源。高流量服務上的 capture agent 會消耗 CPU、network 與 disk，正式啟用前要先量測 overhead，並設定 sampling、rate limit 與 stop condition。

## Evidence Package

GoReplay 結果應回寫到 evidence package。最小欄位包括 capture source、capture time range、filter / rewrite rule、sample size、replay rate、target environment、data masking status、p95 / p99、error rate、resource saturation、known gap 與 owner。

| 欄位         | GoReplay 證據來源                            |
| ------------ | -------------------------------------------- |
| Source       | capture command、sample hash、replay command |
| Time range   | capture start / end、replay start / end      |
| Query link   | APM / metrics / logs / diff 查詢連結         |
| Data quality | sample representativeness、masking status    |
| Confidence   | replay rate、target parity、capture coverage |
| Known gap    | 未捕捉 protocol、資料遮罩限制、sandbox 差異  |

Evidence package 的核心用途是讓 replay 結論可審查。Reviewer 要能知道樣本來自哪段 production、經過哪些 filter、打到哪個 target，以及哪些 side effect 被 mock 或隔離。

## 案例回寫

GoReplay 適合回寫 migration 與 production validation 案例。它可接 [Tixcraft 售票壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的 production-shaped load、[SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 cutover 前 replay，以及 [Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 這類資料庫整併前的 query pattern 驗證。

這些案例的重點是 production request shape。GoReplay 頁引用案例時，要把 case 轉成 capture window、filter、rewrite、target isolation、rate limit 與 diff / saturation metric。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 平行：[Service Mesh Mirroring](/backend/09-performance-capacity/vendors/service-mesh-mirroring/)
- 平行：[AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)
- 知識卡：[Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- 官方：[GoReplay documentation](https://docs.goreplay.org/)
