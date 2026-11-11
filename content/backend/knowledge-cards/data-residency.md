---
title: "Data Residency"
date: 2026-05-27
description: "合規要求資料留在特定地理邊界內、跨境複製違反合規、推動 fleet 拓樸決策"
weight: 371
---

Data residency 的核心概念是「合規法規（GDPR、PIPL、LGPD、美國 Wire Act 等）要求資料留在某個地理邊界內、跨境複製本身違反合規、不是延遲或成本議題」。它是 *合規驅動的地理邊界*、跟 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/)（業務 / 帳戶邊界）跟 [Trust Boundary](/backend/knowledge-cards/trust-boundary/)（安全 / 信任邊界）相鄰但語意分離 — 三者可能在同一系統共存、但決策驅動力不同。

## 跟其他概念的關係

Data residency 直接決定 multi-region database 的拓樸選擇。Aurora Global Database 用 cross-region async replication、在受監管金融場景反指標 — 因為資料一旦複製到另一 region 就違反合規、不是 SLA 換的事。CockroachDB locality + placement、Spanner regional configuration、DynamoDB region-pinned Global Tables 是 *合規吸收層* — 用宣告式 region pinning 把資料邏輯綁在合規邊界內、application code 不需要重寫。AWS Outposts / Azure Stack 是另一條路徑、把雲服務硬體直接部署到合規邊界（例如美國 sportsbook 跨州合規要求運算留州內）。

跟 [Blast Radius](/backend/knowledge-cards/blast-radius/) 共軸 — 合規邊界常剛好等於 blast radius 邊界、但兩者的決策驅動力不同（合規是法規硬限、blast radius 是失敗影響範圍）。

## 可觀察訊號與例子

需要面對 data residency 的訊號是「monolith 要進歐盟 / 中國 / 巴西市場」、或「金融 / 醫療 / 博弈業要進跨境部署」。對應 case：Standard Chartered Aurora 7 cluster fleet 路徑（銀行業跨國合規邊界、跨市場業務邏輯弱、每市場獨立 cluster 可行）；Hard Rock Wire Act 跨州博弈（跨州統一帳戶 + 跨州 reporting 是核心業務、必須邏輯一個 CockroachDB cluster + locality placement 吸收合規）。同一個 *合規 driver*、不同 *業務需求強度* 推出完全相反的拓樸決策。

## 判斷條件與後果

合規禁止跨境複製時，residency 是一條硬限制，這條限制寫在哪一層，決定它由誰執行。寫在 application code 的 retry 或路由邏輯裡時，每一條程式路徑各自負責遵守，新加的路徑沒有照做就把資料送出邊界；寫進 schema 層或 placement policy（CockroachDB locality、Spanner regional configuration、region-pinned Global Tables）時，由資料庫把資料綁在合規邊界內，application code 不必各自實作。Aurora Global Database 靠 cross-region async replication，資料一旦複製到另一個 region 就違反合規，這類情境下規劃 Aurora migration 時它不在選項裡，替代的拓樸是每個市場一個獨立 cluster。拓樸的選擇由三項條件決定：合規的顆粒（跨國、跨州或跨 AZ）；跨邊界業務邏輯的需求強度，強時（跨州統一帳戶）走 distributed SQL 的 locality placement，弱時走多個獨立 cluster 的 fleet；以及團隊維運得了哪一種形態（一個跨 region 的邏輯 cluster，或多個獨立 cluster）。把 latency 當成主要驅動力時，選到的工具解決的是另一件事：AWS Outposts 的存在動機是 residency，latency 改善只是副作用。
