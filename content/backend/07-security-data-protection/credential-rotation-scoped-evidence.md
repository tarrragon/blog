---
title: "7.27 Credential Rotation with Scoped Evidence 實作示範"
date: 2026-05-08
description: "以 webhook/API credential 輪替示範 scope map、證據欄位與回退窗口如何一起設計。"
weight: 27
tags: ["backend", "security", "credential-rotation", "implementation"]
---

Credential rotation with scoped evidence 的核心責任是把憑證輪替從一次性操作改成分域、可驗證、可回退的控制流程。

## 服務路徑與控制範圍

示範路徑是 webhook secret 與 service-to-service API token 輪替。這類變更常見錯誤是全域同批切換，導致無法快速定位失效範圍。

第一步先建 `scope map`：哪些服務、哪些環境、哪些第三方端點共用同一組 credential。再定義證據欄位：輪替前健康度、輪替中錯誤率、輪替後驗證結果與撤銷狀態。

## 實作步驟

1. 盤點 scope map：服務、環境、憑證用途、到期日、owner。
2. 設計輪替批次：先低風險租戶與非核心流量，再核心路徑。
3. 建立雙軌驗證窗口：新舊 credential 並行期間記錄命中比例。
4. 設定 rollback window：若驗證失敗可在時限內回退到舊憑證。
5. 輪替後執行撤銷與稽核：確認舊 credential 不再可用並保留 audit evidence。

## 判讀訊號

| 訊號                                | 判讀重點                     | 對應動作                       |
| ----------------------------------- | ---------------------------- | ------------------------------ |
| 輪替後 webhook 驗簽失敗集中在單區域 | scope map 與部署批次不一致   | 暫停擴批，先修區域映射         |
| 新舊 credential 命中比例長期雙高    | 撤銷步驟未完成或有隱藏呼叫方 | 延長觀察並追來源，禁止結案     |
| 輪替成功率高但稽核鏈缺欄位          | 證據不完整，事後不可追蹤     | 補 audit 欄位再進 release gate |
| 回退後仍有驗簽錯誤                  | 客戶端快取或第三方同步延遲   | 補回退窗口策略與客戶端同步公告 |
| 同一 key 在多服務超範圍使用         | credential scope 漂移        | 重新分域並建立到期輪替節奏     |

## 常見誤區

把輪替看成單次安全動作，會忽略它其實是跨服務變更管理。沒有 scope map 的輪替，出問題時只能全域停損。

把撤銷延後也會累積風險。舊 credential 長時間保留，會讓攻擊面與誤用窗口同時存在。

## 案例回寫

這條路徑可用 [7.C9 反例：憑證輪替失敗](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) 回寫。先看失敗是發生在分域、驗證還是撤銷，再回到本章補齊 scope map 與回退窗口。

這個案例主要支撐的是「輪替分域與證據鏈完整度」判讀，不直接支撐 incident 通訊節奏；外部通報回到 8.4/8.20。

## 跨模組路由

1. 與 7.6 的交接：治理原則回到 [Secrets and Machine Credential Governance](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)。
2. 與 7.7 的交接：稽核欄位與責任鏈回到 [Audit Trail and Accountability Boundary](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)。
3. 與 6.8 的交接：高風險輪替變更進 release gate。
4. 與 8.19 的交接：輪替中止與回退判斷進 incident decision log。

## 下一步路由

要回到全模組實作串接，接著讀 [0.15 後端實作教學大綱](/backend/00-service-selection/implementation-teaching-outline/) 的「完成判準」與後續 backlog。
