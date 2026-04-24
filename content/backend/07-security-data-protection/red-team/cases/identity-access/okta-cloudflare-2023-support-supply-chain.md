---
title: "7.R7.1.2 Okta + Cloudflare 2023：支援流程與身分供應鏈"
date: 2026-04-24
description: "支援工單與第三方身份供應商路徑如何變成入侵鏈的一部分"
weight: 71712
---

## 事故摘要

2023 年 10 到 11 月，Okta 與 Cloudflare 的公開說明都指出，攻擊者透過支援相關流程取得可用資訊，形成跨組織的身分供應鏈風險。

## 攻擊路徑

1. 鎖定支援流程與可取得的工單資料。
2. 利用流程缺口取得敏感資訊或權限線索。
3. 以第三方身份供應商作為橋接點延伸到客戶側。

## 失效控制面

- 支援資料流沒有被視為高敏感資產。
- 憑證或會話資料生命周期管理不足。
- 供應商事件到客戶內部輪替流程沒有強制觸發。

## 如果 workflow 少一步會發生什麼

若缺少「供應商事件觸發的全域憑證輪替」，事件會停在公告層，實際可利用的憑證仍留在環境中。

## 可落地的 workflow 檢查點

- 發布前：支援系統資料分級，限制下載與外流路徑。
- 日常：建立第三方事件觸發的 [runbook](../../../../../knowledge-cards/runbook/)。
- 事故中：啟用供應商事件專用 [playbook](../../../../../knowledge-cards/playbook/)，執行輪替、追蹤、封鎖。

## 可引用章節

- `backend/07-security-data-protection` 的第三方信任邊界
- `backend/04-observability` 的供應商事件告警關聯

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[sec.okta.com](https://sec.okta.com/articles/2023/11/unauthorized-access-oktas-support-case-management-system-root-cause)
- 政府或監管：[blog.cloudflare.com](https://blog.cloudflare.com/thanksgiving-2023-security-incident/)
- 技術分析：[cloud.google.com](https://cloud.google.com/blog/topics/threat-intelligence/unc3944-targets-saas-applications)
