---
title: "Game Day"
date: 2026-04-23
description: "說明事故演練如何驗證流程、工具與團隊協作"
weight: 164
---

Game day 的核心概念是「在受控環境模擬故障並演練處置流程」。它用實際操作驗證告警、分級、指揮、回滾與通訊是否真的可用。 可先對照 [On-Call](/backend/knowledge-cards/on-call/)。

## 跟其他概念的關係

Game day 是 [on-call](/backend/knowledge-cards/on-call/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 的訓練場景。它把文件假設轉成可觀察行為與量化結果。

## 可觀察訊號與例子

系統需要 game day 的訊號是流程文件完整但實戰仍常卡住。團隊可在預備環境模擬 broker 中斷、database 延遲、存取憑證失效或 TLS 憑證過期，觀察 MTTR 與升級節奏是否符合預期。

## 判斷條件與後果

Game day 的判斷對象是演練結束後拿得出什麼結論。沒有成功標準時，MTTR 與升級節奏量到了，也無從判定是否符合預期；沒有安全邊界時，在預備環境模擬的 broker 中斷或憑證失效可能波及正式流量；沒有紀錄方式與復盤輸出時，演練中卡住的步驟不會變成 runbook 或流程的修改，下一次實戰在同一個步驟再卡一次。演練範圍只有單一團隊時，告警、分級與指揮在團隊內各自順利，跨角色的溝通與決策節點仍然沒有被驗證過，原因是單一團隊的演練裡沒有需要交接的對象。
