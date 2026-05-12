---
title: "9.C2 GR8 Tech：AI 預測式自動擴容下的體育博彩高峰"
date: 2026-05-12
description: "AI 預測 + EKS 自動擴容怎麼在 25ms p95 下承載 54000 TPS 體育博彩峰值流量"
weight: 2
tags: ["backend", "performance", "capacity", "case-study"]
---

這個案例的核心責任是說明「事件型不可預期峰值」的工程做法。體育博彩流量的形狀跟 Prime Day 不同 — 峰值會在賽事的特定瞬間（進球、最後一分鐘）爆量、單一賽事內可能有多次脈衝、跨賽事的時間點難以提前數月排程。GR8 Tech 在 2022 FIFA World Cup 期間達到零停機營運、是這類負載形狀的有效參考。

## 觀察

GR8 Tech 從本地基礎設施遷移到 AWS、重建為微服務架構後的關鍵數字（引自 [GR8 Tech case study](https://aws.amazon.com/solutions/case-studies/gr8-tech-case-study/)）：

| 指標     | 遷移前狀況                | 遷移後峰值               |
| -------- | ------------------------- | ------------------------ |
| 投注延遲 | 賽事高峰期額外延遲 2-3 秒 | 25 ms p95                |
| 結算吞吐 | （未公開）                | 每分鐘 100 萬次投注結算  |
| 交易吞吐 | （未公開）                | 54000 TPS @ 25ms p95     |
| 同時在線 | -                         | 200,000+ 同時使用者      |
| 投注吞吐 | -                         | 每分鐘 80,000 次體育投注 |
| 可用性   | -                         | 99.95% uptime            |
| 成本彈性 | 固定預配置                | 需求降低時成本下降 25%   |

服務組合：Amazon EKS（Kubernetes 容器編排、跨雲端與本地）、Amazon EC2（compute）、Amazon S3 與 Amazon EBS（儲存）、AWS Auto Scaling 結合 **GR8 Tech 自家 AI 預測模型**、AWS Infrastructure Event Management（重大賽事支援）。

擴展範圍：「Scaled to 15 markets using AWS」。事件覆蓋：2022 FIFA World Cup 期間零停機。

## 判讀

GR8 Tech 的工程做法揭露三個事件型峰值的判讀重點。

1. **不可預期 ≠ 不可預測**：賽事「何時開打」是已知的（schedule 提前公告）、「賽事內何時爆量」是未知的（進球、加時、最後一分鐘）。AI 預測模型不是預測「會不會有峰值」、而是預測「峰值在 60 秒內可能多大」、把擴容窗口縮短到反應時間之內。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 跟 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的「預測時間尺度」軸。
2. **延遲是業務指標、不是技術指標**：「2-3 秒額外延遲」直接造成「投注失敗、客戶流失」。25ms p95 是收入 KPI 而不是 SLO 漂亮數字。對應 [9.8 效能可觀測性](/backend/09-performance-capacity/) 把 latency 翻成業務 metric 的責任。
3. **微服務 + 容器編排是擴容粒度的前置**：遷移前的單體系統「擴容」只能複製整套系統、成本曲線陡峭。EKS 拆解後可以針對熱點服務（投注引擎、結算引擎）獨立擴容、跟 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的逐層定位直接對齊。

需要警惕的判讀盲點：54000 TPS @ 25ms 是 *公開的成功數字*、不是「永遠都這樣」的承諾。AI 預測模型必然有預測誤差、AWS Infrastructure Event Management 也是事件型服務、不是平台預設。這類案例適合作為「目標可達性」的存在證明、不適合直接套用為自家服務的容量假設。

## 策略

可重用的工程做法：

1. **把賽事 schedule 灌進 capacity forecast**：在事件已知的條件下、預先把 baseline 拉高、避免 AI 模型在零起跑時擴容。對應 EC2 Auto Scaling 的 [scheduled scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scheduled-scaling.html) + predictive scaling 雙模。
2. **AI 模型輸入要包含領域訊號**：通用 ML autoscaler 用 CPU / latency 預測、領域 autoscaler 還會用 *賽事重要性*、*投注量歷史曲線*、*下注玩家集中度* 等業務訊號。這層讓擴容時機從反應式變成預測式。
3. **熱點服務獨立擴容、不是整體擴容**：投注引擎跟結算引擎的峰值時間不一致（投注集中在賽前 + 比賽中、結算集中在賽後）、單獨擴容比整體擴容省 25%+ 成本。
4. **AWS Infrastructure Event Management 等廠商支援服務**：在年度重大事件可以申請（World Cup、Olympic、Black Friday 等）、提供 pre-scaling 與專屬監控通道。這在 GCP / Azure 也有對等服務（GCP Customer Care Premium、Azure Event Management Support）。

跨平台等效：GCP GKE + Vertical Pod Autoscaler + 自家 ML 預測、Azure AKS + KEDA + Azure ML 預測、自建 Kubernetes + Karpenter + Prometheus 推導模型都可以實作同樣的「預測 + 擴容」模式。

## 下一步路由

- 想做事件型峰值的容量預測 → [9.11 高峰事件準備](/backend/09-performance-capacity/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想用 AI / ML 做預測式擴容 → [9.9 Performance Improvement Loop](/backend/09-performance-capacity/) + [9.8 效能可觀測性](/backend/09-performance-capacity/)
- 想拆解微服務以便獨立擴容 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/) + [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)
- 對照不同形狀的峰值 → [9.C1 AWS Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)（可預期極端峰值）/ [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)（無峰值低延遲）

## 引用源

- [GR8 Tech Achieves High Performance and Scalability with Data Center Migration to AWS](https://aws.amazon.com/solutions/case-studies/gr8-tech-case-study/)
- [Predictive scaling for Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-predictive-scaling.html)
- [Scheduled scaling for Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scheduled-scaling.html)
