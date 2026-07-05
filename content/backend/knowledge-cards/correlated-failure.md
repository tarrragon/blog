---
title: "Correlated Failure"
date: 2026-07-04
description: "以為獨立的多個元件共享一個隱藏的失效觸發器、在同一時刻一起壞；冗餘副本、觀測系統、跨區部署都可能共命運"
weight: 50
tags: ["backend", "knowledge-card", "reliability"]
---

Correlated failure（相關失效 / 共命運失效）指多個以為彼此獨立的元件、其實共享一個隱藏的失效觸發器、於是在同一時刻一起壞。它戳破的假設是「多放幾份就更可靠」—— 冗餘只在失效彼此獨立時才乘上可靠性；共享觸發器讓 N 份副本的有效冗餘塌回 1。跟 [cascading failure](/backend/knowledge-cards/cascading-failure/) 常接力出現，但觸發機制不同。

## 常見的共享觸發器

- **同一次變更**：跨區同時套用的自動更新、同一份錯誤配置推到所有副本 —— 副本再多也一起中招。
- **同一層基礎設施**：同一個電源、機架、可用區、DNS、憑證到期 —— 上層看似獨立、共享底層。
- **同一份觀測**：把「我有沒有事」外包給單一供應商、供應商掛了所有服務同時失去可見性（見 [4.25 觀測共命運失效](/backend/04-observability/observability-shared-fate/)）。
- **同一個相依**：多個服務共用一個 metadata service、cache 或 auth，它過載時全部一起降。

## 跟 cascading failure 的差別

[Cascading failure](/backend/knowledge-cards/cascading-failure/) 是「一個壞了、透過重試 / 負載轉移把壓力傳給下一個、逐級放大」—— 有時間先後與因果傳導。Correlated failure 是「同一個觸發器讓多個同時壞」—— 沒有先後、是共享隱藏依賴。兩者常接力出現：一次 correlated failure 打掉多個副本、剩下的承受不了而 cascading。

## 概念位置

Correlated failure 是冗餘設計的邊界條款：畫 [blast radius](/backend/knowledge-cards/blast-radius/) 與失效域時，要問的不是「有幾份副本」而是「這幾份會不會一起死」。防禦方向是拆開共享觸發器 —— 分批 rollout（不是所有副本同時套變更）、跨獨立失效域部署（不同區 / 不同供應商 / 不同 DNS）、關鍵訊號留 out-of-band 的第二條路。
