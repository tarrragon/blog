---
title: "AWS VPC Traffic Mirroring"
date: 2026-05-15
description: "用 VPC 網路層封包鏡像觀察 production traffic 的低侵入 production validation 方式"
weight: 22
tags: ["backend", "performance", "capacity", "vendor", "aws", "traffic-mirroring"]
---

AWS VPC Traffic Mirroring 的核心責任是在 VPC 網路層複製 ENI traffic，讓團隊用低 application 侵入方式觀察 production flow。它適合封包級診斷、網路安全分析、流量樣本收集與部分 replay 前置資料蒐集，重點在明確定義 mirror source、filter、target、加密邊界與保存責任。

## 定位

AWS VPC Traffic Mirroring 適合需要網路層能見度的 AWS workload。當 application code、service mesh 或 host capture 都不適合改動時，VPC 層 mirror 可以從 ENI 複製封包到 analysis appliance、IDS、packet capture 或自管處理服務。

這個定位讓 AWS VPC Traffic Mirroring 接到 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 的 shadow traffic 前置觀測。它偏封包觀察與樣本收集，若要做應用層 replay、filter、rewrite 或 side effect 隔離，通常還需要 GoReplay、proxy、custom processor 或測試環境配合。

## 適用場景

網路層瓶頸定位適合 VPC Traffic Mirroring。當 latency、packet loss、TLS handshake、connection reset、NAT、load balancer 或 cross-AZ traffic 是疑點時，封包 mirror 能提供 application metrics 看不到的證據。

低侵入 traffic sampling 適合 VPC Traffic Mirroring。團隊可以在不改 application code 的情況下收集 production flow，作為 workload model、security analysis 或 replay pipeline 的輸入。

受管 AWS 網路環境適合 VPC Traffic Mirroring。當服務主要跑在 EC2 / ENI 可 mirror 的環境中，VPC 原生能力可以讓網路團隊用既有安全與觀測流程管理。

## 選型判準

| 判準       | AWS VPC Traffic Mirroring 的價值     | 需要補的能力                       |
| ---------- | ------------------------------------ | ---------------------------------- |
| 網路層鏡像 | application 無侵入、封包級可見       | L7 解碼、filter、rewrite 與 replay |
| AWS 原生   | VPC / ENI / filter / target 整合     | AWS 約束、跨帳號與跨 VPC 設計      |
| 安全分析   | 可接 IDS、packet analyzer、forensics | PII / payload 保存與存取控制       |
| 流量樣本   | 可支援 workload model 校正           | 加密 traffic 處理與樣本代表性      |

網路層鏡像價值來自低侵入。團隊可以在不調整 application 或 service mesh 的情況下取得 flow evidence，但也要承擔 L7 語意不足的限制。

安全分析價值來自封包細節。對容量工程而言，封包證據能幫忙確認 connection、TLS、NAT、load balancer 與跨區流量成本；對資安而言，則能支援 IDS 與 forensic workflow。

## 跟其他方式的取捨

AWS VPC Traffic Mirroring 和 GoReplay 的主要差異是層級。VPC mirroring 在 L3 / L4 觀察封包；GoReplay 更接近 HTTP application replay，對 request rewrite 與 target control 更直接。

AWS VPC Traffic Mirroring 和 service mesh mirroring 的主要差異是控制範圍。VPC mirroring 由網路層控制，適合低侵入封包觀察；service mesh mirroring 由 L7 route policy 控制，適合服務版本與 route 對照。

AWS VPC Traffic Mirroring 和 synthetic load test 的主要差異是用途。VPC mirroring 提供 production traffic evidence；synthetic load test 提供可控壓力。兩者常搭配：先用 mirror 校正 workload model，再用 k6 / Gatling / Locust 產生可控負載。

## 操作成本

AWS VPC Traffic Mirroring 的主要成本是資料治理。Mirror target 可能收到 payload、token、cookie、internal identifiers 與敏感資料，因此保存、查詢、保留期限、存取權與刪除責任要先定義。

網路成本來自複製 traffic。Mirror session 會增加網路流量與 target processing 成本，高流量服務要先估算 mirror ratio、filter、target capacity 與跨 AZ 費用。

加密成本來自 L7 可讀性。TLS traffic 在網路層 mirror 後通常仍是加密封包；若需要 application payload，要搭配解密點、proxy、key 管理或 application-level capture。

## Evidence Package

AWS VPC Traffic Mirroring 結果應回寫到 evidence package。最小欄位包括 mirror source ENI、filter rule、mirror target、session number、time range、sampling / truncation、target capacity、payload handling、packet metrics、known gap 與 owner。

| 欄位         | AWS VPC Traffic Mirroring 證據來源           |
| ------------ | -------------------------------------------- |
| Source       | mirror session、filter、target config        |
| Time range   | mirror start / end                           |
| Query link   | packet analyzer、flow logs、metrics link     |
| Data quality | filter coverage、sampling、encryption status |
| Confidence   | target capacity、source coverage             |
| Known gap    | 加密 payload、未 mirror ENI、L7 語意不足     |

Evidence package 的核心用途是把網路層觀察接回效能判斷。Reviewer 要能知道 mirror 覆蓋哪些 ENI、哪些封包被 filter、target 是否有 capacity，以及封包證據如何對應到 application latency 或 saturation。

## 案例回寫

AWS VPC Traffic Mirroring 適合回寫網路與平台層效能案例。它可接 [9.C34 GCP 130K node GKE cluster](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/) 的大規模網路觀測需求（雖在 GCP、但網路證據的層次拆解可類比）、[9.C22 Wayfair GCP burst capacity](/backend/09-performance-capacity/cases/wayfair-gcp-burst-capacity/) 的跨雲容量觀測、[9.C1 Prime Day readiness](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) 的 pre-event network evidence、[9.C12 Riot Games 246 EKS cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 跨 cluster 的網路流量觀測、以及 [9.C24 Genesys DynamoDB 15-region](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) 的 99.999% 可用性下封包層 evidence 補強。

這些案例的重點是網路層 evidence。VPC Traffic Mirroring 頁引用案例時，要把 case 轉成 mirror source、filter、target capacity、packet metric、cross-AZ cost 與 L7 correlation — 例如 Riot Games 35ms 延遲門檻下、cross-AZ traffic mirror 本身會增加成本、必須先用 filter 收斂到關鍵 ENI。

## 下一步路由

- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 平行：[GoReplay](/backend/09-performance-capacity/vendors/goreplay/)
- 平行：[Service Mesh Mirroring](/backend/09-performance-capacity/vendors/service-mesh-mirroring/)
- 知識卡：[Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- 官方：[AWS VPC Traffic Mirroring documentation](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html)
