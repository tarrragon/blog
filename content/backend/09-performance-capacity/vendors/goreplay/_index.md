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

跟 [k6](/backend/09-performance-capacity/vendors/k6/) / [JMeter](/backend/09-performance-capacity/vendors/jmeter/) 的 synthetic load 設計 mindset 完全不同。Scripted load 假設 *測試者能描述使用者行為* — 寫 script、設 rate、跑 scenario；GoReplay 假設 *production 才是 source of truth* — endpoint mix、header 分布、payload size、burst pattern 都從真實 traffic 抽樣、不靠人為建模。對 long-tail 行為（少見 endpoint、巨大 payload、特殊 header 組合）這個差異決定了 capacity 規劃的真實度。

## 最短判讀路徑

判斷 GoReplay deployment 是否健康、最少看四件事：

- **Capture mode**：用 `raw` (libpcap-based)、`pcap-file`（離線 replay 已存檔的 pcap）、`file`（GoReplay 原生 gor format）哪一種？raw 對 production host 有 CPU / network overhead、pcap-file 適合事後 replay、file 適合 long-running capture buffer
- **Replay target**：打到 staging full-stack、shadow service、還是 isolated sandbox？POST / PUT / DELETE 是否導到 dry-run path 或 idempotent mock？webhook / payment / notification 是否被攔截？
- **Rate adjustment**：用原始 production rate replay，還是 2x / 10x / 0.1x？capacity 規劃通常需要 *speed up* 來測未來流量、debug 通常需要 *slow down* 跟單一請求追查
- **Middleware filter**：PII / token / cookie / credential redaction 在哪一段做（capture 前、capture 後、replay 前）？是否走 GoReplay middleware binary（stdin / stdout pipeline）統一處理

## 適用場景

架構遷移驗證適合 GoReplay。DB、cache、search、API gateway 或 framework 重寫時，可以把真實 HTTP traffic replay 到新路徑，觀察 latency、error、resource saturation 與 response diff。

Long-tail workload 校正適合 GoReplay。Synthetic scenario 通常覆蓋主路徑，GoReplay 可以揭露少見 endpoint、特殊 header、巨大 payload、冷門 tenant 與尖峰 [cohort](/backend/knowledge-cards/cohort/)。

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

### 核心取捨表

| 取捨維度       | GoReplay                                       | k6 / JMeter (synthetic)                | AWS VPC Traffic Mirroring         | Service Mesh Mirroring         |
| -------------- | ---------------------------------------------- | -------------------------------------- | --------------------------------- | ------------------------------ |
| 流量來源       | Production sniff（real shape）                 | Scripted scenario（builder's model）   | VPC 網路層封包複製                | Sidecar / proxy 層複製         |
| 工作層級       | HTTP / L7（capture host）                      | HTTP / L7（client-side script）        | L3-L4（packet level）             | L7（sidecar in-mesh）          |
| Rate adjust    | 原生支援（0.1x - 10x）                         | scenario 內 ramp / arrival rate        | 全量、無 rate control             | mesh policy 控制               |
| Replay 控制    | filter / rewrite / middleware binary           | 程式內 logic 完整可控                  | 需自寫 application-level rewriter | mesh-level routing rule        |
| Long-tail 覆蓋 | 強（real distribution）                        | 弱（取決於 scenario design）           | 強（real distribution）但需後處理 | 強（in-mesh real traffic）     |
| PII / 安全成本 | 高（middleware 自己寫 redaction）              | 低（fixture 由人控制）                 | 高（packet-level 難語意化遮罩）   | 中（mesh policy 可協助）       |
| 部署條件       | host agent + libpcap，需有權限 sniff interface | 無（client / load generator 機台即可） | AWS-only、ENI mirroring 配額      | 已落地 mesh（Istio / Linkerd） |

選 GoReplay 的核心訴求：*HTTP 應用層 replay + production shape 保真 + 沒落地 mesh*；若已用 mesh、優先看 mesh 內建 mirroring；若要跨 protocol（gRPC / 自家 binary）GoReplay 開源版受限、需考慮 Pro 版或 mesh 方案。

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

## 進階主題

**Capture to file（pcap-like artifact）**：用 `--output-file` 把 capture 寫成 GoReplay 原生 gor file（或讀 pcap）、之後用 `--input-file` 重複 replay。這個模式讓 *capture window* 跟 *replay run* 解耦 — capture 一次，可在不同 staging branch / 不同 rate / 不同 target 重播多次。對 regression 驗證跟「事故當時的 traffic shape」回放特別關鍵、但 file artifact 也成為 PII 儲存物、retention 跟存取控制要跟 production log 同級。

**Replay with rate adjustment（10x speed）**：`--input-file-replay-speed 10`（gor format）或加 `--input-file-loop` 反覆播放。10x speed 對 capacity headroom 驗證直接有用 — 用真實 traffic shape 模擬「未來流量翻 10 倍」、避開 scripted scenario 自帶的人為偏差。反向用法 0.1x 跟 isolated request replay 適合排錯特定 endpoint 的 long-tail latency。注意 10x 會把下游 DB / cache / external API 同樣放大，sandbox target 容量要先評估。

**Middleware filter（PII redaction）**：GoReplay middleware 是獨立 binary、用 stdin / stdout 跟 GoReplay process 串接、可寫任何語言。典型責任：JSON body 解析、Authorization / Cookie / Set-Cookie header strip、Email / phone / card number regex 遮罩、cross-request session ID rewriting（讓 staging 不撞 production session）。middleware 邏輯本身需要 code review、寫進版控、staging 測過再放到 production capture host。

**Pro version（GoReplay Pro - binary protocols）**：開源版聚焦 HTTP/1.x；GoReplay Pro 支援 binary protocol（自家 protocol、protobuf-over-TCP、部分 gRPC pattern）跟 enterprise 維護 SLA。判斷點：若服務是純 HTTP REST 開源版夠用、若有 gRPC 或自家 binary 且不在 mesh 內、要評估 Pro 或改走 service mesh mirroring。

## 排錯與失敗快速判讀

- **Capture loss / sample 不完整**：libpcap 在高流量下會 drop packet、`gor stat` 的 capture stats 顯示 drop > 1% 就不可信 — 加 capture host CPU、改用 PF_RING / AF_PACKET、或縮 capture filter 範圍（只 capture target port + sampling）
- **TCP reassembly 失敗 / replay 結果亂碼**：跨 packet 的 HTTP body 沒被正確組裝、常見於 MTU / TCP segment offload 設定異常 — 確認 capture interface 沒開 TSO / GRO、或用 application-level capture（HEC-style sidecar）取代 packet capture
- **PII / secret 漏 redact 進 staging**：middleware 規則沒覆蓋新加的 header / 新的 body schema — 建立 redaction allowlist（只放行已知 schema）而非 denylist、每次 schema 變更同步更新 middleware、staging 入口加 secret scanner 做 last-mile 攔截
- **Replay 觸發下游真實副作用**：POST / PUT 沒導 sandbox、webhook 真的打出去、payment 真的扣款 — replay target 預設 *deny all write*、白名單放行特定 idempotent endpoint、其餘走 mock 或 dry-run flag
- **Replay rate 拖垮 capture host**：同機 capture + replay、CPU / NIC 互相搶 — capture host 只負責 sniff + write to file、replay 機器獨立、用 gor file 解耦
- **長時間 capture 寫爆 disk**：未設 rotation 或 size limit — `--output-file` 加 size / time rotation、定期 archive 到 S3 + 過期刪除
- **Staging 容量比 production 小、放大流量打爆**：10x replay 沒先估下游 — capacity 規劃前先用 1x 暖機、觀察下游 saturation、再 ramp 到目標倍率

## 案例回寫

GoReplay 適合回寫 migration 與 production validation 案例。它可接 [9.C15 Tixcraft 售票壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的 production-shaped load、[9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 cutover 前 replay、[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 這類資料庫整併前的 query pattern 驗證、[9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 跨 DB 遷移的請求 pattern 重播，以及 [9.C30 Microsoft 365 MongoDB → Cosmos DB](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 的全球分析平台遷移 query 驗證。

這些案例的重點是 production request shape。GoReplay 頁引用案例時，要把 case 轉成 capture window、filter、rewrite、target isolation、rate limit 與 diff / saturation metric — 例如 Zomato 遷 DB 時、replay 必須先 mask PII + 改寫 SQL 方言、不能直接把 TiDB query 打進 DynamoDB SDK。

Capacity 規劃用 real workload model 是這些案例的共通對照啟示。Tixcraft 的售票 spike、SeatGeek 的 waiting room cutover、Netflix 的 Aurora 整併、Microsoft 365 的全球 query 分布 — 共通點是 *scripted scenario 無法事先列舉所有 endpoint 跟 payload 組合*。GoReplay 的回應是把「使用者行為建模」這個工作丟回給 production traffic 本身、規劃者只負責決定 capture window、replay rate 跟 target boundary，不再試圖窮舉 scenario。這個 mindset 才是 GoReplay 跟 [k6](/backend/09-performance-capacity/vendors/k6/) / [JMeter](/backend/09-performance-capacity/vendors/jmeter/) 在 capacity 規劃流程中的真正分工點。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 平行：[Service Mesh Mirroring](/backend/09-performance-capacity/vendors/service-mesh-mirroring/)
- 平行：[AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)
- 知識卡：[Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- 官方：[GoReplay documentation](https://docs.goreplay.org/)
