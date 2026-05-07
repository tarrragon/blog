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

## 影響維度

Customer impact assessment 的影響維度要同時描述誰受影響、哪個功能受影響、影響多久，以及是否形成資料或金錢後果。

| 維度              | 核心問題                       | 常見資料來源                       |
| ----------------- | ------------------------------ | ---------------------------------- |
| User / Tenant     | 哪些用戶、租戶、客群受影響     | account metadata、support ticket   |
| Region / Channel  | 哪些區域、裝置、入口受影響     | RUM、CDN、mobile crash、region tag |
| Feature / Journey | 哪個 customer journey 受影響   | SLI、product analytics、trace      |
| Duration          | 影響從何時開始、何時結束       | incident timeline、SLO window      |
| Data correctness  | 資料是否遺失、重複、錯誤或延遲 | audit log、reconciliation          |
| Financial impact  | 是否影響交易、收費、補償或 SLA | billing event、order system        |

User / tenant 維度能避免平均值誤導。低比例錯誤若集中在高價值 tenant、企業客戶或關鍵市場，severity 與 stakeholder update 都需要提升精度。

Region / channel 維度能定位擴散範圍。單一区域、mobile-only、browser-specific、CDN edge 或 VPN / enterprise network 問題，對通訊與修復路由有不同影響。

Feature / journey 維度能把技術症狀轉成產品語言。`API 5xx` 對外仍需要翻成 login、checkout、upload、search、report export 或 webhook delivery 等使用者旅程。

Data correctness 維度需要獨立於 availability 判讀。服務可用但資料重複、漏寫、錯帳或延遲時，customer impact 通常比 error rate 更嚴重。

Financial impact 維度需要和商務與法務協作。交易失敗、重複扣款、SLA credit、補償政策與合約通知，都需要更嚴謹的 evidence chain。

## 服務影響類型

Customer impact assessment 需要把技術症狀映射到服務影響類型。這個映射能讓 severity、communication 與 compensation 使用一致語言。

| 服務影響類型        | 技術樣貌                           | 對外語言                         |
| ------------------- | ---------------------------------- | -------------------------------- |
| Availability loss   | 5xx、timeout、login failure        | 用戶功能不可用                   |
| Latency degradation | p95 / p99 上升、queue lag          | 功能變慢或處理延遲               |
| Data delay          | replication lag、index stale       | 顯示資料較舊或更新延遲           |
| Data inconsistency  | duplicate、missing、wrong value    | 資料可能不正確，需要校驗         |
| Duplicate action    | retry / replay 造成重複副作用      | 可能重複通知、重複交易或重複任務 |
| Partial degradation | fallback、read-only、load shedding | 部分功能暫停或降級               |

Availability loss 是最容易分級的影響類型。它通常可以直接對應 SLO、status page 與客服話術。

Latency degradation 需要時間窗與使用者旅程。短時間 p99 上升可能只影響少數操作，也可能造成交易超時或 queue backlog，因此需要搭配 customer journey 判讀。

Data delay 常被低估。search index、reporting、notification、read model 或 cache projection 延遲時，用戶看到的是資料更新延遲。

Data inconsistency 需要更高 evidence 標準。它可能牽涉合規、金額、客戶信任與後續修復，因此要接 audit log、reconciliation 與 [decision log](/backend/knowledge-cards/incident-decision-log/)。

Duplicate action 需要補償視角。retry、replay 或 idempotency 缺口造成的重複副作用，可能需要退款、撤銷通知、資料修復或客戶通知。

## 判讀訊號

- error rate 很低，但集中在高價值客戶或核心功能
- server-side 指標正常，但 RUM / support ticket 顯示用戶受影響
- 事故結束後才開始計算受影響帳戶
- status page 寫「部分用戶」，內部需要臨場估算部分的範圍
- 補償判斷需要工程臨時產出查詢

實務場景常是 server error rate 不高，但問題集中在高價值客戶或關鍵流程。若 impact assessment 只看平均值，會錯配通訊與補償；若同時看 tenant / feature / value 分佈，決策會更精準。

## Assessment 流程

Customer impact assessment 的流程是從技術證據走向對外決策。第一版可以粗，後續要隨 evidence 更新。

1. 從 incident intake 取得 source、time、feature 與初始 impact。
2. 用 SLI / SLO、RUM、support ticket 與 product analytics 估算 affected scope。
3. 標示 confidence：estimated、confirmed、reconciled。
4. 把 impact 分層：internal-only、limited customers、broad customer impact、regulated / financial impact。
5. 輸出 severity、status update、stakeholder update 與 compensation input。

Estimated 代表初估。事故早期可以使用 error rate、ticket 數、synthetic probe 或抽樣資料先估範圍，但要標示限制。

Confirmed 代表已有多來源證據對齊。當 server-side、client-side、support 與 product data 指向同一範圍，impact assessment 就能支援對外通訊。

Reconciled 代表事後完成精算。補償、SLA credit、資料修復與 PIR 通常需要 reconciled impact，並把事中估算作為對照。

## 通訊與補償

Customer impact assessment 是 stakeholder communication 與補償判斷的輸入。通訊需要足夠早，補償需要足夠準。

Status update 應描述使用者可理解的功能影響。`database CPU high` 應翻成 `部分用戶建立報表延遲` 或 `部分 API request 回應變慢`。

Stakeholder update 應描述範圍、信心與下一次更新時間。若影響仍在估算，應明確說明目前 confidence 與正在補的 evidence。

Compensation input 應接到可重算資料。affected users、duration、transaction amount、SLA tier、data correctness 與 customer segment 都應能被查詢與復核。

## 常見反模式

Customer impact assessment 的反模式通常來自用單一技術指標代表所有影響。技術指標是 evidence，完整影響模型還需要客戶、功能、時間、正確性與金額維度。

| 反模式                   | 表面現象                    | 修正方向                            |
| ------------------------ | --------------------------- | ----------------------------------- |
| Server error rate 即影響 | 低 error rate 就低估事故    | 加入 tenant、feature、client signal |
| 所有客戶同一句更新       | 狀態頁過粗或過度廣泛        | 依 region / feature / segment 分層  |
| 補償事後拼帳             | 工程臨時查 billing 與 usage | 事前定義補償資料欄位                |
| 只算人數                 | 忽略金額、合約、資料正確性  | 加入 financial / compliance impact  |
| Confidence 不標示        | 估算與確認混在一起          | 標示 estimated / confirmed          |

Server error rate 即影響會讓事故分級失真。低錯誤率集中在核心客戶、金流流程或資料正確性時，實際 impact 可能高於平均值。

補償事後拼帳會拖慢收尾。若 billing、usage、audit 與 incident timeline 在平時就能對齊，補償與客戶回覆會更快進入可驗證狀態。

## 與資安分流的關係

Customer impact assessment 需要在資料外洩、授權錯誤與合規影響出現時啟動資安分流。這類事故的影響不只看可用性，也看資料類型、責任鏈、通知義務與證據保存。

若 impact assessment 發現 PII、credential、audit log gap、cross-tenant access 或資料匯出異常，應交給 07 的資料保護與事故分流流程，並在 8.19 decision log 中標示 evidence handling 限制。

## 交接路由

- 04.10 client-side / synthetic / RUM：補用戶感知訊號
- 04.12 audit log：補資料與責任證據
- 08.1 severity trigger：把 impact assessment 接入分級
- 08.4 incident communication：提供對外更新內容
- 08.10 stakeholder communication：接 status page 與補償政策
- 07.4 data protection：資料外洩或資料正確性影響分流
