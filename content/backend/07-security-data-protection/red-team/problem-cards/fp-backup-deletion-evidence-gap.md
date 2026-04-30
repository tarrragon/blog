---
title: "7.R11.P14 備份刪除證據缺口"
tags: ["備份刪除", "Deletion Evidence", "Retention", "Red Team"]
date: 2026-04-30
description: "說明主路徑刪除完成但備份證據不可驗證時的長尾暴露風險"
weight: 7244
---

這個失效樣式的核心問題是刪除閉環只覆蓋主系統，沒有覆蓋備份路徑的可驗證證據。當備份刪除證據不足，資料暴露會長期停留在隱性狀態，並破壞 [data lifecycle](/backend/knowledge-cards/data-lifecycle/) 一致性。

## 常見形成條件

- 正式資料刪除流程未同步到備份刪除流程。
- 備份保留政策與 [retention](/backend/knowledge-cards/retention/) 承諾缺少對齊條件。
- 刪除回覆缺少主體、時間與資產的 [audit log](/backend/knowledge-cards/audit-log/) 欄位。

## 判讀訊號

- 主系統刪除完成後，備份仍可長期還原相同資料。
- 刪除事件在 [incident timeline](/backend/knowledge-cards/incident-timeline/) 與稽核鏈上缺少備份路徑證據。
- 使用者刪除請求關閉後仍出現同資料外送跡象。

## 案例觸發參考

- [LastPass 2022](/backend/07-security-data-protection/red-team/cases/data-exfiltration/lastpass-2022-backup-chain/)
- [Snowflake 2024](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)
- [WS_FTP 2023](/backend/07-security-data-protection/red-team/cases/data-exfiltration/progress-wsftp-2023-file-service-breach/)

## 來源流程卡

- [匯出流程濫用](/backend/07-security-data-protection/red-team/problem-cards/export-flow-abuse/)
