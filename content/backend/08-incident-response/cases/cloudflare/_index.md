---
title: "Cloudflare"
date: 2026-05-01
description: "Cloudflare 全球 edge 事故時間線與架構脈絡"
weight: 2
---

Cloudflare 是 anycast edge 的代表、單一配置 push 即可影響全球流量、是 configuration push 風險 / regex catastrophic backtracking / BGP 信任的教學標竿。Cloudflare 工程部落格公開度極高、post-mortem 細節豐富。

## 規劃重點

- 全球 configuration push 的 blast radius：為何 60 秒內可癱瘓全球流量
- Regex CPU 耗盡：catastrophic backtracking 如何繞過所有 timeout
- BGP 風險：路由洩漏如何把流量吸入錯誤 ASN
- Recovery 設計：為何 configuration rollback 需要 dataplane 層協作

## 預計收錄事故

| 年份 | 事故               | 教學重點                                     |
| ---- | ------------------ | -------------------------------------------- |
| 2019 | Regex CPU 27 分鐘  | catastrophic backtracking、WAF rule 部署流程 |
| 2020 | BGP route leak     | 跨 ASN 信任、網路層事故止血                  |
| 2022 | 配置 push 全球退化 | 變更節奏、staged rollout 的價值              |
| 2023 | R2 outage          | 新服務的 capacity 假設與 dependency 暴露     |

## 案例定位

Cloudflare 這個案例在講的是 edge 平台如何把一個小錯誤快速放大到全球。讀者先看懂配置推送、runtime 驗證與路由撤銷各自的責任，再把 anycast 與 control plane 當成事故擴散的核心路徑。

## 判讀重點

當 regex、workers 設定或 deployment tool 出現問題時，真正危險的不是單一節點故障，而是錯誤被快速推到全網。當 BGP 或 BYOIP 參數變動時，回滾與驗證就必須先於擴散，否則影響會直接表現在全球流量上。

## 可操作判準

- 能否在全網推送前做足夠的配置驗證
- 能否把 blast radius 限制在局部 edge 群組
- 能否在 CPU 熱點或路由撤銷前先看見異常
- 能否把 rollback 動作設計成快速且可驗證

## 與其他案例的關係

Cloudflare 和 Fastly 都在講 edge 平台的快速擴散，但 Cloudflare 更常暴露控制面與部署工具的問題。它和 AWS S3、GCP 放在一起看，可以更清楚看到全球網路事故不是單一節點失效，而是配置與路由鏈條的連鎖反應。

## 代表樣本

- 2019 年 regex CPU outage 是 catastrophic backtracking 直接拖垮 edge runtime 的經典樣本。
- 2023 年控制面事故與 2026 年 BYOIP / BGP 事故則顯示配置與路由都能成為全球擴散點。
- 這組樣本也能對照配置推送與回滾速度對 blast radius 的影響。
- Cloudflare 的事故史很適合拿來和 Fastly 比較 edge 平台差異。
- workers / deployment tool misconfiguration 讓控制面本身成為風險。
- anycast edge 讓路由錯誤能在全球尺度迅速顯現。
- global propagation 讓回滾時間直接影響用戶體感。
- control plane bug 常常比 data plane bug 更難局部化。

## 引用源

- [Details of the Cloudflare outage on July 2, 2019](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019)：regex CPU / catastrophic backtracking 事故的官方回顧。
- [Cloudflare incident on January 24, 2023](https://blog.cloudflare.com/cloudflare-incident-on-january-24th-2023/)：service token / control plane 變更導致的多產品連鎖影響。
- [Cloudflare incident on October 30, 2023](https://blog.cloudflare.com/cloudflare-incident-on-october-30-2023/)：Workers KV / deployment tool misconfiguration 的控制面事故。
- [Cloudflare outage on February 20, 2026](https://blog.cloudflare.com/cloudflare-outage-february-20-2026/)：BYOIP / BGP 變更造成的路由撤銷事故。
