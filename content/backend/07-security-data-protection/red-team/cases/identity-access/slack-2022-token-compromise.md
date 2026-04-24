---
title: "7.R7.1.7 Slack 2022：企業 token 與程式碼資產路徑"
date: 2026-04-24
description: "員工帳號被社交工程利用後，企業 token 與私有程式碼資產的防線如何運作"
weight: 71717
---

## 事故摘要

Slack 2022 安全公告說明攻擊者透過員工帳號路徑接觸內部資產，突顯企業 token 與程式碼資產的連動風險。

## 攻擊路徑

1. 先透過社交工程取得員工憑證。
2. 進入內部工具並接觸 token 或程式碼資產。
3. 嘗試擴大到高價值系統或資料節點。

## 失效控制面

- 員工身份遭濫用後的隔離速度不足。
- token 範圍與用途邊界定義不夠細緻。
- 程式碼資產存取異常訊號未快速匯流。

## 如果 workflow 少一步會發生什麼

若少了「內部 token 快速撤銷」步驟，攻擊者會維持有效會話，讓追查與復原成本上升。

## 可落地的 workflow 檢查點

- 發布前：把管理 token 分域並限制到最小權限。
- 日常：建立 [alert runbook](../../../../knowledge-cards/alert-runbook/) 監控異常存取。
- 事故中：分層撤銷 token，並用 [blast radius](../../../../knowledge-cards/blast-radius/) 框定影響面。

## 可引用章節

- `backend/07-security-data-protection` 的 token 與權限治理
- `backend/08-incident-response` 的止血與回復策略

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[slack.com](https://slack.com/blog/news/slack-security-update)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications)
