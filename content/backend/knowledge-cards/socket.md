---
title: "Socket"
date: 2026-04-23
description: "說明 network socket 如何成為 application 與網路之間的資料傳輸邊界"
weight: 131
---

Socket 的核心概念是「application 和網路連線之間的資料讀寫端點」。HTTP、database driver、broker client 與自訂 TCP protocol 最後都會透過 socket 讀寫資料，因此 socket 行為會影響 timeout、連線池、buffer 與資源耗盡風險。

## 概念位置

Socket 位在 application runtime、作業系統與網路之間。上層通常看到的是 [HTTP client](../http-client/)、database client 或 [broker](../broker/) client；底層則由 socket 負責連線、讀取、寫入與關閉。

## 可觀察訊號與例子

系統需要理解 socket 的訊號是外部依賴變慢時，application 的連線數、等待時間與資源使用同步上升。付款 API response 變慢時，HTTP client 可能佔住更多 socket；如果 timeout 太長，worker 會把時間花在等待網路回應。

## 設計責任

Socket 相關設計要定義連線數上限、read / write timeout、[idle timeout](idle-timeout/)、[connection pool](../connection-pool/)、[buffer](../buffer/) 大小與關閉流程。操作上要觀察連線數、timeout、reset、重連次數與下游 latency，避免網路等待耗盡 application 的 worker 或檔案描述符。
