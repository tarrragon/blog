---
title: "7.R7.1.3 Twilio 2022：社交工程與員工帳號路徑"
date: 2026-04-24
description: "社交工程如何穿透員工身分流程，並影響下游客戶與供應鏈"
weight: 71713
---

## 事故摘要

2022 年 8 月，Twilio 公告社交工程攻擊造成員工帳號被濫用，影響內部系統與部分客戶關聯風險。

## 攻擊路徑

1. 以釣魚或社交工程瞄準員工。
2. 取得可登入的員工身份。
3. 使用合法身份移動到高價值系統與資料。

## 失效控制面

- 員工身份保護流程對社交工程韌性不足。
- 登入後的高敏感操作缺少額外驗證。
- 身分異常事件與快速隔離機制不夠緊密。

## 如果 workflow 少一步會發生什麼

若缺少「員工帳號異常即時隔離」步驟，攻擊者會持續用合法會話做橫向移動，調查難度與影響面同步上升。

## 可落地的 workflow 檢查點

- 發布前：高風險管理操作要求二次核准。
- 日常：針對員工身份建立 [alert runbook](../../../../knowledge-cards/alert-runbook/)。
- 事故中：執行分批憑證輪替與權限縮減，控制 [blast radius](../../../../knowledge-cards/blast-radius/)。

## 可引用章節

- `backend/07-security-data-protection` 的身份治理章節
- `backend/08-incident-response` 的止血與角色分工

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[twilio.com](https://www.twilio.com/en-us/blog/august-2022-social-engineering-attack)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-sms-phishing-sim-swapping-ransomware/)
