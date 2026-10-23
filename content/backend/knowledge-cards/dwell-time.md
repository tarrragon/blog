---
title: "Dwell Time（攻擊者駐留時間）"
date: 2026-10-23
description: "資安事故要估攻擊者在被發現之前待了多久、清查與鑑識要往回追溯到哪一天，或要解讀入侵報告裡的駐留時間中位數時，查這段時間從哪一刻算到哪一刻、它怎麼決定清查範圍"
weight: 492
tags: ["backend", "security", "incident-response"]
---

Dwell time（攻擊者駐留時間）是攻擊者最初進入環境，到防守方偵測到入侵之間經過的時間。網站分析裡也有一個 dwell time，指使用者在頁面上停留多久，與這裡的意思無關。駐留時間越長，攻擊者讀過的程式碼、拿到的存取憑證與佈下的立足點越多，根除（[Eradication](/backend/knowledge-cards/eradication/)）要清查的範圍跟著變大。

## 概念位置

駐留時間的起點在偵測當下通常還不知道：事故處理團隊要從 [Indicator of Compromise（入侵指標）](/backend/knowledge-cards/indicator-of-compromise/) 與存取紀錄往回追溯到最早的一筆攻擊者活動，才定得出來；在那之前，清查與[數位鑑識](/backend/knowledge-cards/digital-forensics/)要涵蓋的期間取能證明的最早時間點。駐留時間停在偵測的那一刻，偵測之後的處理到恢復花了多久，由 [MTTR](/backend/knowledge-cards/mttr/) 這類指標量。

## 可觀察訊號與例子

一台 CI 建置主機在被發現之前已被入侵三週：這三週裡建出的每一個產物、主機讀得到的每一把憑證與每一份原始碼都要列進清查清單，而不只看發現當天的狀態。資安廠商的年度入侵報告以駐留時間的中位數衡量防守方的偵測能力，那個數字的定義是從入侵到偵測，不含之後的處置時間（素材見 [Mandiant M-Trends](/backend/07-security-data-protection/blue-team/materials/professional-sources/mandiant-m-trends-defender-pressure/)）。

## 設計責任

事故紀錄要分開記下最早的攻擊者活動時間、偵測時間與止血時間，駐留時間才算得出來，清查也才知道要追溯到哪一天。紀錄的保留期短於駐留時間時，最早那一段的活動查不到，清查清單與對外宣告都要寫明這個缺口。建置主機被入侵時，駐留時間怎麼影響清查範圍與多波攻擊的監看，見 [8.25 建置主機被入侵後的根除與重建](/backend/08-incident-response/compromised-build-host-eradication/)。
