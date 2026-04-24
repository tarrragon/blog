---
title: "7.2 身分與授權邊界"
date: 2026-04-24
description: "用服務環節視角整理身份、授權、會話與供應商身分鏈的問題與注意事項"
weight: 72
---

本章的責任是建立身分與授權邊界的判讀框架。核心輸出是判讀訊號、風險邊界、注意事項與案例路由，讓不同服務實體能用同一套語言對齊決策。

## 服務環節問題地圖

| 環節 | 主要問題 | 注意事項 | 優先案例 |
| --- | --- | --- | --- |
| 登入與初始驗證 | 入口成功後可快速擴散 | 高風險動作需要獨立事件節奏 | [Uber 2022](red-team/cases/identity-access/uber-2022-mfa-fatigue/) |
| 內部工具授權 | 角色存在但擴散路徑過寬 | 內部管理工具需要分層授權 | [MGM 2023](red-team/cases/identity-access/mgm-2023-identity-lateral-impact/) |
| 供應商身分鏈 | 第三方事件可傳導到內部 | 供應商事件要直接觸發收斂流程 | [Okta + Cloudflare 2023](red-team/cases/identity-access/okta-cloudflare-2023-support-supply-chain/) |
| 會話與 token | 修補後會話仍可被利用 | 會話失效與憑證輪替要同步執行 | [Citrix Bleed 2023](red-team/cases/edge-exposure/citrix-bleed-2023-session-hijack/) |

登入與初始驗證的責任是提供第一層邊界。這個環節的判讀重點是異常登入密度、跨地區登入節奏與高風險操作接續模式。

內部工具授權的責任是限制擴散速度。這個環節的判讀重點是高權限能力集中度與代理操作路徑。

供應商身分鏈的責任是縮短傳導窗口。這個環節的判讀重點是外部事件到內部收斂的時間差。

會話與 token 的責任是管理持續存取邊界。這個環節的判讀重點是事件後會話失效覆蓋與 token 生命周期分域。

## 判讀訊號

- [authentication](../knowledge-cards/authentication/) 異常密度與重複驗證模式。
- [authorization](../knowledge-cards/authorization/) 與角色邊界跨越次數。
- 高風險管理功能的連續操作與代理操作模式。
- 第三方事件後內部 token 與 session 收斂進度。

## 風險邊界

身分邊界的核心風險是擴散速度快於判讀速度。當事件節奏落後，攻擊者可沿著合法身份樣態擴大可操作範圍。

## 下一步路由

- 身分事件轉 runbook： [8.8 事故報告轉 workflow](../08-incident-response/incident-report-to-workflow/)
- 邊界入口與網路實體設計： [部署平台與網路入口](../05-deployment-platform/)
- 可用性與回復節奏： [模組六：可靠性](../06-reliability/)

## 大綱

- 身分邊界模型：人員、服務帳號、機器憑證
- 權限擴散路徑：角色模型與代理操作
- 供應商身分鏈：事件傳導與收斂節奏
- 會話與 token：生命周期、失效與回查
