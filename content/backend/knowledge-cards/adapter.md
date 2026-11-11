---
title: "Integration Adapter"
date: 2026-04-23
description: "說明外部系統接入層如何轉換介面與隔離差異"
weight: 1
---

Integration Adapter 的核心概念是「把外部系統的介面轉成 application 需要的形狀」。它是 service boundary 與具體技術之間的轉譯層。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 跟其他概念的關係

Integration Adapter 位在 application port 與外部服務之間。repository adapter、provider adapter、notification adapter 都屬於這個角色。 可先對照 [Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)。

## 可觀察訊號

系統需要 integration adapter 的訊號包括：外部系統介面常變、錯誤碼不一致、同一個功能需要支援多個供應商、業務邏輯不應直接耦合外部介面細節。

## 接近真實網路服務的例子

資料庫 adapter 負責 SQL row mapping 與錯誤轉換；付款 adapter 負責 provider API 與內部訂單狀態對齊；通知 adapter 負責把 domain event 轉成 email、push 或 webhook payload。

## 判斷條件與後果

Integration Adapter 做了哪些事，決定外部介面改變時要改哪裡。adapter 只做介面轉換與錯誤分類時，供應商改 API 或換一家供應商，改動停在 adapter 裡，application 不必動；業務規則寫進 adapter 時，同一條規則在每個供應商的 adapter 各有一份，換供應商要重寫規則，幾份之間也可能不一致。錯誤沒有分類時，application 收到的是各家原始的錯誤碼，重試與回報的程式要認得每一家的格式；觀測欄位（供應商名稱、外部請求 id）沒有保留時，出錯時分不出是哪一家的哪一次呼叫。adapter 同時做轉換與流程控制（重試、多步驟呼叫）時，兩種邏輯的改動互相牽動，所以把純轉換與流程控制分開。
