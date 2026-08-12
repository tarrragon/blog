---
title: "Problem Details（RFC 9457）"
date: 2026-08-11
description: "錯誤格式的現成標準給了什麼——URI 命名空間與未知欄位忽略條款，這兩件事自建格式要自己補"
weight: 436
---

Problem Details 的核心責任是給 HTTP API 的錯誤回應一個現成的、可演化的形狀。RFC 9457 定義 media type `application/problem+json`，核心成員是 `type`（錯誤種類的 URI）、`title`、`status`、`detail`、`instance` 五個。它跟 [API Contract](/backend/knowledge-cards/api-contract/) 的關係是後者的一個具體切面：錯誤格式一旦被消費者依賴，變更成本跟正常回應完全相同，因此它需要跟成功路徑同等的演化設計。

## 概念位置

這份標準的定位寫在規範裡：problem details 是**補充** HTTP status code、而非取代。這句話決定了它在錯誤格式光譜上的位置——讀 status 的角色（中介層的 retry 與快取、監控的錯誤率、SDK 的例外轉換）拿到粗分類，讀 body 的角色拿到細節，兩層對同一個錯誤說一致的話。相對地，讓 status 恆定為 200 而把錯誤全放進酬載的做法，會讓前一組角色失明（該取捨見 [錯誤格式之爭](/backend/11-api-design/error-format-debate/)）。錯誤格式跟 [Idempotency Key](/backend/knowledge-cards/idempotency-key/) 有一個具體接點：冪等衝突需要在錯誤模型裡佔一個可程式化分辨的位置，而 `type` URI 正是給它的落點。

欄位清單之外，這份標準真正的價值在兩個設計條款，而它們最常在「照抄五個欄位」時被漏掉。`type` 用 URI 而非字串 enum，把錯誤種類的命名空間外部化，跨團隊與跨服務不撞名。「client MUST ignore unknown extensions」是向前相容的演化條款——服務端可以增加欄位而不破壞既有消費者，等同錯誤模型的開放封閉原則。IANA 另建了一份公用 problem type 的登記表，補上前一版標準（RFC 7807）留下的生態碎片化。

## 可觀察訊號與例子

該採用的訊號：新建的 HTTP API、還沒有既有錯誤格式被依賴、且希望拿到現成的工具生態。既有 API 已有自訂格式且被大量依賴時，換格式本身就是一次 breaking change，務實做法是把上述兩個條款補進自訂格式，而非搬家。

缺這兩個條款的觀察形態各不相同。命名空間缺席時，跨服務的錯誤碼會撞號，且錯誤碼寫成連續數字（`code: 1047`）時 grep 不到語意。演化條款缺席時，每次新增欄位都無法確認既有消費者安不安全，於是格式實際上凍住了——沒有人敢加欄位，錯誤資訊只好塞進 `message` 文字，而消費者開始 parse 那段文字，改字就成為破壞相容的變更。

## 設計責任

採用時要決定的是 `type` URI 的命名空間怎麼分配（按服務、按領域、還是按錯誤族），以及哪些資訊放 extension member。不採用時要承擔的是同樣兩件事的自建版本，並且盡早把「未知欄位請忽略」寫進文件。它保護的是寫下它之後才新增的欄位，因此晚寫不追溯保護已經發出去的那些——而正因為價值在往後，晚寫仍然值得補。

錯誤該分幾類、格式欄位怎麼設計的完整判準見 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)；跨風格的格式交鋒見 [錯誤格式之爭](/backend/11-api-design/error-format-debate/)。
