---
title: "Abuse Case"
date: 2026-04-24
description: "說明合法功能如何被惡意轉用成突破或濫用路徑"
weight: 125
---

Abuse case 的核心概念是「功能本來合法，但可能被攻擊者重新組合成非預期用途」。它和 threat model 的差別在於，abuse case 更關心具體的惡意使用情境，而不是抽象風險分類。

## 概念位置

Abuse case 會落在 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[BOLA / IDOR](/backend/knowledge-cards/bola-idor/)、[Function-Level Authorization](/backend/knowledge-cards/function-level-authorization/)、[Least Privilege](/backend/knowledge-cards/least-privilege/) 與 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的交界。常見場景包含 export、invite、reset、approval、trial、switch、share 與 automation。

## 可觀察訊號與例子

如果一個功能有很多例外分支、角色切換或長流程，紅隊就會把它視為可濫用面。像是匯出功能被用來批量蒐集資料、邀請流程被用來擴張不該有的存取、重設流程被用來接管帳號，這些都是 abuse case。

## 設計責任

防護要能回答三件事：正常目的為何、可能被怎麼濫用、濫用時要在哪一層攔下來。若流程本身包含權限跳轉、狀態切換或代理操作，這些地方就應該優先被列為 abuse case。
