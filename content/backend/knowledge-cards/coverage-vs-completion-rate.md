---
title: "Coverage vs Completion Rate（覆蓋率與完成率）"
tags: ["backend", "knowledge-card", "observability", "governance"]
date: 2026-08-17
description: "說明同一個百分比的分母由誰列舉，決定它衡量的是全體的覆蓋率還是管理範圍內的完成率"
weight: 440
---

Coverage 與 completion rate 的核心區別是分母由誰列舉：**完成率的分母是被某個系統管理的那批，覆蓋率的分母是實際存在的全體**。同一個百分比因此可以長期接近滿分而與風險無關——分母由執行這項工作的工具自己列舉時，它衡量的是「工具管的那些做完了沒有」，不是「該做的都做了沒有」。 可先對照 [Data Completeness](/backend/knowledge-cards/data-completeness/)。

## 概念位置

這個區別位在 [metrics](/backend/knowledge-cards/metrics/)、[SLI / SLO](/backend/knowledge-cards/sli-slo/) 與 [known gap](/backend/knowledge-cards/known-gap/) 之間：指標定義決定算什麼、SLO 決定門檻、而分母的來源決定這個數字承載的是哪一個命題。它與 [data completeness](/backend/knowledge-cards/data-completeness/) 的對象不同——那張卡問資料本身夠不夠完整，這裡問的是比例的母體從哪裡來。

判讀的問法只有一句：**這個數字是從哪裡數出來的**。答案是某個工具的清單、某張登記表或某個自動化系統的作業範圍時，拿到的是完成率；要得到覆蓋率，分母必須來自不受該系統影響的獨立來源。

## 可觀察訊號與例子

訊號是完成率長期接近滿分而同類事故仍在發生。憑證輪替是最典型的形態：自動續期導入時涵蓋的是當時看得到的那批，之後完成率一直是滿分，而手動放進設定檔或燒進映像檔的那幾張從未進入分母——[7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/) 展開這個形態並給出三份獨立來源（外部連線側掃描、設定反推、簽發側列舉）。

治理指標有同構的形態：例外關閉率的分母是登記過的例外，沒登記的不在分母裡，所以這個數字與治理品質可以無關（見 [7.25 資安成熟度的組織節奏](/backend/07-security-data-protection/security-maturity-organization-cadence/) 的指標段）。偵測側的誤報率也一樣——關掉噪音大的規則會改善它，而被關掉的規則涵蓋的攻擊路徑不出現在任何分母裡。

## 設計責任

每個對外報告的百分比要標分母的來源，而不只標算法。分母來自被量測系統自己時，指標旁邊要寫明它衡量的範圍；要把完成率升級成覆蓋率，要先建立一份獨立列舉，而獨立來源通常不只一份（各自有可達性限制，差集才是缺口）。獨立來源建不出來時，誠實的做法是把這個數字標成完成率並記一筆 [known gap](/backend/knowledge-cards/known-gap/)，而不是讓它以覆蓋率的名義進入儀表板或稽核報告。
