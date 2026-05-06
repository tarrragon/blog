---
title: "Integration Adapter"
date: 2026-04-23
description: "說明外部系統接入層如何轉換介面與隔離差異"
weight: 0
---


Integration Adapter 的核心概念是「把外部系統的介面轉成 application 需要的形狀」。它是 service boundary 與具體技術之間的轉譯層。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 概念位置

Integration Adapter 位在 application port 與外部服務之間。repository adapter、provider adapter、notification adapter 都屬於這個角色。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 可觀察訊號

系統需要 integration adapter 的訊號包括：外部系統介面常變、錯誤碼不一致、同一個功能需要支援多個供應商、業務邏輯不應直接耦合外部介面細節。

## 接近真實網路服務的例子

資料庫 adapter 負責 SQL row mapping 與錯誤轉換；付款 adapter 負責 provider API 與內部訂單狀態對齊；通知 adapter 負責把 domain event 轉成 email、push 或 webhook payload。

## 設計責任

Integration Adapter 要隔離介面差異、做錯誤分類、保留觀測欄位、避免把業務規則塞進整合層。若 adapter 過厚，應把純轉換和流程控制分開。
