---
title: "Authorization"
tags: ["授權", "Authorization"]
date: 2026-04-23
description: "說明授權如何判斷誰能對哪些資源執行哪些操作"
weight: 39
---

Authorization 的核心概念是「判斷已識別主體是否能執行某個操作」。[Authentication](/backend/knowledge-cards/authentication/) 回答你是誰；authorization 回答你能做什麼、對哪個資源做、在什麼條件下做。

## 跟其他概念的關係

Authorization 是資料保護與操作安全的核心邊界。它可以用 role、permission、policy、[tenant boundary](/backend/knowledge-cards/tenant-boundary/)、resource owner 或 attribute-based rule 表達。

## 可觀察訊號與例子

系統需要授權模型的訊號是角色、資料範圍或操作風險開始分級。客服可以查看訂單狀態，但調整退款、下載 [PII](/backend/knowledge-cards/pii/) 或修改權限應需要更高權限與 [audit log](/backend/knowledge-cards/audit-log/)。

## 判斷條件與後果

授權模型少了哪一個成分，就有一類判斷做不出來。只有主體與操作、沒有資源時，系統只判斷得了「這個角色能不能做這件事」，判斷不了「能不能對這一筆資料做」，請求裡換掉 id 就讀得到別人的資料；沒有條件時，時間、tenant、操作風險這類情境進不了判斷；沒有拒絕原因與稽核欄位時，被擋下的越權嘗試與被誤擋的正常操作都查不回原因。測試只涵蓋正常角色的正常操作時，越權路徑不會被測到，原因是越權請求的形狀和正常請求一樣，只有換成另一個 tenant 或另一個權限等級去呼叫才看得出差別；所以測試涵蓋跨 tenant 存取、低權限升級、高風險操作、[function-level authorization](/backend/knowledge-cards/function-level-authorization/) 與資料匯出。
