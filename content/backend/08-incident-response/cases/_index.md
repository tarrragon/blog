---
title: "事故處理服務案例庫"
date: 2026-05-01
description: "按服務組織的公開事故案例庫，累積架構脈絡與 longitudinal pattern"
weight: 90
tags: ["backend", "incident-response", "case-study"]
---

本案例庫以服務為單位、收錄公開事故報告（post-mortem / status page / 工程部落格）。每個服務一個資料夾，累積該服務的架構脈絡、事故時間線與共通失敗模式。

服務分層依 [模組八 _index](/backend/08-incident-response/) 的 T1 / T2 / T3 規劃。重複出現於 06 / 08 的服務（stripe / cloudflare / linkedin）資料夾住在主要教學模組、跨模組以連結互通。

## 完成狀態

案例庫的完成狀態以「可直接引用的事故頁」為準。服務資料夾只算索引，子案例頁才算可引用素材；每篇子案例至少要有事故摘要、判讀訊號、事故路徑、可回寫控制面、下一步路由與引用源。

| 服務       | 已完成案例                                                                                                                                                                                                                                                                                                                     | 下一步               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| Cloudflare | [2019 Regex CPU Outage](/backend/08-incident-response/cases/cloudflare/2019-regex-cpu-outage/)、[2023 Control Plane Token Incident](/backend/08-incident-response/cases/cloudflare/2023-control-plane-token-incident/)、[2026 BYOIP BGP Withdrawal](/backend/08-incident-response/cases/cloudflare/2026-byoip-bgp-withdrawal/) | 已回寫 4.21 / 6.24   |
| AWS S3     | [2017 US-EAST-1 Service Disruption](/backend/08-incident-response/cases/aws-s3/2017-us-east-1-service-disruption/)                                                                                                                                                                                                             | 補 2021 多服務退化   |
| GitHub     | 尚未展開                                                                                                                                                                                                                                                                                                                       | 先寫 2018 MySQL 事故 |
| GCP        | 尚未展開                                                                                                                                                                                                                                                                                                                       | 先寫全球控制面案例   |
| Atlassian  | 尚未展開                                                                                                                                                                                                                                                                                                                       | 先寫 2022 多租戶誤刪 |
| Roblox     | 尚未展開                                                                                                                                                                                                                                                                                                                       | 先寫 2021 長事故     |
| Fastly     | 尚未展開                                                                                                                                                                                                                                                                                                                       | 先寫 2021 config bug |

## T1 服務

- [aws-s3](/backend/08-incident-response/cases/aws-s3/)
- [cloudflare](/backend/08-incident-response/cases/cloudflare/)
- [github](/backend/08-incident-response/cases/github/)
- [gcp](/backend/08-incident-response/cases/gcp/)
- [atlassian](/backend/08-incident-response/cases/atlassian/)
- [roblox](/backend/08-incident-response/cases/roblox/)
- [fastly](/backend/08-incident-response/cases/fastly/)

## T2 服務

- [slack](/backend/08-incident-response/cases/slack/)
- [datadog](/backend/08-incident-response/cases/datadog/)
- [stripe（住於 06）](/backend/06-reliability/cases/stripe/)
- [discord](/backend/08-incident-response/cases/discord/)
- [azure-ad](/backend/08-incident-response/cases/azure-ad/)

## T3 服務

- [heroku](/backend/08-incident-response/cases/heroku/)
- [linkedin（住於 06）](/backend/06-reliability/cases/linkedin/)
- [reddit](/backend/08-incident-response/cases/reddit/)
- [microsoft-365](/backend/08-incident-response/cases/microsoft-365/)
