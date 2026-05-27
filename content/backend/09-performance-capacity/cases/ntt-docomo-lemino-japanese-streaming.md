---
title: "9.C29 NTT DOCOMO Lemino：3 個月達 500 萬 MAU 的串流後端"
date: 2026-05-12
description: "Lemino 用 DynamoDB + AWS Media Services 撐 30 channels live + 5M MAU、工程工時下降 90%"
weight: 29
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "predictable-peak"]
---

這個案例的核心責任是說明「電信商級新串流服務」如何用雲端服務快速 launch + scale。Lemino 是 NTT DOCOMO 在 2023-04 推出的串流服務、3 個月達 5M MAU、工程工時下降 90% — 這個「不用大量工程師」的營運模式靠的是 managed services 組合、不是自建。

## 觀察

NTT DOCOMO Lemino 在 AWS 的關鍵數字（引自 [Lemino Case Study](https://aws.amazon.com/solutions/case-studies/ntt-docomo-lemino/)）：

| 指標              | 數字                       |
| ----------------- | -------------------------- |
| 3 個月 MAU        | 500 萬                     |
| 同時直播頻道      | 30 channels（規劃擴到 50） |
| DynamoDB 請求峰值 | tens of thousands req/sec  |
| 工程工時下降      | 90%（vs 自建）             |
| 啟動年份          | 2023-04                    |

服務組合：AWS Media Services（Elemental Link、MediaConnect、MediaLive、MediaPackage）、Amazon Aurora、Amazon DynamoDB、DynamoDB Accelerator (DAX)、Amazon OpenSearch Service。

關鍵敘述：採用 DynamoDB 的原因 — 「connection limits became bottlenecks when experiencing a rapid increase in access」。

## 判讀

Lemino 案例揭露三個現代串流服務啟動的工程重點。

1. **「connection limit 是 RDB 的隱性 bottleneck」是 OLTP 在 surge 下的典型問題**：傳統 RDB（PostgreSQL、MySQL）每個連線吃記憶體跟 process / thread、connection pool 上限通常 1K-5K 個。當突發流量湧入、第一個爆的不是 CPU 也不是 disk、是 *連線數量*。DynamoDB 的 HTTP API 模型沒有 connection state、天然解決這個問題。對應 [01 資料庫模組](/backend/01-database/) 的 connection pool 議題、跟 [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 遷移動機同類。
2. **AWS Media Services 是「電視台級」串流基礎設施**：Elemental Link（encoding）、MediaConnect（transport）、MediaLive（live encoding）、MediaPackage（packaging + DRM）— 這套 stack 過往是電視台才買得起的硬體設備、AWS 把它變成 pay-per-use 服務。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 vendor-specific 串流服務評估。
3. **90% 工程工時下降 = 走 managed 路線的真正價值**：傳統電信商 launch 串流服務、要養 50-100 個 SRE + DBA + network 工程師、Lemino 用 managed 服務只需 5-10 個。差距不在「能不能 launch」、在「launch 後的維運成本」。對應 [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 的同類訴求。

需要警惕：「tens of thousands req/sec」可能指 2 萬或 8 萬、差距 4 倍。「3 個月 5M MAU」很亮眼、但 NTT DOCOMO 自身有 8000 萬+ 電信用戶可以推、不是純自然成長。

## 策略

可重用的工程做法：

1. **新串流服務優先選 DynamoDB / Cosmos DB / Bigtable 撐 metadata 層**：避免 connection limit、避免 schema migration、避免 DBA 維運成本。
2. **AWS Media Services / GCP Media CDN / Azure Media Services 是新進入者快速 launch 的捷徑**：不要重造串流 stack、直接用 vendor 提供的。
3. **DAX 是 DynamoDB 讀 cache 的標準解法**：當讀峰值持續高（例如熱門節目首播、Hotstar 等級）、加 DAX 減少 DynamoDB 讀次數、降低成本。對應 [02 快取模組](/backend/02-cache-redis/)。
4. **小團隊 + managed services 是電信商雲端轉型的範本**：傳統電信商過去靠人海戰術、現在改靠 managed + 工程紀律。

跨平台等效：GCP 提供 Media CDN + Anvato，Azure 提供 Media Services + Azure Front Door — 各家都有完整串流 stack。

## 下一步路由

- 對照其他串流案例 → [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/)（live 直播）/ [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)（VOD metadata）
- 想理解 connection limit 議題 → [01 資料庫模組](/backend/01-database/) + [9.C20 Zomato 遷移](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)
- 想做 DAX / cache 加速 → [02 快取模組](/backend/02-cache-redis/) + [9.C25 Tubi ML feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)
- 想規劃 managed-only 串流 stack → [05 部署平台模組](/backend/05-deployment-platform/) + [00 服務選型模組](/backend/00-service-selection/)
- 想做串流 metadata 的 partition / GSI 設計 → [DynamoDB partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) + [DynamoDB GSI / LSI 設計](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)
- 想評估 on-demand vs provisioned 給直播 / VOD 用 → [DynamoDB on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)

## 引用源

- [NTT Docomo Rebuilds Infrastructure for Lemino Streaming Service Launch](https://aws.amazon.com/solutions/case-studies/ntt-docomo-lemino/)
- [Direct to Consumer & Streaming on AWS](https://aws.amazon.com/media/direct-to-consumer-d2c-streaming/)
