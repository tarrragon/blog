---
title: "Timing Attack"
date: 2026-07-27
description: "比對密鑰、token 或簽章的程式碼要判斷是否會由執行時間洩漏資訊時的依據"
weight: 423
---

Timing Attack 的核心概念是攻擊者從操作耗時的差異反推出他不該知道的資訊。它成立的條件是處理時間與秘密值相關：比對兩個字串時，多數語言的相等運算在第一個不同的位元組就返回，回應時間因此隨「前面猜對了幾個位元組」而變長，攻擊者逐位元組調整就能把猜測收斂。它針對的是 [Message Authentication](/backend/knowledge-cards/message-authentication/) 的驗證值、[Credential](/backend/knowledge-cards/credential/) 與 token 這類需要逐字比對的秘密。

## 概念位置

Timing Attack 是實作層的問題。[Message Authentication](/backend/knowledge-cards/message-authentication/) 的機制設計正確、[Key Management](/backend/knowledge-cards/key-management/) 也妥當的系統仍然可能在這一層洩漏，因為問題出在驗證程式碼怎麼寫。這使它在設計評審中容易被跳過：架構圖上看不到，只有讀到比對那一行才會發現。

它與其他側通道（快取時序、功耗、電磁）屬同一族，共同特徵是資訊從「計算過程的可觀察屬性」洩漏，而非從計算結果洩漏。網路服務的情境裡，遠端量測的雜訊大，可利用的通常是量級明顯的差異（例如提早返回與完整比對之間），而非奈秒級落差。

## 可觀察訊號與例子

需要正視的訊號是程式碼用一般相等運算比對秘密值：`==`、`equals`、字串比較函式。驗證簽章、比對 API token、檢查一次性密碼都落在這一類。

另一個訊號是錯誤路徑的耗時差異。帳號不存在時立刻返回、帳號存在但密碼錯誤時才跑完整的雜湊驗證，兩者的耗時差距讓攻擊者能列舉出哪些帳號存在，即使回應訊息刻意寫成一樣。

資料庫查詢也會產生同類差異。用秘密值當查詢條件時，索引命中與否的耗時差異可能對應到「這個值存不存在」。

## 設計責任

比對秘密值要用等時比較函式，多數語言的標準函式庫都提供：Node 的 `crypto.timingSafeEqual`、PHP 的 `hash_equals`、Go 的 `crypto/subtle.ConstantTimeCompare`、Python 的 `hmac.compare_digest`。這些函式比對完全部位元組才返回，耗時與內容無關。取用不到時的替代做法（兩側各再 HMAC 一次後比對）與「自己照文件寫才會踩、用對方 SDK 多半不會」的識別動作見 [7.35 簽章對接的驗證收斂](/backend/07-security-data-protection/signature-integration-verification/)。

認證流程的各條路徑要讓耗時一致。做法是無論帳號是否存在都執行同樣的驗證步驟，包含對不存在的帳號也跑一次雜湊運算，讓成功與失敗的成本相同。

判斷防護必要性時看的是該值能不能被反覆嘗試。有嚴格 [Rate Limit](/backend/knowledge-cards/rate-limit/) 且失敗會鎖定的路徑，逐位元組收斂需要的嘗試次數不可行；無限重試的內部端點則相反，那裡的風險比對外端點高。
