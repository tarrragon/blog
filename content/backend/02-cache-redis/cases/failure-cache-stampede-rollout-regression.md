---
title: "2.C9 反例：快取切換引發 Stampede 回歸"
date: 2026-05-07
description: "快取策略切換若缺乏保護，會導致回源壓力與錯誤率連鎖上升。"
weight: 9
tags: ["backend", "cache", "case-study"]
---

這個反例的核心責任是說明快取轉換最常失敗在回源保護不足。

## 事故長相

一次看似低風險的 cache key 或 TTL 切換，會讓熱門資料同時 miss。使用者看到的是 API 變慢與錯誤率上升，資料庫看到的是原本被快取吸收的流量突然全部回源。

## 為什麼會擴大

快取切換如果沒有 warmup、singleflight、節流與降級保護，miss 會引發重試，重試又會增加 origin 壓力。這不是單一 key 的問題，而是讀取路徑同時失去緩衝。

## 回退判讀

回退不應只把程式版本切回去。若新舊快取 key、TTL 或序列化格式已經混在一起，回退還要處理資料可讀性與回源壓力。實務上要先降載或恢復舊 key 讀取，再逐步清理新策略留下的快取狀態。

## 快取專屬告警條件

- 熱門 key miss 同步上升，且 origin QPS 快速超過平日基線
- response time 拉長並伴隨重試流量增加
- stale read 與 cache miss 同時惡化

## 下一步路由

回 [2.2](/backend/02-cache-redis/cache-aside/) 與 [6.24](/backend/06-reliability/rule-rollout-safety-gate/)。
