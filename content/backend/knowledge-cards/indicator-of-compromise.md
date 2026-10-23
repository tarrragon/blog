---
title: "Indicator of Compromise（入侵指標）"
date: 2026-10-22
description: "要從日誌與流量判斷某個攻擊者是否活動過、或根除之後是否回來時，查哪些可觀察的特徵能把同一個攻擊者的活動認出來"
weight: 488
tags: ["backend", "security", "incident-response", "detection"]
---

入侵指標（indicator of compromise，常縮寫為 IOC）是能在日誌、流量與主機上辨認出某一個攻擊者活動的可觀察特徵：來源 IP 位址、網域、檔案雜湊值、工具與惡意程式的特徵、特定的請求形態。事故處理團隊從已確認的入侵裡整理出這些特徵，用來回頭搜尋同一個攻擊者還碰過哪些系統，以及在根除之後設成告警，偵測他是否再次進入。可先對照 [Eradication（根除）](/backend/knowledge-cards/eradication/)。

## 概念位置

入侵指標是偵測規則的一種輸入，它針對的是一個已知攻擊者的具體痕跡；針對攻擊手法的行為偵測（例如一台主機向平常不連的位址發起連線，見 [Lateral Movement（橫向移動）](/backend/knowledge-cards/lateral-movement/)）不依賴已知的特徵。攻擊者換一個來源位址或換一套工具，入侵指標就比對不到，所以只靠入侵指標的監看攔不住從另一個入口進來的同一個攻擊者。

## 可觀察訊號與例子

CI 建置主機被入侵之後，事故處理團隊從主機外的連線紀錄整理出攻擊者用過的來源位址與下載過的工具雜湊，在防火牆與端點偵測裡設成告警。根除完成後的監看期內，這組告警沒有觸發只證明同一組特徵沒有再出現；攻擊者若用第一波讀到的內部端點與金鑰從別的入口進來，要靠「已輪替的舊金鑰被嘗試使用」「被讀過的內部端點出現異常存取」這類以第一波資訊為對象的告警才看得到。

## 設計責任

入侵指標要記下來源、取得時間與有效範圍，並在偵測規則裡標明它屬於哪一次事故，事故結束後依規則的生命週期檢討是否保留。告警怎麼併進既有偵測規則見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)；根除之後的監看與它的結束條件見 [8.25 建置主機被入侵後的根除與重建](/backend/08-incident-response/compromised-build-host-eradication/)。
