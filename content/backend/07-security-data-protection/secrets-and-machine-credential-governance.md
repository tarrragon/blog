---
title: "7.6 秘密管理與機器憑證治理"
date: 2026-04-24
description: "用服務環節視角整理 secret、token、key 與機器憑證治理的問題與注意事項"
weight: 76
---

本章的責任是建立秘密管理與機器憑證治理的判讀框架。核心輸出是分域策略、生命周期邊界與事件收斂路由，讓機器身份風險可在實作前被明確切分。

## 服務環節問題地圖

| 環節 | 主要問題 | 注意事項 | 優先案例 |
| --- | --- | --- | --- |
| 第三方 token 鏈 | 供應商節點事件可直接擴散 | token 分域與撤銷節奏要可回查 | [GitHub OAuth 2022](red-team/cases/supply-chain/github-oauth-2022-token-supply-chain/) |
| CI secrets 集中 | 集中 secrets 提高單點風險 | 事件時需要分批輪替與優先順序 | [CircleCI 2023](red-team/cases/supply-chain/circleci-2023-secrets-rotation/) |
| 支援流程憑證 | 支援事件會傳導到內部憑證 | 外部事件要觸發內部憑證收斂 | [Cloudflare 2023](red-team/cases/identity-access/cloudflare-2023-okta-token-follow-through/) |
| 機器憑證生命周期 | 發放與淘汰節奏不一致 | 生命周期節奏要與事件節奏對齊 | [Storm-0558 2023](red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) |

第三方 token 鏈的責任是限制外部信任擴散。這個環節的判讀重點是 token 範圍與撤銷時序。

CI secrets 集中的責任是維持交付可用性與收斂速度平衡。這個環節的判讀重點是分層輪替策略與依賴盤點完整度。

支援流程憑證的責任是縮短事件傳導窗口。這個環節的判讀重點是外部公告到內部收斂的節奏。

機器憑證生命周期的責任是維持機器身份可控性。這個環節的判讀重點是發放、輪替、撤銷的一致性。

## 判讀訊號

- [secret-management](../knowledge-cards/secret-management/) 事件與分域策略差異。
- [credential](../knowledge-cards/credential/) 撤銷與輪替完成時間差。
- 高風險 token 的用途分域與實際使用差異。
- 外部事件後內部憑證收斂覆蓋率。

## 風險邊界

秘密治理的核心風險是可用憑證存量高於收斂速度。當分域與生命周期失去一致節奏，攻擊者可沿機器身份路徑延長事件影響。

## 下一步路由

- 交付與執行環境實作： [模組五：部署平台與網路入口](../05-deployment-platform/)
- 事件收斂流程： [模組八：事故處理與復盤](../08-incident-response/)

## 大綱

- 憑證分類：human credential、service credential、ephemeral token
- 分域策略：用途分域、環境分域、權限分域
- 生命周期治理：發放、更新、撤銷、淘汰
- 事件收斂：供應商事件後的輪替與盤點節奏
