---
title: "Message Authentication"
date: 2026-07-27
description: "兩個系統用共享密鑰互相呼叫時，用來判斷驗證值保護到什麼範圍、撤銷粒度落在哪一層"
weight: 417
---

Message Authentication 的核心概念是用雙方共享的密鑰為訊息產生一段驗證值，接收方重算後比對，同時確認「訊息出自持有密鑰的一方」與「內容在傳輸中沒有被改過」。這段驗證值在多數 API 文件裡稱為 signature 或 MAC。它承擔的是來源與完整性，訊息本身照常明文傳輸；需要內容不可讀時要疊加 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 或 [At-Rest Encryption](/backend/knowledge-cards/at-rest-encryption/)，密鑰的保存與輪替接回 [Key Management](/backend/knowledge-cards/key-management/)。

## 概念位置

Message Authentication 位在 [Authentication](/backend/knowledge-cards/authentication/) 的機器對機器分支。人類身分驗證回答「這個人是誰」並依賴 session 或 token；訊息驗證回答「這個請求出自哪個系統、內容是否原封不動」，每個請求各自獨立驗證，沒有 session 狀態。它與 [Token Revocation](/backend/knowledge-cards/token-revocation/) 的差異在撤銷粒度：token 可以個別撤銷，共享密鑰的撤銷是換掉密鑰、影響所有使用該密鑰的呼叫方，因此屬於 [Secret Management](/backend/knowledge-cards/secret-management/) 的輪替範疇。

密鑰由雙方共同持有這件事界定了它的能力上限：兩端都能產生對方看來合法的值，因此驗證值本身證明不了是哪一端產生的。這個上限是原語的性質而非系統的性質——把驗證值交給獨立第三方記錄（時間戳權威、雙方都無法單方改寫的 append-only log）時，舉證能力回來了，但它來自那個見證機制而非驗證值。需要對第三方舉證或對不特定多方發佈可驗證憑證、又不想引入見證方時，要的是非對稱簽章，判斷標準見 [Non-repudiation](/backend/knowledge-cards/non-repudiation/)。

HMAC（Hash-based Message Authentication Code）是這個機制的主流建構。它把密鑰經內外兩層衍生後做兩次雜湊，堵住的是單層雜湊的一個性質：知道 `雜湊(密鑰 + 訊息)` 的結果與密鑰長度時，攻擊者不必知道密鑰本身，就能算出「訊息尾端再追加內容」的合法雜湊值。這個性質讓自行拼接的 `雜湊(密鑰 + 訊息)` 不能當驗證值用，要用函式庫提供的 HMAC 實作。

在 webhook 這類單向推送的場景裡，訊息驗證是身分保證的主要來源，其餘的推送契約（重試策略、payload schema、錯誤回應）見 [Webhook Protocol](/backend/knowledge-cards/webhook-protocol/)。

## 可觀察訊號與例子

需要正視訊息驗證設計的訊號是系統之間用共享密鑰互相呼叫，卻沒有明確定義驗證素材涵蓋哪些欄位。驗證素材指的是進入計算的那串內容——哪些欄位、以什麼順序、用什麼編碼串接起來。常見失效是它只涵蓋 body 而不含時間戳與路徑，攻擊者攔截後可以無限重放同一個請求，或把它改送到另一個端點。

驗證值涵蓋時間戳能限制重放窗口，前提是接收方確實檢查時間戳的新鮮度。時間戳進了驗證值但沒被檢查時，防重放的設計等於沒有生效 —— 攻擊者重放整包內容時驗證值仍然吻合。窗口長度與去重機制的取捨見 [Replay Attack](/backend/knowledge-cards/replay-attack/)，窗口的下界受 [Clock Skew](/backend/knowledge-cards/clock-skew/) 約束。攻擊者的重放與正常呼叫方的重試是兩個獨立問題，後者的收斂點在 [Idempotency Key](/backend/knowledge-cards/idempotency-key/)。

跨團隊對接時的高頻落差是雙方對驗證素材的定義不一致：欄位順序、分隔符、空請求時 payload 段落填什麼、時間戳的單位是秒或毫秒。這些差異在驗證值上只會表現成「對不起來」，錯誤訊息無法指出是哪一項。

## 設計責任

設計時要把驗證素材的組成寫成雙方共同的規格：涵蓋哪些欄位、串接順序、編碼方式、時間戳單位與有效窗口、輸出格式。規格明確之後，對接失敗才能逐項核對而非反覆重試。素材的逐項拆解與兩端對齊的實作見 [HMAC 簽章對接](/work-log/hmac_signature_field_alignment/)，規格與重放窗口在對接階段的收斂判讀見 [7.35 簽章對接的驗證收斂](/backend/07-security-data-protection/signature-integration-verification/)。

重算出的值要用等時比較來比對，一般的字串相等運算會由回應時間洩漏吻合前綴的長度，見 [Timing Attack](/backend/knowledge-cards/timing-attack/)。

密鑰要與應用程式分離配發，並納入輪替排程。配發本身要定什麼（這個交付動作能不能免掉、核發與審批看什麼、初次交付與登記）見 [7.32 機器憑證的配發](/backend/07-security-data-protection/machine-credential-issuance/)。密鑰隨程式一起發佈時，任何取得程式的人都能偽造合法請求，驗證機制的保護就消失了。憑證隨產出物發佈後被檢索、重用的實際後果見 [USAHERDS 2021 硬編碼憑證](/backend/07-security-data-protection/red-team/cases/edge-exposure/usaherds-cve-2021-44207-hardcoded-credential/)。

監控要能按原因分辨拒絕，因為每種原因指向不同的處置：驗證值不符指向規格或密鑰不一致，時間戳過期指向時鐘偏移。做了識別值去重的系統還有第三種——識別值重複，而它是三者裡唯一需要再分一次的：絕大多數來源是推送方的正常重試，判別要看來源位址與時間分布，見 [Replay Attack](/backend/knowledge-cards/replay-attack/)。把這幾種併成一個「驗證失敗」計數時，事件當下無法從監控判斷該往哪個方向查。
