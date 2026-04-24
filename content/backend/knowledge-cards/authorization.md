---
title: "Authorization"
tags: ["授權", "Authorization"]
date: 2026-04-23
description: "說明授權如何判斷誰能對哪些資源執行哪些操作"
weight: 38
---

Authorization 的核心概念是「判斷已識別主體是否能執行某個操作」。[Authentication](../authentication/) 回答你是誰；authorization 回答你能做什麼、對哪個資源做、在什麼條件下做。

## 概念位置

Authorization 是資料保護與操作安全的核心邊界。它可以用 role、permission、policy、[tenant boundary](../tenant-boundary/)、resource owner 或 attribute-based rule 表達。

## 可觀察訊號與例子

系統需要授權模型的訊號是角色、資料範圍或操作風險開始分級。客服可以查看訂單狀態，但調整退款、下載 [PII](../pii/) 或修改權限應需要更高權限與 [audit log](../audit-log/)。

## 設計責任

授權設計要定義主體、資源、操作、條件、拒絕原因與稽核欄位。測試要覆蓋跨 tenant 存取、低權限升級、高風險操作、[function-level authorization](../function-level-authorization/) 與資料匯出。

