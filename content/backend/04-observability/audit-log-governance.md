---
title: "4.12 Audit Log 邊界與 PII 治理"
date: 2026-05-01
description: "把稽核訊號從 operational log 拆出、按法規與不變性治理"
weight: 12
---

## 大綱

- audit log 跟 operational log 的本質差異：對象、不變性、保留、法規
- audit log 該記什麼：who / what / when / where / outcome、不可被應用層改寫
- 不變性保證：append-only storage、tamper-evident hash chain、independent retention
- PII 治理：log 中的 PII 偵測、redaction、tokenization、最小揭露原則
- 法規維度：GDPR / HIPAA / SOC2 / 個資法 對保留期與存取的要求
- 跟 [4.1 log schema](/backend/04-observability/log-schema/) 的分工：4.1 是欄位設計、4.12 是治理邊界
- 跟 [07 資安](/backend/07-security-data-protection/) 的交接：稽核責任邊界
- 反模式：audit 跟 operational 混在同 stream；PII 直接打進 log；audit log 跟 application DB 同保留期

## 判讀訊號

- 稽核需求出現時、靠 grep operational log 拼湊
- log 中發現 credit card / 身分證 / token 等 PII
- audit log 跟 application 同 retention（30 / 90 天）、不符法規
- 應用層帳號可寫入 / 修改 audit log
- 法規稽核請求耗時數週、無法定位事件鏈

## 交接路由

- 04.1 log schema：欄位設計
- 04.7 cardinality / cost：audit 的長期保留成本
- 07 資料保護：PII redaction 與責任邊界
- 08.5 postmortem：事故證據鏈引用 audit log
- 08.17 security vs operational IR：證據鏈來源
