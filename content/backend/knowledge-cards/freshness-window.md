---
title: "Freshness Window"
date: 2026-07-20
description: "每類資料能容忍多久的不新鮮？依欄位風險分級定義過時窗口、取代單一全域 TTL"
weight: 389
tags: ["backend", "knowledge-card", "cache", "freshness"]
---

Freshness window 的核心概念是「一份資料被允許偏離正式狀態最新版本的可接受時間範圍」。它把「這筆資料可以 stale 多久」寫成可執行的分級規則，取代對所有欄位套用同一個全域 [TTL](/backend/knowledge-cards/ttl/) 的做法——商品描述可以接受幾分鐘的舊資料，價格與庫存的可接受範圍要壓到秒級。

## 概念位置

Freshness window 是 [source of truth](/backend/knowledge-cards/source-of-truth/) 與快取副本之間的容忍度契約，TTL、事件失效與版本化 key 都是達成這個容忍度的實作手段，freshness window 本身定義的是業務能接受的上限，不是機制。它跟 [bounded staleness](/backend/knowledge-cards/bounded-staleness/) 同屬「把不一致寫成可監控上限」這個思路，差別在 bounded staleness 常用於跨區複製的一致性語意，freshness window 聚焦快取副本對正式狀態的容忍度。

## 可觀察訊號與例子

需要明確定義 freshness window 的訊號是同一個快取服務裡混著體驗資料與交易資料，卻只設了一個全域 TTL。商品詳情頁的實務分級：商品描述 5-15 分鐘、促銷標籤 1-3 分鐘（切換頻繁、錯誤會影響轉換率）、庫存可售狀態 10-30 秒（超賣風險高）、價格與幣別 5-15 秒（交易正確性高風險，需搭配事件失效）。這種分級要先於 cache 服務選型討論，先問「這個值是可重建副本還是被拿來做正式判斷」與「每種值的 freshness window 是多久」。

## 設計責任

Freshness window 要跟 [cache invalidation](/backend/knowledge-cards/cache-invalidation/) 策略對齊：可接受 stale 的資料用 TTL 保底即可，高代價 stale 的資料需要事件驅動失效或版本化 key 加短 TTL 雙重保險。設計時要同時定義超標處置——freshness window 一旦沒有對應的告警與降級策略，就只是團隊口頭承諾，事故發生時無法佐證是否踩線。TTL 只回答了「預設多久過期」——freshness 的完整定義還要回答不同欄位的分級 TTL、以及超過 window 後要不要阻擋讀取或觸發保護動作。分欄位分級表的完整設計與跨區一致性延伸見 [2.7 Cache Copy Boundary 與 Freshness](/backend/02-cache-redis/cache-copy-freshness-boundary/)。
