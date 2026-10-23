---
title: "Internal Admin Tool（客服後台）"
date: 2026-10-23
description: "設計讓客服以帳號或訂單編號查使用者資料的內部頁面、決定它顯示哪些欄位與留下什麼紀錄，或讀到 support tooling、admin tool、back office 這些名稱要確認它們是否指同一種工具時，查客服後台的讀寫範圍、權限與稽核責任，以及它與管理端點、代登入的分界"
weight: 495
tags: ["backend", "security", "incident-response"]
---

Internal admin tool（客服後台）是只給公司內部人員使用的網頁介面：客服輸入使用者的帳號、email 或訂單編號，查出那一位使用者的訂單、付款狀態、登入紀錄與最近的錯誤，用來查證使用者回報的狀況，一線客服因此不必請工程去查資料庫。這一類工具在業界沒有單一固定名稱，internal admin tool、support tooling、support console、back office tool 指的都是它，本站寫作客服後台。Okta、Keycloak 這類產品自己的 admin console 是設定那個產品的介面，不是這裡說的工具。客服後台以讀取為主，少數會改資料的操作（停用帳號、退款、改方案）背後呼叫的是 [Admin Endpoint（管理端點）](/backend/knowledge-cards/admin-endpoint/)。

## 概念位置

在 [Tiered Support（分層支援）](/backend/knowledge-cards/tiered-support/) 裡，客服後台決定一則回報是否停在一線：客服查得到那一筆資料的狀態，就能當場答覆；查不到，回報就要轉給工程。它與兩個相鄰的概念分工不同。管理端點負責改資料，客服後台上的寫入按鈕只是它的入口，核准與稽核的要求跟著端點走。代登入（impersonation）讓客服以使用者的身分登入產品，看到的畫面與權限和該使用者相同，涵蓋整個產品；客服後台只顯示挑出來、遮罩過的欄位，查得到的範圍比代登入窄。代登入的授權邊界見 [7.2 身分與授權邊界〈代理操作的授權邊界〉](/backend/07-security-data-protection/identity-access-boundary/#代理操作的授權邊界)。

## 可觀察訊號與例子

需要客服後台的訊號是轉給工程的單裡，常有不少只是請工程查一筆資料的狀態（這個短碼是否過期、這個月有沒有扣款），工程查完回覆一句話就結案。短網址服務的例子：客服以短碼查到它的狀態、原始網址、到期日與檢舉紀錄，以帳號查到方案、本月剩餘額度與本期的扣款紀錄；email 與姓名不顯示，卡號只顯示末四碼（欄位與權限的完整設計見 [11.16 面向終端使用者的錯誤碼與請求編號〈客服查詢工具的權限〉](/backend/11-api-design/end-user-error-code-and-reference-id/#客服查詢工具的權限)）。

客服後台讀得到全部客戶的資料，所以它也是攻擊者的目標。Mailchimp 在 2023 年 1 月公告，攻擊者以社交工程取得員工的帳號密碼，進入客服與帳號管理工具，存取了特定客戶的帳號（見 [Mailchimp 2023 支援工具路徑](/backend/07-security-data-protection/red-team/cases/data-exfiltration/mailchimp-2023-support-tool-abuse/)）；同年 Okta 的客服支援系統被入侵，風險從支援系統擴散到客戶的租戶（見 [Okta 支援系統事件](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)）。兩起事件裡攻擊者的每一次操作都經過正常的權限檢查，權限檢查分不出合法的客服查詢與攻擊者的查詢。

## 設計責任

設計客服後台時要決定讀寫範圍、欄位、查詢的理由與紀錄。讀寫範圍：預設只讀，寫入操作逐項列出並走管理端點的核准流程。欄位：只顯示客服答覆需要的欄位，個人資料與付款資訊做欄位層級的遮罩（見 [Data Masking（資料遮罩）](/backend/knowledge-cards/data-masking/)）。查詢的理由：查詢附上還在處理中的客服單號，結案的單號解不開查詢，每一次查詢因此都有理由與有效期間。紀錄：誰、什麼時間、以哪一張單、查了哪個帳號都寫進 [Audit Log（稽核紀錄）](/backend/knowledge-cards/audit-log/)，並對每個客服帳號的查詢量設告警，查詢量突然升高的帳號可能已經被盜用。客服帳號本身依 [Least Privilege（最小權限）](/backend/knowledge-cards/least-privilege/) 只給它負責的範圍。

多租戶平台另外要決定客服後台一次能查幾個租戶：查詢限縮到每次一個租戶、批次匯出要第二人核准，見 [7.44 多租戶平台的隔離層級〈存取層的隔離〉](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/#存取層的隔離建置管線共用運算營運後台內部工具平台資料庫管理備份與其他共用元件的權限範圍)。客服拿查詢結果當場答覆使用者的流程，見 [8.24 客服回報的處理〈客服當場答覆時用的資訊〉](/backend/08-incident-response/support-escalation-and-engineering-reply/#客服當場答覆時用的資訊)。
