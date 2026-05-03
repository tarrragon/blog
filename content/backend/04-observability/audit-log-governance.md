---
title: "4.12 Audit Log 邊界與 PII 治理"
date: 2026-05-01
description: "把稽核訊號從 operational log 拆出、按法規與不變性治理"
weight: 12
---

## 大綱

- [audit log](/backend/knowledge-cards/audit-log/) 跟 operational log 的本質差異：對象、不變性、保留、法規
- [audit log](/backend/knowledge-cards/audit-log/) 該記什麼：who / what / when / where / outcome、不可被應用層改寫
- 不變性保證：append-only storage、tamper-evident hash chain、independent retention
- [PII](/backend/knowledge-cards/pii/) 治理：log 中的 PII 偵測、[data masking](/backend/knowledge-cards/data-masking/)、tokenization、最小揭露原則
- 法規維度：GDPR / HIPAA / SOC2 / 個資法 對保留期與存取的要求
- 跟 [4.1 log schema](/backend/04-observability/log-schema/) 的分工：4.1 是欄位設計、4.12 是治理邊界
- 跟 [07 資安](/backend/07-security-data-protection/) 的交接：稽核責任邊界
- 反模式：audit 跟 operational 混在同 stream；PII 直接打進 log；audit log 跟 application DB 同保留期

## 概念定位

[Audit log](/backend/knowledge-cards/audit-log/) 是把責任、授權與敏感操作留下可稽核證據的訊號，責任是支援合規、責任追蹤與安全事件調查。

這一頁處理的是 governance 邊界。Operational log 服務於除錯，audit log 服務於證據；兩者可以共享部分欄位，但保留、不變性、存取權限與 PII 規則不同。

## 核心判讀

判讀 audit log 時，先看事件是否能回答 who / what / when / where / outcome，再看資料是否受到獨立保護。

重點訊號包括：

- audit event 是否不可由一般應用流程修改
- [PII](/backend/knowledge-cards/pii/) 是否經過 redaction、tokenization 或最小揭露
- [retention](/backend/knowledge-cards/retention/) 是否符合法規與客戶合約要求
- security incident 與 operational incident 是否能引用同一條證據鏈

## 判讀訊號

- 稽核需求出現時、靠 grep operational log 拼湊
- log 中發現 credit card / 身分證 / token 等 PII
- audit log 跟 application 同 retention（30 / 90 天）、不符法規
- 應用層帳號可寫入 / 修改 audit log
- 法規稽核請求耗時數週、事件鏈定位需要人工補洞

## 交接路由

- 04.1 log schema：欄位設計
- 04.7 cardinality / cost：audit 的長期保留成本
- 07 資料保護：[PII](/backend/knowledge-cards/pii/) redaction 與責任邊界
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：事故證據鏈引用 audit log
- 08.17 security vs operational IR：證據鏈來源
