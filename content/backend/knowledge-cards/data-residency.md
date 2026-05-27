---
title: "Data Residency"
date: 2026-05-27
description: "合規要求資料留在特定地理邊界內、跨境複製違反合規、推動 fleet 拓樸決策"
weight: 370
---

Data residency 的核心概念是「合規法規（GDPR、PIPL、LGPD、美國 Wire Act 等）要求資料留在某個地理邊界內、跨境複製本身違反合規、不是延遲或成本議題」。它是 *合規驅動的地理邊界*、跟 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/)（業務 / 帳戶邊界）跟 [Trust Boundary](/backend/knowledge-cards/trust-boundary/)（安全 / 信任邊界）相鄰但語意分離 — 三者可能在同一系統共存、但決策驅動力不同。

## 概念位置

Data residency 直接決定 multi-region database 的拓樸選擇。Aurora Global Database 用 cross-region async replication、在受監管金融場景反指標 — 因為資料一旦複製到另一 region 就違反合規、不是 SLA 換的事。CockroachDB locality + placement、Spanner regional configuration、DynamoDB region-pinned Global Tables 是 *合規吸收層* — 用宣告式 region pinning 把資料邏輯綁在合規邊界內、application code 不需要重寫。AWS Outposts / Azure Stack 是另一條路徑、把雲服務硬體直接部署到合規邊界（例如美國 sportsbook 跨州合規要求運算留州內）。

跟 [Blast Radius](/backend/knowledge-cards/blast-radius/) 共軸 — 合規邊界常剛好等於 blast radius 邊界、但兩者的決策驅動力不同（合規是法規硬限、blast radius 是失敗影響範圍）。

## 可觀察訊號與例子

需要面對 data residency 的訊號是「monolith 要進歐盟 / 中國 / 巴西市場」、或「金融 / 醫療 / 博弈業要進跨境部署」。對應 case：Standard Chartered Aurora 7 cluster fleet 路徑（銀行業跨國合規邊界、跨市場業務邏輯弱、每市場獨立 cluster 可行）；Hard Rock Wire Act 跨州博弈（跨州統一帳戶 + 跨州 reporting 是核心業務、必須邏輯一個 CockroachDB cluster + locality placement 吸收合規）。同一個 *合規 driver*、不同 *業務需求強度* 推出完全相反的拓樸決策。

## 設計責任

設計受合規驅動的系統時、要先把 residency 規則 *寫進 schema 層 / placement policy*、不是寫在 application code retry 邏輯。讀者規劃 Aurora migration 不能假設 Global Database 一定可用 — 合規禁止跨境複製時要改用每市場獨立 cluster。判讀軸線：(1) 合規顆粒（跨國 / 跨州 / 跨 AZ）、(2) 跨 boundary 業務邏輯需求強度（強 → distributed SQL locality / 弱 → fleet of independent clusters）、(3) 團隊運維能力（單邏輯 cluster 跨 region vs 多獨立 cluster fleet）。錯把 latency 當主因（例如把 AWS Outposts 當「降低 cross-state latency 工具」）會買到 wrong tool — Outposts 的存在動機是 residency、latency 改善是副作用。
