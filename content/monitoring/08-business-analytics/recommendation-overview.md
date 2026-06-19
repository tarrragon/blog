---
title: "推薦系統概論"
date: 2026-06-19
description: "Collaborative filtering / content-based / 混合方法 — 推薦系統的三種基本架構和各自的資料需求"
weight: 6
tags: ["monitoring", "analytics", "recommendation", "collaborative-filtering", "content-based"]
---

推薦系統從使用者的歷史行為或物品的內容特徵推斷使用者可能感興趣的物品。三種基本方法各自依賴不同的資料：collaborative filtering 依賴使用者行為矩陣，content-based 依賴物品特徵，混合方法結合兩者。

## Collaborative Filtering

Collaborative filtering 的核心假設是「和你行為相似的人喜歡的東西，你也可能喜歡」。它不分析物品的內容，只看使用者的行為模式。

### User-based

找到和目標使用者行為最相似的一群人（neighbors），把 neighbors 互動過但目標使用者沒互動過的物品推薦給目標使用者。

資料需求：使用者-物品互動矩陣（user × item matrix），每格是評分、點擊、購買等互動訊號。

挑戰：使用者數量增加時，計算使用者相似度的成本呈平方增長。冷啟動問題 — 新使用者沒有足夠的互動歷史來找到 neighbors。

### Item-based

計算物品之間的相似度（根據哪些使用者同時互動過這兩個物品），推薦和使用者已互動物品相似的物品。

資料需求：同上，但相似度計算的維度是物品而非使用者。

優勢：物品的相似度矩陣比使用者相似度穩定（物品不會突然改變行為，使用者會），可以離線計算和快取。Amazon 的「購買此商品的人也買了」就是 item-based collaborative filtering。

## Content-based Filtering

Content-based filtering 分析物品的內容特徵，推薦和使用者過去喜歡的物品內容相似的物品。

資料需求：每個物品的特徵向量（genre、author、price range、keywords）和使用者的偏好 profile（從歷史互動推斷）。

優勢：不依賴其他使用者的行為 — 單一使用者就能產生推薦。新物品只要有特徵描述就能被推薦（解決 collaborative filtering 的新物品冷啟動）。

挑戰：推薦結果傾向和使用者歷史行為相似，缺乏意外發現（serendipity）。特徵工程的品質直接影響推薦品質 — 物品的特徵描述不完整或不準確，推薦就不準確。

## 混合方法

結合 collaborative filtering 和 content-based 的優勢，減少各自的弱點。

### 加權混合

兩種方法各自產生推薦清單，用加權分數合併。權重可以固定，也可以根據情境動態調整（新使用者偏重 content-based，老使用者偏重 collaborative filtering）。

### 特徵增強

用 content-based 的特徵增強 collaborative filtering 的矩陣。使用者-物品互動矩陣加上物品的內容特徵，讓相似度計算同時考慮行為和內容。

### 級聯

先用一種方法粗篩，再用另一種方法排序。Collaborative filtering 產生候選清單，content-based 根據使用者的內容偏好排序。

## 行為事件在推薦系統的角色

推薦系統的輸入是使用者的互動行為 — 瀏覽、點擊、加入購物車、購買、評分。這些互動行為就是行為事件（[模組一 心智模型](/monitoring/01-mental-model/)）的 event 類型。

行為事件的設計直接影響推薦系統的資料品質。事件的粒度決定了推薦的精細度 — 只記錄「頁面瀏覽」比記錄「頁面瀏覽 + 停留時間 + 滾動深度」的推薦信號弱。

## 下一步路由

- 使用者分群的工程實作 → [RFM 分群](/monitoring/08-business-analytics/rfm-segmentation/)
- 行為事件設計 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
- 自架方案的分析能力邊界 → [從 collector 資料做基礎 funnel 分析](/monitoring/08-business-analytics/self-hosted-funnel/)
