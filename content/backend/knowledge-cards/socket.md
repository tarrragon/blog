---
title: "Socket"
date: 2026-04-23
description: "說明 network socket 如何成為 application 與網路之間的資料傳輸邊界"
weight: 132
---

Socket 的核心概念是「application 和網路連線之間的資料讀寫端點」。HTTP、database driver、broker client 與自訂 TCP protocol 最後都會透過 socket 讀寫資料，因此 socket 行為會影響 timeout、連線池、buffer 與資源耗盡風險。 可先對照 [HTTP Client](/backend/knowledge-cards/http-client/)。

## 跟其他概念的關係

Socket 位在 application runtime、作業系統與網路之間。上層通常看到的是 [HTTP client](/backend/knowledge-cards/http-client/)、database client 或 [broker](/backend/knowledge-cards/broker/) client；底層則由 socket 負責連線、讀取、寫入與關閉。

## 可觀察訊號與例子

系統需要理解 socket 的訊號是外部依賴變慢時，application 的連線數、等待時間與資源使用同步上升。付款 API response 變慢時，HTTP client 可能佔住更多 socket；如果 timeout 太長，worker 會把時間花在等待網路回應。

## 判斷條件與後果

每一個等待網路回應的 socket 都佔著一條連線與一個檔案描述符，同步模型下還佔著一個 worker，所以外部依賴變慢時，socket 的設定決定 application 的資源被佔住多少、多久。沒有連線數上限時，下游越慢，同時開著的連線越多，直到檔案描述符用完；read / write timeout 設得長時，worker 把時間花在等待回應，能處理新請求的 worker 變少；沒有 [idle timeout](/backend/knowledge-cards/idle-timeout/) 時，閒置連線一直佔著資源，或被中間的網路設備單方面切斷，下一次使用時才收到 reset；不用 [connection pool](/backend/knowledge-cards/connection-pool/) 時，每個請求都重新建立連線，握手的耗時加在每一次呼叫上；[buffer](/backend/knowledge-cards/buffer/) 太小時一次回應要分多次讀取，太大時每條連線佔的記憶體乘上連線數；關閉流程漏掉錯誤路徑時，那些 socket 沒有被關閉，檔案描述符隨時間洩漏。連線數、timeout、reset、重連次數與下游 latency 是這幾項設定開始失效時最先變化的觀測值。
