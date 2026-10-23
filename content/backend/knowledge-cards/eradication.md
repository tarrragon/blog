---
title: "Eradication（根除）"
date: 2026-10-22
description: "資安事故止血之後、要決定什麼時候可以把服務帶回來時，查攻擊者留在環境裡的存取憑證、後門與被改過的產物要移除到什麼程度"
weight: 487
tags: ["backend", "security", "incident-response", "eradication"]
---

根除（eradication）是資安事故處理中位於止血之後、回復之前的階段：移除攻擊者在環境裡留下的全部**立足點（foothold）**，也就是他取得的憑證、放置的後門、改過的程式與產物，以及寫進資料裡的帳號與設定。止血（[Containment](/backend/knowledge-cards/containment/)）切斷的是已知的存取路徑，攻擊者手上還沒被發現的憑證在止血之後仍然可用，所以資安事故在止血與回復之間多出這一段；運維事故的故障原因不會主動尋找新的路徑，通常沒有這一段。NIST SP 800-61 Rev. 2 把這一段與止血、回復合稱 Containment, Eradication, and Recovery。

## 概念位置

根除的範圍由攻擊者可能碰過的憑證、系統、資料與產物決定，而那份清單從被入侵元件的權限推出：它手上的憑證、憑證與網路連得到的系統、它建置的產物、它能讀寫的程式碼與資料。攻擊者從被入侵的元件往外擴散的方式見 [Lateral Movement（橫向移動）](/backend/knowledge-cards/lateral-movement/)；辨認同一個攻擊者是否回來的特徵見 [Indicator of Compromise（入侵指標）](/backend/knowledge-cards/indicator-of-compromise/)。

## 可觀察訊號與例子

一台 CI 建置主機被入侵：止血是斷開它的對外連線、停用已知外洩的帳號；根除是撤銷它手上全部的憑證、用入侵之前的設定與映像重建一台新主機、重建入侵期間的產物、移除攻擊者在資料庫或雲端帳號裡新增的帳號與金鑰。根除沒有做完就宣告事故解除時，常見的後果是同一個攻擊者用一把清查時沒列到的憑證再進來一次。

## 設計責任

根除要寫成可查核的完成條件：清查清單上的每一項是否已處置、處置方式是什麼、哪些項目做不到並寫明理由。被入侵的主機以重建取代清理，因為刪掉找到的檔案證明不了攻擊者沒有放別的檔案。完整的清查範圍、重建來源與憑證撤銷順序見 [8.25 建置主機被入侵後的根除與重建](/backend/08-incident-response/compromised-build-host-eradication/)。
