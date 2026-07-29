---
title: "Authorization Scope（授權範圍）"
tags: ["身分安全", "Authorization", "OAuth", "Security"]
date: 2026-07-29
description: "把一次授權寫成可協商的單位時，用來判斷顆粒由誰決定、授予的範圍與實際用到的範圍差多少、以及事後收斂為什麼比事前貴"
weight: 424
---

Authorization Scope 的核心概念是把一次授權表達成一組具名的範圍，讓「這個呼叫方獲准做什麼」在授予當下就寫成可列舉的清單。它與 [authorization](/backend/knowledge-cards/authorization/) 的分工是：authorization 回答單一請求該不該放行，scope 是那個判斷所依據的授予內容本身。OAuth 系列協定用 `scope` 這個參數承載它，而同樣的結構在 API key 的權限勾選、雲平台的角色政策、資料庫的授權語句裡都成立。

## 概念位置

Scope 的顆粒由**發行方**決定，這是它與 [least-privilege](/backend/knowledge-cards/least-privilege/) 之間最常被忽略的落差。最小權限是使用方的原則，而使用方能挑的選項只有發行方提供的那幾個——想只給讀取而選項只有「全部」時，最小權限這條原則在這一格無法落實。判斷自己被卡在哪一側，看的是需求描述得出來的動作與可勾選的項目之間差幾層。

自己就是發行方時（內部 API 多半如此）顆粒可以自己切，約束因此換成另一件事：重切 scope 要每個既有使用方跟著遷移，顆粒切錯是向後相容問題而非「沒得選」問題，處置見 [11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)。

授予的範圍與實際用到的範圍之間的差額，就是白白多承擔的暴露面，而它決定了發行方出事時傳導進來的半徑，收斂點見 [blast radius](/backend/knowledge-cards/blast-radius/)。這個差額在正常運作期間沒有任何徵兆——沒被用到的權限不會產生錯誤、不會拖慢回應、也不會出現在任何監控上。

Scope 與 [token revocation](/backend/knowledge-cards/token-revocation/) 解的是相鄰但不同的問題：scope 限制的是這張憑證能碰到什麼，撤銷處理的是它什麼時候失效。兩者獨立成立——範圍收得很緊的憑證仍需要撤銷路徑，而撤銷很快的憑證在有效期內仍然由 scope 決定它能做多少事。

## 可觀察訊號與例子

需要正視 scope 設計的訊號是整合被授予的權限清單與它實際呼叫過的端點對不起來。取一段時間的存取日誌按端點去重，沒被呼叫過的權限就是超出實際使用的部分。

發行方那一側的訊號是 scope 的名稱取自產品功能而非資源與動作（`admin`、`integration`、`full_access` 這類）。名稱裡看不出它涵蓋哪些資源與哪些動作時，使用方沒有辦法判斷自己需要的是哪一個，於是傾向勾選看起來一定夠用的那一個——這一步不需要判斷發行方當初為什麼這樣命名，觀察得到的就足以決定處置。

另一種形態是 scope 存在但顆粒只有兩級：全部或無。這一格常見於早期就開放 API 而權限模型尚未拆分的產品，使用方能做的取捨是接受粗顆粒、在自己這邊架一層降權的中間層、或換供應商。

## 設計責任

收斂 scope 的成本最低的時機是授予當下。整合上線之後縮小權限要協調對方調整程式碼，而這道協調成本讓「先給寬鬆權限之後再收」的收斂動作缺少發動的時機——沒有任何一方的既定工作會自然帶出它。成本次低的窗口是雙方本來就要動憑證的時刻：整合升級到新版介面、對方的憑證到期要重新授權、供應商事件之後的強制輪替。

作為發行方設計 scope 時，一個 scope 要對應一組可列舉的資源與動作，並讓讀與寫分屬不同的 scope。顆粒切得太細的代價是使用方要勾一長串、容易漏；切得太粗的代價由每一個使用方承擔，而他們沒有辦法自行修正。

代理場景的範圍是另一條判斷：一個系統代表某個使用者呼叫下游時，交集怎麼算、誰負責算、驗證方怎麼實測，都在 [7.33 委任型憑證](/backend/07-security-data-protection/delegated-credential-selection/)，本卡不重述。第三方整合的範圍與事件傳導半徑的關係見 [7.29 API 認證的信任邊界分層](/backend/07-security-data-protection/api-authentication-trust-boundaries/)，機器身分那一側的分域治理見 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)。
