---
title: "7.R7.4.5 VMware ESXiArgs 2023：虛擬化平台勒索回復壓力"
date: 2026-04-24
description: "虛擬化平台漏洞被利用後，回復策略與營運連續性會面臨同步壓力"
weight: 71745
---

## 事故摘要

ESXiArgs 事件顯示 CVE-2021-21974 與 CVE-2021-21972 這類虛擬化平台漏洞可轉為大規模勒索與服務中斷，回復節奏成為關鍵控制面。

## 攻擊路徑

1. 利用已知 ESXi 漏洞取得主機控制能力。
2. 執行加密或破壞作業影響虛擬機。
3. 造成資料可用性與業務連續性衝擊。

## 失效控制面

- 虛擬化平台修補節奏與資產可見性不足。
- 快照、備份與復原演練覆蓋不足。
- 事故中回復優先級路由不夠明確。

## 如果 workflow 少一步會發生什麼

若少了「回復優先級排序」步驟，團隊會在高壓情境下延長核心服務停擺時間。

## 可落地的 workflow 檢查點

- 發布前：定義核心服務的 [RTO](../../../../knowledge-cards/rto/) 與 [RPO](../../../../knowledge-cards/rpo/)。
- 日常：演練備份還原並記錄 [MTTR](../../../../knowledge-cards/mttr/)。
- 事故中：先恢復核心服務，再分批回補次要工作負載。

## 可引用章節

- `backend/06-reliability` 的備援與回復策略
- `backend/08-incident-response` 的回復決策流程

## 三個以上來源（官方/政府或監管/技術分析）

- 官方：https://www.vmware.com/security/advisories/VMSA-2021-0002.html
- 政府或監管：https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-040a
- 技術分析：https://nvd.nist.gov/vuln/detail/CVE-2021-21972
- 技術分析：https://nvd.nist.gov/vuln/detail/CVE-2021-21974
