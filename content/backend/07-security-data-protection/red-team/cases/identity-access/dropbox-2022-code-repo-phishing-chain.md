---
title: "7.R7.1.8 Dropbox 2022：釣魚入侵與程式碼倉儲風險"
date: 2026-04-24
description: "從員工釣魚事件到私有程式碼資產保護，建立身分與研發資產的聯防流程"
weight: 71718
---

## 事故摘要

Dropbox 2022 事件顯示員工帳號釣魚成功後，攻擊者可接觸私有程式碼倉儲與內部文件資產。

## 攻擊路徑

1. 社交工程鎖定員工帳號。
2. 取得可登入的企業身份。
3. 存取程式碼倉儲與內部文件系統。

## 失效控制面

- 員工端高風險登入驗證策略不足。
- 研發資產保護缺少額外 step-up 驗證。
- 身分異常與程式碼倉儲稽核串接不足。

## 如果 workflow 少一步會發生什麼

若少了「程式碼資產異常存取升級」步驟，攻擊者可在內部環境延長停留時間並擴大探索範圍。

## 可落地的 workflow 檢查點

- 發布前：對高敏感 repo 操作要求強化 [authentication](../../../../knowledge-cards/authentication/)。
- 日常：將 repo 存取告警納入 [on-call](../../../../knowledge-cards/on-call/) 流程。
- 事故中：即時凍結可疑憑證與連線，保留時間軸證據。

## 可引用章節

- `backend/05-deployment-platform` 的程式碼與交付保護
- `backend/07-security-data-protection` 的身份分層治理

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[dropbox.tech](https://dropbox.tech/security/a-security-update-on-code-repositories)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-320a)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications)
