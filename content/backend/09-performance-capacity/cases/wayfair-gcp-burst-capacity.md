---
title: "9.C22 Wayfair：用 GCP 提供 Way Day / Black Friday 的 burst capacity"
date: 2026-05-12
description: "Wayfair 22M+ 商品 + 16,000+ 供應商、用 GCP 補充 on-prem data center 在峰值事件的 burst capacity"
weight: 22
tags: ["backend", "performance", "capacity", "case-study", "data-architecture", "gcp", "predictable-peak"]
---

這個案例的核心責任是說明「hybrid cloud burst」模式 — 平日跑自家 data center、峰值事件靠雲端補容量。這跟全部上雲（[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)）或全部自管的兩種極端都不同、是大企業常見的折衷路徑。

## 觀察

Wayfair 在 GCP 的關鍵敘述（引自 [Wayfair Case Study](https://cloud.google.com/customers/wayfair)）：

| 指標               | 數字                                            |
| ------------------ | ----------------------------------------------- |
| 商品數量           | 22 M+ 個 SKU                                    |
| 供應商數量         | 16,000+                                         |
| 員工數             | 17,000                                          |
| 服務地理           | 北美 + 歐洲                                     |
| 峰值事件           | Way Day（年度大促）、Black Friday、Cyber Monday |
| COVID Q2 2020 業績 | 美國淨營收成長 +82.5%                           |
| 架構模式           | Hybrid（on-prem + GCP burst）                   |

服務組合：BigQuery（資料倉儲）、Cloud Dataproc（資料處理）、Cloud Pub/Sub（資料注入）、Looker（dashboard）、Cloud DLP（合規）、C2 processors（高性能 compute）。

關鍵敘述：「Our automation systems signal the cloud to scale on demand」「We were able to reduce and eventually eliminate the need for change freezes leading up to big events」。

## 判讀

Wayfair 揭露三個 hybrid cloud burst 模式的工程重點。

1. **Hybrid burst 是「容量規劃成本平衡」的折衷**：自家 data center 平日跑得便宜、峰值事件不夠用；全部上雲峰值好辦但平日成本高。Hybrid 模式讓 baseline 用便宜的、峰值用彈性的、總成本曲線最平。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的長期 TCO 規劃。
2. **「Change freeze 不再需要」是 burst 模式的真正價值**：傳統零售 IT 為了 Black Friday 通常 2-3 個月前就 freeze code change、確保穩定。Wayfair 在 GCP burst 上線後、能在峰值前繼續正常 release — 因為新功能可以單獨 deploy 到 GCP、不影響 on-prem 主系統。對應 [06.8 release gate](/backend/06-reliability/release-gate/) 的非凍結式變更管理。
3. **資料平面（BigQuery / Dataproc）是 hybrid 的主場、交易平面仍在 on-prem**：Wayfair 把「分析、報表、推薦模型」放 GCP、「核心交易、訂單處理、庫存」仍在自家。這個切分是 hybrid 的常見做法 — 計算密集的工作上雲、業務核心保留自管。對應 [01 資料庫模組](/backend/01-database/) 的核心 OLTP 跟 [04 可觀測性模組](/backend/04-observability/) 的分析資料層分離。

需要警惕：

- Wayfair 案例 *沒有* 提具體 TPS、latency、capacity scale 數字 — 行銷敘述居多、工程細節較少。讀此類案例要對 *策略* 做學習、不要套用具體數字。
- 「82.5% 美國淨營收成長」是 *業績*、不是 *系統指標*。系統能撐業績、但兩者不是同一件事。

## 策略

可重用的工程做法：

1. **Hybrid burst 適合「業務核心 on-prem 已穩定 + 季節性 / 事件型峰值」的企業**：對於全新雲原生 startup、直接全上雲更簡單；對於有 15-20 年自建系統的大企業、hybrid 是穩妥路徑。
2. **資料平面先上雲、交易平面後上**：BI、ML、推薦這類「計算密集 + 資料量大 + 容忍延遲」適合先上 GCP / AWS / Azure；OLTP 後續再評估。對應 [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的資料層先行模式。
3. **automation signal + 雲端 burst 是「change freeze」的解法**：監控訊號 → 自動 trigger 雲端容量 → 平滑釋放 → 不影響 on-prem 主系統的部署節奏。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/)。

跨平台等效：AWS Outposts + AWS Direct Connect、Azure Arc + ExpressRoute、Equinix + 各雲商 PrivateLink 都是 hybrid burst 的基礎設施。差異是各家 hybrid 策略成熟度。

## 下一步路由

- 想規劃 hybrid cloud burst → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [9.11 高峰事件準備](/backend/09-performance-capacity/)
- 想做資料平面遷移 → [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) + [01 資料庫模組](/backend/01-database/)
- 對照全雲原生 → [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)
- 想取消 change freeze → [06.8 release gate](/backend/06-reliability/release-gate/) + [06.17 feature flag governance](/backend/06-reliability/feature-flag-governance/)

## 引用源

- [Wayfair Case Study (Google Cloud)](https://cloud.google.com/customers/wayfair)
- [Way Day 2019 burst capacity](https://cloud.google.com/blog/topics/customers)
