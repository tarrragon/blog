---
title: "Attack Surface"
date: 2026-04-24
description: "說明系統哪些對外暴露面會被先行探測與枚舉"
weight: 124
---

Attack surface 的核心概念是「攻擊者能先看見並嘗試互動的所有暴露面」。它不只包括 public API，也包括 admin route、webhook、diagnostic endpoint、upload path、debug flag、雲端資源與任何能被外部觸及的入口。 可先對照 [Public API Endpoint](/backend/knowledge-cards/public-api-endpoint/)。

## 跟其他概念的關係

Attack surface 是紅隊分析的起點。誰會來看、想拿什麼、能做到什麼程度由 [threat model](/backend/knowledge-cards/threat-model/) 承接，本卡只回答「哪裡先被看到」，因此會和 [Public API](/backend/knowledge-cards/public-api-endpoint/)、[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/)、[Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)、[webhook](/backend/knowledge-cards/webhook/) 與 [Security Misconfiguration](/backend/knowledge-cards/security-misconfiguration/) 一起被檢查。

## 可觀察訊號與例子

系統只要有多種入口、不同權限等級、可枚舉資源或可回傳診斷資訊，就需要明確盤點 attack surface。若某個 endpoint 可以被猜路徑、透過錯誤訊息推回內部結構，或因預設設定而暴露額外能力，這個 surface 就應該被優先標記。

## 判斷條件與後果

對外公開的 surface 是攻擊者能直接互動的入口，它的驗證、速率控制與回應內容各有對應的後果：驗證不足時任何人都能呼叫；沒有速率控制時，可列舉的資源能被逐一嘗試；回應帶出多餘的欄位或錯誤細節時，攻擊者從回應拼出內部結構。內部 surface 只有已經進到內部網路的呼叫者碰得到，所以對外 surface 在這三項上比內部 surface 嚴格。入口的用途、來源限制、資料回應與日誌責任分開定義時，盤點能逐項比對每個入口開放給誰、回傳什麼、留下什麼紀錄；只寫一句「這是內部用的」時，因預設設定而多暴露的能力沒有任何一項可以比對，盤點時看不出來。
