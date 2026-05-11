---
title: "7.C9 反例：憑證輪替未分 Scope"
date: 2026-05-07
description: "憑證輪替若未分域分批，容易造成跨系統連鎖中斷。"
weight: 9
tags: ["backend", "security", "case-study"]
---

這個反例的核心責任是說明 credential rotation 的失敗通常是治理節奏錯誤。

## 事故長相

憑證輪替完成後，多個服務同時開始認證失敗。問題不一定是新憑證錯，而是共用憑證牽涉太多服務，且各服務支援新舊憑證的時間窗口不同。

## 為什麼會擴大

secret、token、key 若沒有按作用域分開，輪替會變成一次性控制面變更。當一個系統先切新憑證、另一個系統還只認舊憑證，故障會沿著服務依賴快速擴散。

## 回退判讀

憑證事故不能只把舊憑證放回去。若舊憑證已被視為風險來源，直接回放可能重新打開安全缺口。更穩定的做法是先分域隔離受影響服務，恢復雙憑證窗口，再逐批收斂。

## 資安專屬告警條件

- 認證失敗同時跨多個 service boundary
- 輪替失敗率上升並伴隨權限例外增加
- incident log 顯示 owner 與憑證作用域不清

## 下一步路由

回 [7.6](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 與 [7.14](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)。
