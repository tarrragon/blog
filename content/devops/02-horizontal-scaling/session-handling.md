---
title: "Session 處理"
date: 2026-07-03
description: "多實例下要決定用戶登入狀態怎麼放時，比較 sticky session、外部 session store、無狀態 token 三種途徑，以及剛寫完就要讀到的 session 一致性怎麼保證"
weight: 2
tags: ["devops", "horizontal-scaling", "session", "jwt", "read-after-write"]
---

Session 處理有三種途徑，各自把「用戶登入狀態放哪」解成不同形狀：綁在某台實例上（sticky）、放進共享的外部儲存（session store）、或根本不存在伺服器端（無狀態 token）。這三種對水平擴展的友善度差很多——sticky 最省事但破壞無狀態，session store 讓實例對等但多一個共享依賴，無狀態 token 徹底無狀態但撤銷困難。選哪一種，決定了水平擴展時 session 這塊會不會變成綁手綁腳的地方。

## Sticky session：綁實例，最省事也最受限

Sticky session 把同一個用戶的 session 綁定到某台實例，session 資料就存在那台的記憶體裡。它最省事——不用改應用、不用外部依賴，登入狀態放本機就好。代價是它直接破壞無狀態：那台實例掛了、被縮容、或被重啟，綁在上面的 session 全部消失，那些用戶要重新登入。負載也會不均，因為熱門 session 集中在某幾台。sticky 的完整取捨在 [負載分散演算法](/devops/01-load-balancing/load-balancing-algorithms/) 的黏著段講過，這裡的重點是：它是三種途徑裡對水平擴展最不友善的，通常是暫時的過渡、不是目標狀態。

## 外部 session store：實例對等，但 session 是 hot row

外部 session store 把 session 從實例本地移到一個共享的儲存，每個實例都無狀態、任何實例都能讀到任何用戶的 session。這讓實例真正對等，是水平擴展下 session 的主流做法。（歷史上還有第四種做法：把 session 在所有實例之間互相複製，讓每台都持有全部 session。它早被外部 store 取代，因為複製流量隨實例數平方成長、擴到一定規模就撐不住——外部 store 用「一份共享」取代「每台一份」，正是為了避開這個。）但這裡有一個選型陷阱：session 是典型的高頻更新資料（每個請求可能都在刷新它的過期時間），放進 SQL 資料庫當一般資料表，會在那幾行 session 上撞出嚴重的鎖競爭——它是典型的 hot row 場景。

所以 session store 通常選鍵值儲存或快取（如 Redis、DynamoDB 這類支援原子操作的）、而不是 SQL。它們的資料模型正好適合「用一個 key 快速讀寫一個 session、高頻更新、不需要跨行交易」，避開了 SQL 在 hot row 上的鎖競爭。這條選型判斷延伸到 [Shared storage 選型](/devops/02-horizontal-scaling/shared-storage-selection/)——高頻的鍵值狀態跟結構化的查詢狀態，適合的儲存不一樣。

## 無狀態 token：不存伺服器端，但撤銷困難

無狀態 token（如 JWT）把 session 資料簽進 token 本身，發給客戶端隨每個請求帶回來，伺服器端完全不存 session。這是最徹底的無狀態——任何實例收到請求，驗證 token 簽章就知道用戶是誰，不必查任何共享儲存，連 session store 這個依賴都省了。

徹底無狀態的代價在撤銷跟大小。撤銷困難是最關鍵的：token 一旦簽發，在它過期之前都有效，伺服器端沒有一個「登出」按鈕能立刻讓它失效——因為伺服器根本不存它的狀態。要提前撤銷（用戶登出、帳號被停用）就得額外維護一個撤銷清單，那又把無狀態的好處吃掉一部分。大小是另一個代價：token 隨每個請求傳輸，塞太多資料會讓每個請求都變重，所以 token 只適合放少量、非敏感的識別資訊，不能當通用的 session 資料容器。無狀態 token 適合「短期有效、不需要即時撤銷」的場景，需要即時登出、需要存較多 session 資料的，還是走 session store。

## Session 一致性：剛寫完要讀得到

三種途徑之外，session 還有一個一致性問題會在水平擴展、讀寫分離後浮現：剛寫完的資料，馬上讀要讀得到（read-after-write）。當讀路徑走了資料庫的唯讀副本、而副本有複製延遲時，一個用戶剛更新完 session（或剛下單、剛改了餘額），下一個請求若打到副本，可能讀到還沒同步過來的舊資料。

解法是選擇性地路由，而不是把所有讀都無差別送回主庫：用一個 session token 標記「這個 session 剛寫過」，在複製延遲的那個時間窗內（幾秒），把它的讀強制走主庫；過了窗、或本來就容忍稍舊資料的讀（看別人的公開資料、看報表），走副本就好。session 一致性因此是按查詢分類的——不可容忍舊資料的（剛寫完查自己、餘額確認）走主庫，容忍的走副本。這個補丁要花多少工，其實取決於底層的複製延遲有多大，而那是 [Shared storage 選型](/devops/02-horizontal-scaling/shared-storage-selection/) 的 replication 架構決定的。

## 下一步路由

- 高頻鍵值 vs 結構化查詢 vs 大檔，各放哪種共享儲存 → [Shared storage 選型](/devops/02-horizontal-scaling/shared-storage-selection/)
- 把 session 從實例本地移出去，是無狀態設計的一部分 → [Stateless 設計原則](/devops/02-horizontal-scaling/stateless-design/)
- sticky session 的黏著代價與演算法 → [負載分散演算法](/devops/01-load-balancing/load-balancing-algorithms/)
