---
title: "7.R7.2.9 Kaseya VSA 2021：MSP 供應鏈擴散路徑"
date: 2026-04-24
description: "管理平台事件透過 MSP 模型向多客戶擴散時，workflow 應如何分層應對"
weight: 71729
---

## 事故摘要

Kaseya VSA 2021 事件指出 MSP 管理平台若失守，攻擊可沿著託管關係快速擴展到多個客戶環境。

## 攻擊路徑

1. 攻擊管理平台入口。
2. 透過自動化管理能力下發惡意行為。
3. 連鎖影響多個下游客戶系統。

## 失效控制面

- 管理平面與客戶環境隔離不足。
- 自動化任務缺少高風險動作保護。
- 多租戶事件協調流程準備不足。

## 如果 workflow 少一步會發生什麼

若少了「跨客戶分批隔離」步驟，事件會在同一時間窗內形成大規模連鎖衝擊。

## 可落地的 workflow 檢查點

- 共同基線：以 [runbook](../../../../knowledge-cards/runbook/) 與 [incident timeline](../../../../knowledge-cards/incident-timeline/) 固定記錄觸發條件與處置節奏。
- 發布前：限制管理平面高權限任務範圍。
- 日常：建立多租戶事件通知與處置模板。
- 事故中：先分域隔離，再啟動客戶側回復計畫。

## 可引用章節

- `backend/07-security-data-protection` 的多租戶邊界治理
- `backend/08-incident-response` 的跨組織通訊節奏

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：[helpdesk.kaseya.com](https://helpdesk.kaseya.com/hc/en-gb/articles/4403440684689)
- 政府或監管：[cisa.gov](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-209a)
- 技術分析：[nvd.nist.gov/CVE-2021-30116](https://nvd.nist.gov/vuln/detail/CVE-2021-30116)
