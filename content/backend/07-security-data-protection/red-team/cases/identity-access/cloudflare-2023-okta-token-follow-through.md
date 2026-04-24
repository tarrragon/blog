---
title: "7.R7.1.6 Cloudflare 2023：供應商事件後的身分收斂"
date: 2026-04-24
description: "同一條供應商事件鏈，如何在客戶端變成 session 與 token 的收斂壓力"
weight: 71716
---

## 事故摘要

Cloudflare 在 2023 年事件說明中展示了供應商端事件如何傳導到客戶端身分流程，並觸發大規模憑證與 token 收斂作業。

## 攻擊路徑

1. 攻擊者先利用供應商支援流程取得線索。
2. 嘗試使用取得的資訊進入客戶端環境。
3. 透過 token、session 或憑證鏈路擴展存取。

## 失效控制面

- 供應商事件觸發條件與內部 runbook 連動不足。
- 高權限 token 的失效與輪替策略準備度不足。
- 受影響資產盤點與證據保存流程分離。

## 如果 workflow 少一步會發生什麼

若少了「供應商事件即啟動全域 token 盤點」步驟，事件判讀會停在公告層，內部可利用憑證仍持續存在。

## 可落地的 workflow 檢查點

- 發布前：為第三方事件設計獨立 [runbook](../../../../knowledge-cards/runbook/) 與責任分工。
- 日常：維護 [playbook](../../../../knowledge-cards/playbook/) 的憑證輪替優先級。
- 事故中：先凍結高風險憑證，再分批恢復必要權限。

## 可引用章節

- `backend/07-security-data-protection` 的第三方信任邊界
- `backend/08-incident-response` 的事故分級與角色分工

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：https://blog.cloudflare.com/thanksgiving-2023-security-incident/
- 政府或監管：https://sec.okta.com/articles/2023/11/unauthorized-access-oktas-support-case-management-system-root-cause
- 技術分析：https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications
