---
title: "API Contract"
date: 2026-04-23
description: "說明 request / response 邊界如何維持相容與可驗證"
weight: 1
---

API Contract 的核心概念是「client 與 service 對 request / response 行為達成一致」。它定義欄位、錯誤、版本相容與破壞性變更。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

API Contract 位在 client、[API Gateway](/backend/knowledge-cards/api-gateway/) 與 application 之間。當外部呼叫者依賴穩定格式時，就需要這種 contract。實際被依賴的範圍常大於文件承諾的範圍、見 [Hyrum's Law](/backend/knowledge-cards/hyrums-law/)。

## 可觀察訊號

系統需要 API contract 的訊號是不同團隊會共同整合，且欄位、錯誤碼或版本變動可能直接影響外部使用者。

## 接近真實網路服務的例子

查詢訂單、建立付款、更新會員資料或回傳錯誤資訊，都應遵守 API contract，並以 contract test 驗證。

## 判斷條件與後果

API Contract 沒寫定的項目，client 就依據某一次回應的實際行為寫程式。欄位名稱與必要欄位沒有寫定時，服務端改名或拿掉欄位，client 解析失敗；預設值沒有寫定時，服務端換了預設，client 的行為跟著改變而不出現任何錯誤；錯誤格式沒有寫定時，client 只能逐一比對錯誤字串；相容版本沒有定義時，服務端分不出哪些改動會打斷既有的 client。破壞性變更一上線，依賴舊行為的 client 就已經出錯，沒有受控發布與回復路徑時，只能等修正版上線，所以破壞性變更要經受控發布，並備好回復路徑。

這四件事各自的推導層在 [模組十一](/backend/11-api-design/)：什麼算破壞性變更看 [向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)、錯誤格式的容器選擇看 [錯誤格式之爭](/backend/11-api-design/error-format-debate/)、相容版本怎麼分期看 [版本策略流派之爭](/backend/11-api-design/versioning-strategy-debate/)。契約已經上線之後才要收緊某個性質時，路徑跟綠地不同，見 [既有 API 的改造路徑](/backend/11-api-design/existing-api-retrofit/)。
