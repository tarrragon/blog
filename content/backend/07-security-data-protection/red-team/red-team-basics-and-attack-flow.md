---
title: "7.R0 紅隊基礎：攻擊流程作為服務判讀語言"
date: 2026-04-24
description: "建立紅隊共同詞彙與流程視角，讓案例分析回到服務環節的決策判讀"
weight: 710
---

本章的責任是提供一套共用判讀語言，讓團隊在討論案例時先對齊服務環節與風險節奏。紅隊在本教材中的定位是攻擊者視角的風險檢查方法，核心輸出是問題地圖與注意事項，並把防護實作需求路由到對應服務章節。

## 服務視角定位

紅隊分析把事件拆回服務生命週期，目標是回答三件事：入口在哪裡、擴散怎麼發生、衝擊如何形成。這個拆法讓架構設計、事故處理、案例引用可以使用同一組語言。

## 攻擊流程六段判讀

1. 偵察：攻擊者先看見可達入口與可枚舉資源。
2. 初始進入：攻擊者取得第一個可操作落點。
3. 權限擴張與持續控制：攻擊者提升可操作範圍並維持進入能力。
4. 橫向移動：攻擊者沿著服務邊界進入其他系統。
5. 目標行動：攻擊者進行資料蒐集、外送或營運衝擊。
6. 掩護與延長停留：攻擊者降低被發現機率並延長影響期。

## 服務環節問題地圖（觀念層）

| 服務環節 | 主要問題 | 注意事項 | 優先案例 |
| --- | --- | --- | --- |
| 身分與授權 | 入口驗證通過後仍可快速擴散 | 高風險動作需要獨立判讀節奏 | [Uber 2022](cases/identity-access/uber-2022-mfa-fatigue/)、[Twilio 2022](cases/identity-access/twilio-2022-social-engineering/) |
| 第三方整合 | 供應商事件可直接傳導到內部流程 | 事件觸發與憑證收斂需要同一條路由 | [Okta + Cloudflare 2023](cases/identity-access/okta-cloudflare-2023-support-supply-chain/)、[GitHub OAuth 2022](cases/supply-chain/github-oauth-2022-token-supply-chain/) |
| 邊界與入口 | 暴露面與修補窗口同時放大風險 | 入口隔離、分區修補、狀態驗證要同時規劃 | [Ivanti 2024](cases/edge-exposure/ivanti-2024-vpn-chain/)、[PAN-OS 2024](cases/edge-exposure/panos-cve-2024-3400-edge-rce/) |
| 交付與供應鏈 | 合法交付路徑可被反向利用 | 凍結、驗證、恢復需要明確順序 | [SolarWinds 2020](cases/supply-chain/solarwinds-2020-sunburst/)、[TeamCity 2024](cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/) |
| 資料與回復 | 外送風險與營運衝擊常同時出現 | 資料盤點、回復排序、通報節奏需要連動 | [Snowflake 2024](cases/data-exfiltration/snowflake-2024-credential-abuse/)、[Change Healthcare 2024](cases/data-exfiltration/change-healthcare-2024-ops-impact/) |

## 與其他章節的分工路由

- 本章與 `7.R6`、`7.R7`：提供問題判讀與案例證據。
- `backend/05-deployment-platform`：承接交付鏈與入口流量治理的實作。
- `backend/06-reliability`：承接回復排序與可用性設計的實作。
- `backend/08-incident-response`：承接事故分級、指揮、runbook 落地。

這個分工維持教材一致性：紅隊章節先回答「問題長什麼樣」，服務章節再回答「實際怎麼做」。

## 下一步

進入 [7.R6 事故故事：服務環節問題與注意事項](../incident-stories-by-attack-stage/) 之後，會把每個環節拆成可直接引用的判讀訊號與決策提醒。
