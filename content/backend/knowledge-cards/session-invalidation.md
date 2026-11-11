---
title: "Session Invalidation"
tags: ["會話失效", "Session Invalidation"]
date: 2026-04-24
description: "說明事件後如何讓既有會話失效，避免被重放或延續利用"
weight: 266
---

Session invalidation 的核心概念是「使既有會話在定義時間內失去可用性」。它是事件收斂的重要步驟，常與存取憑證輪替同時執行。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 跟其他概念的關係

Session invalidation 位在 [authentication](/backend/knowledge-cards/authentication/)、[credential](/backend/knowledge-cards/credential/)、[incident-timeline](/backend/knowledge-cards/incident-timeline/) 與 [runbook](/backend/knowledge-cards/runbook/) 之間。它承接身分事件後的收斂節奏。

## 可觀察訊號與例子

系統需要會話失效機制的訊號是修補完成後仍觀察到可疑會話、異常登入地理分布或持續重放行為。邊界設備事件與 SSO 事件常需要全域會話失效。

## 判斷條件與後果

會話失效的觸發條件、覆蓋範圍、失效時序與驗證方式，各自在安全收斂速度與業務可用性之間取捨。觸發條件沒有涵蓋身分事件時，修補完成後的可疑會話照樣有效；覆蓋範圍只到單一帳號或單一裝置時，邊界設備與 SSO 事件裡其他被盜用的會話還開著，擴到全域時，所有使用者同時被登出，重新登入與客服的負載同時升高；失效有時序延遲（token 到期前仍被接受）時，延遲的長度就是攻擊者還能使用會話的窗口；沒有驗證方式時，無法確認失效之後重放行為已經停止。

委派身分的系統另有一條線：對方停用帳號時這邊預設收不到事件，既有會話與備用登入路徑都還開著，處置見 [7.38 外部身分與本地紀錄](/backend/07-security-data-protection/external-identity-local-record-lifecycle/)。外洩當下撤銷與重設的先後見 [7.37 密碼外洩之後](/backend/07-security-data-protection/credential-breach-response/)。
