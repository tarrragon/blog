---
title: "7.R7.3.16 Citrix ADC 後續事件：Session 重放延伸"
date: 2026-04-24
description: "同一波邊界事件在後續通報階段，重點轉為會話與憑證收斂"
weight: 717316
---

## 事故摘要

Citrix 後續事件通報指出，漏洞修補後仍需處理 session 與憑證風險，才能完成真正關閉。

## 攻擊路徑

1. 利用邊界漏洞取得會話資訊。
2. 以重放方式維持未授權存取。
3. 在修補後窗口延續攻擊。

## 失效控制面

- 修補流程與會話收斂流程分離。
- 權杖失效策略執行覆蓋不足。
- 事後追蹤指標沒有對準重放風險。

## 如果 workflow 少一步會發生什麼

若少了「修補後全域重新驗證登入」步驟，已竊取會話仍可能繼續被利用。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](/backend/knowledge-cards/runbook/) 與 [incident timeline](/backend/knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：定義漏洞事件後的 session 重發機制。
- 日常：維護會話壽命與失效政策基線。
- 事故中：修補、會話失效、登入重驗證三段同步。

## 可引用章節

- `backend/07-security-data-protection` 的 session 治理
- `backend/08-incident-response` 的驗證關閉標準

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[support.citrix.com](https://support.citrix.com/article/CTX579459)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/alerts/2023/11/07/cisa-releases-guidance-addressing-citrix-netscaler-adc-and-gateway-vulnerability-cve-2023-4966)
- 技術分析：[nvd.nist.gov/CVE-2023-4966](https://nvd.nist.gov/vuln/detail/CVE-2023-4966)
