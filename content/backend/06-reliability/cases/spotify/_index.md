---
title: "Spotify"
date: 2026-05-01
description: "Spotify Chaos Engineering 與 Squad-based SRE"
weight: 21
---

Spotify 是音樂串流平台、squad-based 組織模型對 SRE 實踐有特殊影響、chaos engineering 文章是 mid-size company 採用 chaos 的代表。

## 規劃重點

- Squad-based SRE：分散式組織下的可靠性責任分配
- Backstage：開源開發者平台的可靠性整合
- Chaos engineering 採用過程：從 zero 到 mature 的實踐軌跡
- Streaming infrastructure：高頻寬媒體的可靠性挑戰

## 預計收錄實踐

| 議題                       | 教學重點                               |
| -------------------------- | -------------------------------------- |
| Backstage                  | service catalog + reliability metadata |
| Squad SRE                  | 分散組織的可靠性責任                   |
| Chaos Engineering Adoption | Spotify 的 chaos 起步歷程              |
| CDN / Streaming Resilience | 媒體串流的失敗模式                     |

## 案例定位

Spotify 這個案例在講的是平台工程如何把可靠性散到每個 squad，又把共同能力集中到 Backstage 這類基礎設施。讀者先抓 squad-based SRE、service catalog 與 declarative infrastructure 的關係，再看它們怎麼支撐大型串流平台。

## 判讀重點

當組織採用分散責任模型時，可靠性不再只靠中央團隊，而是靠平台把常見能力做成共同元件。當 fleet 或 streaming 基礎設施需要治理時，重點是 catalog 與 control plane 是否讓團隊看得到、管得動。

## 可操作判準

- 能否把 service catalog 跟 reliability metadata 接起來
- 能否說清楚 squad 與平台各自負責什麼
- 能否用 declarative infrastructure 管 fleet 變化
- 能否在 chaos 採用時保住平台一致性

## 與其他案例的關係

Spotify 的重點是把可靠性做成平台能力，這和 LinkedIn 的 operability、Honeycomb 的 observability、Meta 的 control plane 治理屬於相近抽象層。不同的是 Spotify 更強調組織分工，所以很適合拿來說明平台如何支撐分散團隊。

## 代表樣本

- Backstage 將 service catalog 與 reliability metadata 整合成平台入口。
- declarative infrastructure 讓 fleet 管理變成可重現的控制流程。
- squad-based SRE 讓責任分散到服務團隊。
- chaos engineering adoption 讓平台能力和演練節奏一起成熟。
- streaming resilience 讓高頻寬服務的失敗模式能被平台化管理。
- service catalog 讓可靠性資訊跟服務拓撲一起被看見。
- fleet management 讓大規模機器與服務狀態保持一致。
- catalog-driven ops 讓平台資訊成為日常營運入口。

## 引用源

- [About | Spotify Engineering](https://engineering.atspotify.com/about/)：Spotify Engineering 與 Backstage 的官方入口。
- [Announcing Backstage](https://backstage.io/blog/2020/03/16/announcing-backstage)：Backstage 的開源宣布與背景。
- [Technical overview](https://backstage.io/docs/overview/technical-overview)：Backstage 的技術總覽與 catalog/portal 說明。
- [Fleet Management at Spotify (Part 2): The Path to Declarative Infrastructure](https://engineering.atspotify.com/2023/05/fleet-management-at-spotify-part-2-the-path-to-declarative-infrastructure/)：大規模 fleet 與控制面的治理。
