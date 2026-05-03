---
title: "8.20 Customer Impact Assessment"
date: 2026-05-02
description: "把受影響用戶、功能、區域、金額、SLO 與補償判斷串成影響評估模型"
weight: 20
---

## 大綱

- customer impact assessment 的責任：把技術症狀轉成用戶與業務影響
- 影響維度：user count、tenant、region、feature、duration、data correctness、financial impact
- 服務維度：availability、latency、data loss、duplicate action、partial degradation
- 證據來源：SLI / SLO、RUM、support ticket、billing event、audit log、status page
- 分級用途：severity、stakeholder update、補償政策、PIR prioritization
- 跟 04 的交接：client-side / synthetic / audit log 提供 impact evidence
- 跟 07 的交接：資料外洩、授權錯誤與合規影響需要分流
- 反模式：只用 server error rate 代表用戶影響；所有客戶用同一句 status update；補償判斷事後人工拼帳

Customer impact assessment 的價值是把工程語言翻成決策語言。事故期間若只看技術指標，團隊容易低估商業影響或高估通訊範圍；impact model 讓分級、通訊與補償使用同一組事實。

## 概念定位

Customer impact assessment 是把事故影響轉成用戶、產品與業務語言的模型，責任是支援分級、通訊、補償與復盤排序。

這一頁處理的是影響量化。事故指標可以從 server 開始，但對外決策需要知道誰受影響、影響多久、影響哪個功能、是否造成資料或金錢後果。

影響量化的重點是可追蹤更新。初版估算可以粗，但要明確標記 confidence 與更新節點，讓 stakeholder 知道哪些是已確認影響、哪些仍在查證。

## 核心判讀

判讀 customer impact 時，先看影響對象與功能，再看影響是否可量化到通訊與補償所需精度。

重點訊號包括：

- affected users / tenants / regions 是否可估算
- affected feature 是否能對應 customer journey
- duration 是否能用 incident timeline 與 SLO 對齊
- data correctness / financial impact 是否需要獨立調查
- status update 是否能反映不同客群的實際影響

| 影響面向 | 最小可用判準                     | 對外決策用途       |
| -------- | -------------------------------- | ------------------ |
| 對象     | users / tenants / regions 可估算 | 分級與客戶通知範圍 |
| 功能     | 對應具體 customer journey        | 狀態頁與客服話術   |
| 時間     | 可對齊 timeline 與 SLO           | 影響期間與恢復宣告 |
| 正確性   | 資料 / 交易是否受損可判定        | 補償與法規通報     |
| 金額     | financial impact 可分層估算      | 補償與商務決策     |

## 判讀訊號

- error rate 很低，但集中在高價值客戶或核心功能
- server-side 指標正常，但 RUM / support ticket 顯示用戶受影響
- 事故結束後才開始計算受影響帳戶
- status page 寫「部分用戶」，內部需要臨場估算部分的範圍
- 補償判斷需要工程臨時產出查詢

實務場景常是 server error rate 不高，但問題集中在高價值客戶或關鍵流程。若 impact assessment 只看平均值，會錯配通訊與補償；若同時看 tenant / feature / value 分佈，決策會更精準。

## 交接路由

- 04.10 client-side / synthetic / RUM：補用戶感知訊號
- 04.12 audit log：補資料與責任證據
- 08.1 severity trigger：把 impact assessment 接入分級
- 08.4 incident communication：提供對外更新內容
- 08.10 stakeholder communication：接 status page 與補償政策
- 07.4 data protection：資料外洩或資料正確性影響分流
