---
title: "4.C10 對照：規模差異下的觀測遷移"
date: 2026-05-07
description: "觀測遷移在不同規模團隊下的流程與風險差異。"
weight: 10
---

這篇對照的核心責任是提醒觀測遷移不是工具替換，而是治理能力轉換。

## 小型團隊常見判讀

小型團隊最怕雙軌過久。若同時維護兩套儀表，通常會先耗盡人力。小團隊更需要短期對照、快速收斂，而不是一次拉滿所有治理流程。

## 中型團隊常見判讀

中型團隊會碰到 schema 漂移與標籤膨脹。這個階段的失敗常見於「看得到數據，但看不懂是否同一語意」，導致告警與容量判讀彼此矛盾。

## 大型團隊常見判讀

大型團隊的觀測遷移會牽涉成本分攤、採樣策略、collector 拓撲。若只追求功能對齊，往往在遷移後才出現成本暴增與告警漂移。

## 這個情境的專屬告警條件

- 新舊管線 `error rate` 或 `burn rate` 偏差長期超標
- missing signal 比例持續上升
- 同一事件在兩套儀表板得到相反結論

觸發條件時應停止切換，先修資料語意與採樣策略，再決定是否繼續遷移。

## 判讀訊號

判讀重點是「兩套觀測是否仍在描述同一個系統狀態」。當 error rate、burn rate、trace coverage 三者任一長期偏離，就代表遷移證據不可信，應先停切換再修資料品質。

## 邊界判讀

這篇對照只處理觀測遷移的判讀邊界，不處理各 vendor 的實作細節。主要風險是把資料語意不一致當成短暫噪音，導致團隊在錯誤證據上推進切換。

## 下一步路由

先回到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/) 修正語意與採樣，再到 [4.11 Telemetry Pipeline](/backend/04-observability/telemetry-pipeline/) 校正雙軌管線。若已影響事故判讀，交接到 [8.18 Incident Intake](/backend/08-incident-response/incident-intake-evidence-triage/)。
