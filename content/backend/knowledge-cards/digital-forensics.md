---
title: "Digital Forensics（數位鑑識）"
date: 2026-10-23
description: "資安事故要決定被入侵主機關機或重建之前先保全什麼、內部紀錄不夠時何時委託外部鑑識，或要判斷一份調查結論是否足以作為對外說明的依據時，查數位鑑識保全哪些證據、證據的保管鏈要記什麼"
weight: 493
tags: ["backend", "security", "incident-response"]
---

Digital forensics（數位鑑識）是以事後能被第三方檢驗的方式取得、保存與分析電子證據，用來重建入侵經過：攻擊者從哪裡進來、做了什麼、碰過哪些資料。它與事故處理同時進行而目的不同：止血（[Containment](/backend/knowledge-cards/containment/)）與根除（[Eradication](/backend/knowledge-cards/eradication/)）要盡快改變系統狀態，鑑識要在系統狀態被改變之前把證據留下來。

## 概念位置

鑑識取得的每一份證據都要記保管鏈（chain of custody）：誰在什麼時間從哪裡取得、用什麼方式複製、複本的雜湊值、之後經過誰的手，第三方才能確認證據沒有被改過。擷取的先後由資料的揮發程度決定（order of volatility）：記憶體、執行中的程序與網路連線在關機後就消失，要先取；磁碟映像與雲端的稽核紀錄之後仍取得到。鑑識結論常見的內容是 [Indicator of Compromise（入侵指標）](/backend/knowledge-cards/indicator-of-compromise/) 與攻擊者在環境裡的時間範圍（[Dwell Time](/backend/knowledge-cards/dwell-time/)）。

## 可觀察訊號與例子

建置主機被入侵之後，舊主機斷網保留、不接回網路，事故處理團隊在關機前擷取記憶體與網路連線，再做磁碟快照，服務改由另外重建的主機承接。平台自己的紀錄不足以判斷外洩是否經由平台這一側發生時（資料庫的查詢紀錄沒有開啟、攻擊者用合法存取憑證查詢），平台委託外部鑑識：攻擊工具的特徵、外洩資料流通的情報在外部鑑識團隊手上，不在平台自己的紀錄裡。

## 設計責任

事前要決定由誰擷取證據、證據存放在哪裡、誰能存取，以及什麼條件下委託外部鑑識；事中的處置動作（重開機、重建主機、刪除攻擊者建立的帳號）要先確認相關證據已經保全。調查報告與對外說明要寫明結論來自外部鑑識還是內部調查、兩者是否一致。被入侵主機的保全與重建見 [8.25 建置主機被入侵後的根除與重建〈被入侵主機與入侵期間產物的處置〉](/backend/08-incident-response/compromised-build-host-eradication/#被入侵主機與入侵期間產物的處置)，外洩來源判斷不了時委託外部鑑識的時機見 [8.26 資料外洩時對商家的通知](/backend/08-incident-response/security-incident-customer-notification/)。
