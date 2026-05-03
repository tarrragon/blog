---
title: "Amazon"
date: 2026-05-01
description: "Amazon Cell-based Architecture / Shuffle Sharding / Blast Radius 設計"
weight: 3
---

Amazon 是 cell-based architecture 與 shuffle sharding 的代表、AWS Builders' Library 是大規模分散式系統的工程實踐 SSoT。教學重點在「如何設計才能讓失效局部化」。

## 規劃重點

- Cell-based Architecture：把服務切成獨立 cell、每個 cell 有完整 stack
- Shuffle Sharding：客戶請求映射到 cell 的隨機切分、讓單一壞客戶無法擊倒所有 cell
- Static Stability：control plane 失效時 data plane 仍能服務
- Constant Work Pattern：avoid scaling traffic in failure modes
- AWS Builders' Library：可重用 reliability patterns 的官方文件

## 預計收錄實踐

| 議題                     | 教學重點                                          |
| ------------------------ | ------------------------------------------------- |
| Cell-based Architecture  | DynamoDB / Route 53 / S3 的 cell 劃分原則         |
| Shuffle Sharding         | 數學上的 blast radius 量化                        |
| Static Stability         | control / data plane 分離的設計取捨               |
| Workload Isolation       | tenancy / region / availability zone 的隔離層級   |
| Build with constant work | 為何 push-based 比 pull-based 在 failure 時更穩定 |

## 案例定位

Amazon 這個案例在講的是可靠性如何靠隔離來守住擴散邊界。讀者先看懂 cell-based architecture 與 shuffle sharding 的責任，再把它們當成控制 blast radius 的設計語言，而不是單純的 AWS 名詞。

## 判讀重點

當多租戶系統出現資源爭用時，cell 邊界先決定故障能擴散到哪裡。當容量壓力開始拉高時，shuffle sharding 讓風險分散到不同子集合，避免單一熱點把整個服務拖進同一個失敗模式。

## 可操作判準

- 能否指出一個 workload 的 blast radius 邊界
- 能否把共享基礎設施切成可獨立恢復的 cell
- 能否說明 contention 會落在哪個 shard
- 能否把 recovery 設計成分批恢復，而不是一次全開

## 與其他案例的關係

Amazon 的重點是把隔離變成架構語言，這和 Meta 的 region failover、Shopify 的 pod 架構、GCP 的控制面邊界都在同一條線上。差別只在於 Amazon 更早把 cell 與 shard 語言標準化，所以特別適合用來反推其他大型平台的設計選擇。

## 代表樣本

- cell-based architecture 讓一個 cell 壞掉時，其他 cell 仍能維持服務。
- shuffle sharding 將多租戶請求分散到不同子集合，限制單一客戶或單一熱點的擴散範圍。
- static stability 讓 control plane 失效時 data plane 仍可服務。
- constant work pattern 避免失敗模式下的額外放大成本。
- workload isolation 讓 tenancy / region / AZ 的邊界能各自承擔風險。
- failure containment 讓擴散先停在 cell 或 shard 邊界。
- push-based recovery 讓恢復節奏不依賴大規模同步操作。
- fault isolation 讓局部失效不會拖垮整個 fleet。
- constant work 讓 failure mode 不會因為多做一件事而繼續放大。

## 引用源

- [Introducing The Amazon Builders’ Library](https://aws.amazon.com/about-aws/whats-new/2019/12/introducing-amazon-builders-library/)：Builders' Library 的官方入口。
- [Workload isolation using shuffle-sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)：shuffle sharding 與 fault isolation 的官方文章。
- [FAQ - Reducing the Scope of Impact with Cell-Based Architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/faq.html)：cell-based architecture 與 shuffle sharding 的關係說明。
