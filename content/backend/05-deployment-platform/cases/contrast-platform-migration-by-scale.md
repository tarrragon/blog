---
title: "5.C10 對照：規模差異下的平台遷移"
date: 2026-05-07
description: "平台遷移策略在小中大型組織下的差異。"
weight: 10
tags: ["backend", "deployment", "case-study"]
---

這篇對照的核心責任是避免把同一套切流流程套到所有組織規模。遷移策略的切換單位、回退腳本化程度、依賴同步範圍與協同治理工具，在小中大型組織各有不同取捨。

## 小型組織常見判讀

小型組織通常能快速完成單叢集遷移，但最容易漏掉回退腳本化。結果是第一次回退就需要人工拼接操作，恢復時間不可預測。

回退腳本化缺失的具體表現：

- **手動 kubectl 操作**：回退時 on-call 逐一執行 `kubectl rollout undo`、手動修改 DNS 權重、手動切回 LB 規則。每一步都依賴執行者的記憶與判斷，步驟順序錯誤或遺漏都會延長恢復時間。
- **無 rollback script**：回退流程沒有腳本化，也沒有在 staging 驗證過。第一次真正回退就是在 production 事故中。
- **恢復時間不可預測**：手動操作的恢復時間取決於 on-call 的經驗與當下判斷力。同一個回退在不同人手上可能差 3-10 倍時間。

小型組織的回退投資最小可行版本是一個 shell script：按正確順序執行回退步驟、每步帶 dry-run 模式、在 staging 驗證過。這個投資的 ROI 在第一次真正回退時就回收。

## 中型組織常見判讀

中型組織的主要風險是依賴錯位。服務本身切過去了，但資料面、認證面、觀測面還沒同步，造成切換後局部成功、整體失敗。

依賴錯位的常見維度：

- **Database endpoint**：應用在新叢集但仍連舊叢集的資料庫。跨網路延遲從 <1ms 跳到 5-20ms，慢查詢變多、connection pool 壓力增加。嚴重時跨 AZ / region 的網路分區直接斷開連線。
- **Auth service**：新叢集的服務用舊叢集的 auth endpoint，token 驗證走跨網路。auth 延遲增加讓每個 request 的總延遲上升，高峰時 auth 成為瓶頸。
- **Observability pipeline**：新叢集的 metrics / logs / traces 仍送到舊叢集的收集器，或送到新收集器但 dashboard 還指向舊資料源。事故時看不到新叢集的指標，判讀盲區。
- **DNS 解析路徑**：新叢集的 CoreDNS 設定跟舊叢集不同（upstream resolver、search domain、ndots），服務的 DNS 解析行為改變但沒被偵測到。表現為間歇性連線失敗或解析延遲。

中型組織的遷移 checklist 要把這四個維度列為切換前驗證項目。每個維度各自有切換時機——資料庫通常最後切（風險最高），auth 跟 observability 要先切或同步切。切換順序規劃見 [5.2 分階段平台遷移](/backend/05-deployment-platform/kubernetes-deployment/#分階段平台遷移)。

## 大型組織常見判讀

大型組織的遷移失敗主要來自協同節奏失控。若沒有固定升級節奏與責任分工，單次變更容易演變成廣域事故。

協同節奏的具體治理工具：

- **Upgrade calendar**：所有平台級變更（叢集升級、service mesh 升級、CNI 更新）排進共用日曆。避免兩個團隊同週做影響面重疊的變更。日曆的維護者是 platform team，變更申請需提供 blast radius 估算。
- **Freeze window**：業務高峰期（促銷、財報季、年終）凍結非緊急平台變更。freeze window 的開始 / 結束時間要明確公告，例外申請需 VP 級批准。
- **Blast radius estimation**：每次變更前估算影響範圍——影響幾個 namespace、幾個 service、幾個使用者。估算結果進 release gate 的判定條件。工具層面可用 admission webhook 掃描變更影響的 namespace 數量。
- **Responsibility matrix**：遷移期間的 RACI 明確化——誰負責切換、誰負責監控、誰負責回退決策、誰負責對外溝通。大型組織的遷移通常跨 3+ 團隊，責任模糊是事故升級的主要原因。

大型組織的平台元件升級治理見 [5.7 平台元件升級的可重播流程](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#平台元件升級的可重播流程)。

## 跨規模的共通判讀

三個規模的失敗模式不同（小型漏回退腳本、中型漏依賴同步、大型漏協同節奏），但共通原則是「先定回退條件再開始切換」。回退條件包含三個面向：

1. **觸發條件**：哪些指標偏離到什麼程度就停止切換（5xx 升幅、延遲惡化、reconnect rate）。
2. **執行路徑**：回退的具體步驟、順序、負責人，且在 staging 驗證過。
3. **完成判定**：回退完成的訊號是什麼（連線數回 baseline、error rate 回 baseline、持續 N 分鐘）。

三個面向任一缺失，回退就會變成臨時決策——壓力下的臨時決策品質不穩定，是切流事故擴大的共通機制。

## 這個情境的專屬告警條件

- 切流批次 `5xx` 異常升高
- 長連線重連率飆升
- 回退時間超過既定 RTO
- 跨叢集依賴延遲突增（中型組織特有）

任一條件成立就停止下一批切換，先完成上一批穩定化與回退驗證。

## 下一步路由

回 [5.2 分階段平台遷移](/backend/05-deployment-platform/kubernetes-deployment/#分階段平台遷移) 看切換順序規劃。回 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 看遷移後的 lifecycle 重新驗證。回 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 看切流未 drain 的具體事故 timeline。
