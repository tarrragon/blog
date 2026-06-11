---
title: "BaaS（Backend as a Service）"
date: 2026-06-11
description: "說明把認證、資料庫、檔案儲存、推播打包成現成模組、由前端 SDK 直連的後端交付形態"
weight: 372
---

BaaS（Backend as a Service）的核心概念是把後端的常見能力 — 認證、資料庫、檔案儲存、推播、serverless function — 打包成現成模組、應用程式的前端（app / SPA）用平台 SDK 直接連上這些模組、不經過自己寫的後端服務。它讓「沒有後端工程師」的團隊能先把產品做出來、代價是資料模型、查詢能力與授權機制都沿平台的形狀生長。代表服務是 Firebase 與 Supabase。它的長期成本面接回 [Vendor Lock-In](/backend/knowledge-cards/vendor-lock-in/)。

## 概念位置

BaaS 位在交付形態光譜的中段：比全託管平台（Wix、Shopify 類）保留更多應用程式控制權（前端完全自己寫）、比自建少掉整層後端服務。它跟自建世界的 [database](/backend/knowledge-cards/database/) 與 [object storage](/backend/knowledge-cards/object-storage/) 提供同類能力、差別在存取模型：自建走「client → 自己的 API → 資料庫」、BaaS 走「client → SDK → 平台資料庫」、授權邏輯從 API 層下沉到平台的安全規則裡。

## 可觀察訊號與例子

適合 BaaS 的訊號是產品形態為行動 app 或 SPA、後端需求集中在認證、資料同步與推播、且團隊想把後端工程延後。一個行動端的記帳 app、用 Firebase Auth 處理登入、Firestore 存帳目並即時同步多裝置、Cloud Messaging 推提醒 — 整個 MVP 沒有一行自己的後端程式。

撞到邊界的訊號有三類：複雜查詢（跨集合報表在查詢受限的平台資料庫上變成資料複製工程）、成本曲線轉折（讀寫計費隨流量線性成長、高流量下超過自建）、安全規則失控（client 直連模型把全部授權寫進平台的規則語言、規則長到難以測試與 review）。

## 設計責任

採用 BaaS 時的設計責任是在進場當下記錄退出路徑：資料模型沿平台特性設計（反正規化結構、平台專屬同步語意）、遷出等於重做資料層；認證可攜性要先查證（Firebase Auth 可匯出密碼雜湊、屬於少數友善案例）。授權規則要當成程式碼管理 — 進版本控制、有 review、有測試 — 而不是在 console 上長大。判斷該不該採用、以及何時該遷往自建、屬於交付形態選型的判讀。
