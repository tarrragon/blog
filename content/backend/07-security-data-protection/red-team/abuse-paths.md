---
title: "7.R2 入口濫用與權限突破"
date: 2026-04-24
description: "說明合法功能如何被惡意組合成權限突破或流程濫用"
weight: 712
---

Abuse case 的核心概念是「攻擊者不一定要繞過入口，他也可能直接濫用合法功能」。紅隊關注的不是單一 API 是否存在，而是這個功能是否可以被重新排列成未授權操作、越權動作或流程欺騙。

## 概念位置

Abuse case 會落在 [authentication](../../knowledge-cards/authentication/)、[authorization](../../knowledge-cards/authorization/)、[BOLA / IDOR](../../knowledge-cards/bola-idor/)、[Function-Level Authorization](../../knowledge-cards/function-level-authorization/)、[Tenant Boundary](../../knowledge-cards/tenant-boundary/) 與 [Least Privilege](../../knowledge-cards/least-privilege/) 的交界。它關心的是合法行為如何被轉成非預期結果，例如邀請、重設、匯出、審核、切換或分享流程。

## 可觀察訊號與例子

系統需要 abuse case 檢查的訊號是功能很多、流程很長、角色很多，或有明顯的例外分支。像是匯出功能被用來批量蒐集資料、邀請流程被用來擴張不該有的存取、重設流程被用來接管帳號，這些都不是「攻擊碼」，而是「合法功能被惡意轉用」。

## 設計責任

防護要能回答三件事：這個功能的正常目的為何、它可能被怎麼濫用、濫用時系統要在哪一層攔下來。若流程本身包含權限跳轉、狀態切換或代理操作，紅隊就會把這些地方當成第一優先的濫用路徑。
