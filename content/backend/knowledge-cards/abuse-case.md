---
title: "Abuse Case"
date: 2026-04-24
description: "說明合法功能如何被惡意轉用成突破或濫用路徑"
weight: 126
---

Abuse case 的核心概念是「功能本來合法，但可能被攻擊者重新組合成非預期用途」。它和 [threat model](/backend/knowledge-cards/threat-model/) 的差別在於，abuse case 更關心具體的惡意使用情境，而不是抽象風險分類。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 跟其他概念的關係

Abuse case 會落在 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[BOLA / IDOR](/backend/knowledge-cards/bola-idor/)、[Function-Level Authorization](/backend/knowledge-cards/function-level-authorization/)、[Least Privilege](/backend/knowledge-cards/least-privilege/) 與 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的交界。常見場景包含 export、invite、reset、approval、trial、switch、share 與 automation。

## 可觀察訊號與例子

如果一個功能有很多例外分支、角色切換或長流程，紅隊就會把它視為可濫用面。像是匯出功能被用來批量蒐集資料、邀請流程被用來擴張不該有的存取、重設流程被用來接管帳號，這些都是 abuse case。

## 判斷條件與後果

一項功能的防護寫得出它的正常目的、可能被怎麼重新組合、濫用時由哪一層攔下時，濫用情境才有對應的檢查點；只寫得出正常目的時，防護只驗證正常路徑，匯出、邀請、重設這類功能被重新組合時沒有任何一層攔下，原因是組合裡的每一步單獨看都是合法請求。流程裡有權限跳轉、狀態切換或代理操作（替另一個身分執行動作）時，攻擊者能在步驟之間換掉身分或操作對象，這些位置是 abuse case 最常出現的地方，所以盤點從它們開始。
