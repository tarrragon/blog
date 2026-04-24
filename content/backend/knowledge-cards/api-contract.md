---
title: "API Contract"
date: 2026-04-23
description: "說明 request / response 邊界如何維持相容與可驗證"
weight: 0
---

API Contract 的核心概念是「client 與 service 對 request / response 行為達成一致」。它定義欄位、錯誤、版本相容與破壞性變更。

## 概念位置

API Contract 位在 client、[API Gateway](../api-gateway/) 與 application 之間。當外部呼叫者依賴穩定格式時，就需要這種 contract。

## 可觀察訊號

系統需要 API contract 的訊號是不同團隊會共同整合，且欄位、錯誤碼或版本變動可能直接影響外部使用者。

## 接近真實網路服務的例子

查詢訂單、建立付款、更新會員資料或回傳錯誤資訊，都應遵守 API contract，並以 contract test 驗證。

## 設計責任

API Contract 要定義欄位名稱、必要欄位、預設值、錯誤格式與相容版本。破壞性變更需要受控發布與回復路徑。
