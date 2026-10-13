---
title: "Alert Inhibition（告警抑制）"
date: 2026-10-13
description: "同一個原因觸發一串症狀告警、值班人員被淹沒，或要在 Alertmanager 寫 inhibit_rules 時，查抑制做什麼、它和分組與靜音的差別、哪些症狀適合被抑制，以及它安靜失效的幾種條件"
weight: 472
tags: ["backend", "observability", "alerting", "knowledge-card"]
---

Alert inhibition 是「原因」的告警成立時，自動壓下它造成的「症狀」告警的機制：通知改由原因那一則說明，收到告警的人看到的是一則原因，而不是一串症狀。Prometheus 生態裡由 Alertmanager 的 `inhibit_rules` 實作，規則寫明哪些告警是原因（`source_matchers`）、哪些是症狀（`target_matchers`），以及兩者要在哪些標籤上相同才算同一件事（`equal`）。它是 [Alert Fatigue](/backend/knowledge-cards/alert-fatigue/) 的降噪手段之一，與 [Symptom-Based Alert](/backend/knowledge-cards/symptom-based-alert/) 的分級一起決定誰該被壓下。

## 概念位置

| 機制                         | 由什麼決定                 | 適用                                           |
| ---------------------------- | -------------------------- | ---------------------------------------------- |
| 抑制（inhibition）           | 另一則告警是否成立         | 原因已知、症狀不需要逐一通知                   |
| 分組（grouping，`group_by`） | 告警的標籤相同             | 同一件事的多則告警合成一則通知，每一則仍然存在 |
| 靜音（silence）              | 人手動設定的時間範圍與條件 | 維護時段等已知會觸發的期間                     |

抑制只壓通知、不壓紀錄：被抑制的告警仍在 Prometheus 的 `ALERTS` 序列裡留下成立與結束的時間。抑制把通知交給原因那一則，所以適合不通知值班的症狀（warning，分級見 [Symptom-Based Alert](/backend/knowledge-cards/symptom-based-alert/)）；會通知值班的症狀改用分組，因為抑制也會把同時發生、與原因無關的故障一起藏掉。

## 可觀察訊號與例子

- **一串症狀同時成立**：主機過載時同一台主機上每個服務的延遲告警一起發出；資料庫停止時依賴它的查詢逾時告警一起發出。規則寫法、驗證方法與取捨見 [4.27 主機過載時的監控告警](/backend/04-observability/host-overload-alerting/)〈依原因抑制〉。
- **抑制安靜地不發生**：`equal` 用的標籤在原因與症狀兩邊的值不同（例如用 `instance` 當主機，而它是讀取對象的位址）；原因規則在虛擬機裡看不到虛擬機外的競爭而不成立；原因比症狀晚成立或先解除。這幾種情形都不會報錯，症狀照常通知。
- **抑制藏起不該藏的**：同一段時間另一個服務自己壞了，它的症狀也符合 `target_matchers`，一起被壓下。

## 設計責任

寫抑制規則時寫下原因與症狀的對應、`equal` 的標籤在兩邊各從哪裡來，並讓原因規則的觸發不晚於症狀、恢復不早於症狀（Prometheus 的 `keep_firing_for`）。驗證用合成告警送入一組標籤符合規則的原因與症狀，確認症狀的狀態是 `suppressed`，再送一則 `equal` 標籤值不同的症狀確認它維持 active；Prometheus 的原因規則會不會在實際狀況下成立另以故障注入確認。
