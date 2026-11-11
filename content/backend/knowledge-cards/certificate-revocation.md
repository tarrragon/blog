---
title: "Certificate Revocation"
date: 2026-04-23
description: "說明數位憑證的私鑰洩漏或憑證誤發時如何撤銷並控制影響範圍"
weight: 150
---

Certificate revocation 的核心概念是「在憑證不再可信時快速宣布失效」。常見觸發情境是私鑰洩漏、錯誤簽發、身份資訊不再有效或資安事件需要立即切斷信任。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 跟其他概念的關係

憑證撤銷是 [website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 的事故處理能力，與 [secret management](/backend/knowledge-cards/secret-management/) 與 [audit log](/backend/knowledge-cards/audit-log/) 一起構成憑證風險控制邊界。

## 可觀察訊號與例子

系統需要撤銷流程的訊號是金鑰材料疑似外洩或錯誤部署到不該公開的環境。若缺少撤銷與替換流程，攻擊者可能持續利用舊憑證偽裝服務端點。

## 判斷條件與後果

撤銷流程要判斷的是一張憑證從不再可信，到客戶端不再信任它之間的那段時間有多長。觸發條件（私鑰洩漏、錯誤簽發、身份資訊失效）沒有事先寫定時，發現異常的人要先討論是否該撤銷，這段時間裡持有私鑰的攻擊者仍能用這張憑證偽裝服務端點。責任人沒有指定時，撤銷要等有人出面決定，而撤銷會讓正在用這張憑證的服務出現中斷，這個代價讓沒有被指定的人不會主動下決定。撤銷時新憑證還沒部署好，服務端點在空檔裡出示的是已撤銷的憑證，會檢查撤銷狀態的客戶端拒絕連線；空檔多長取決於替換時序與客戶端影響評估是否事先排好，所以這兩項連同通知依賴方的溝通步驟寫進回復用的 [runbook](/backend/knowledge-cards/runbook/)。金鑰怎麼外洩、憑證為什麼誤發沒有在 [post-incident review](/backend/knowledge-cards/post-incident-review/) 回饋到偵測與輪替策略時，同一種成因會讓下一張憑證再走一次撤銷。

持有者是人而非機器時（企業與政府的智慧卡），撤銷只讓那張憑證失效，卡片還在持有者手上，帳號在其他登入方式上仍然有效，所以撤銷要同時接上實體回收與帳號側的停用，見 [7.39 使用者持有型憑證](/backend/07-security-data-protection/user-held-credential-carrier/)。
