---
title: "模組七：資安與資料保護"
date: 2026-04-24
description: "以原子化概念建立資安章節：先定義服務環節問題，再用案例判讀，最後路由到各服務章節實作"
weight: 7
---

本模組的責任是把資安議題拆成可重用的原子化決策單元。每個章節先回答服務環節的問題與注意事項，再用案例提供判讀證據，最後把實作路由到對應服務章節。

## 原子化拆分原則

原子化拆分的核心是讓每章只承擔一個語意責任。這個做法讓同一個概念可以跨服務重用，並維持章節之間的邊界清晰。

- 身分與授權章：回答誰能做什麼，以及風險如何擴散。
- 入口與邊界章：回答攻擊面在哪裡，以及入口治理節奏。
- 資料保護章：回答資料在回應、匯出、log、備份的暴露風險。
- 傳輸信任章：回答跨邊界流量信任如何建立與維持。
- 憑證與秘密章：回答機器憑證與密鑰生命週期的治理。
- 稽核與責任章：回答高風險操作如何追蹤、判讀、回溯。
- 紅隊章：回答攻擊者視角案例如何映射到服務環節。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由各服務章節承接，確保同一套觀念可依服務實體差異展開。

- `backend/05-deployment-platform`：承接入口、交付鏈與邊界實作。
- `backend/06-reliability`：承接回復排序、可用性與驗證實作。
- `backend/08-incident-response`：承接分級、指揮與 runbook 實作。

## 章節列表（原子化骨架）

| 章節 | 主題 | 核心責任 |
| --- | --- | --- |
| [7.1 攻擊者視角（紅隊）與攻擊面驗證](red-team/) | 案例與攻擊者判讀 | 把案例轉成跨服務問題地圖 |
| [7.2 身分與授權邊界](identity-access-boundary/) | Identity & Access | 建立角色、權限、會話與供應商身分邊界 |
| [7.3 入口治理與伺服器防護](entrypoint-and-server-protection/) | Server Protection | 建立入口分級、暴露面收斂與事件節奏 |
| [7.4 資料保護與遮罩治理](data-protection-and-masking-governance/) | Data Protection | 建立資料流分級、遮罩、匯出與備份邊界 |
| [7.5 傳輸信任與憑證生命週期](transport-trust-and-certificate-lifecycle/) | Transport Trust | 建立 TLS/mTLS 與憑證信任維運節奏 |
| [7.6 秘密管理與機器憑證治理](secrets-and-machine-credential-governance/) | Secrets & Credentials | 建立 secret、token、key 的分域與輪替路由 |
| [7.7 稽核追蹤與責任邊界](audit-trail-and-accountability-boundary/) | Audit & Accountability | 建立高風險操作追蹤與責任判讀框架 |
| [7.8 模組路由：案例到服務實作](security-routing-from-case-to-service/) | Routing | 把案例判讀轉成跨章節落地任務清單 |

## 本輪填充範圍

本輪先完成完整大綱，並先填充 7.2 與 7.3 內文。後續章節已建立可直接續寫的結構與路由。
