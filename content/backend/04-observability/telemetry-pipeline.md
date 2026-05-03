---
title: "4.11 Telemetry Pipeline 架構"
date: 2026-05-01
description: "把 log / metric / trace 的 agent → collector → ingest → storage → query 分層治理"
weight: 11
---

## 大綱

- 為何要把 telemetry 當 pipeline 看：每層有獨立失敗模式與成本邊界
- 分層責任：agent（採集）、collector（聚合 / 轉換）、ingest（寫入 [buffer](/backend/knowledge-cards/buffer/)）、storage（保留 / 查詢）、query（dashboard / alert）
- [buffer](/backend/knowledge-cards/buffer/) 與 [backpressure](/backend/knowledge-cards/backpressure/)：collector 端緩衝、ingest 滿時的降級策略
- OpenTelemetry Collector 的角色：vendor-neutral 中介層
- pipeline 失敗時的 graceful [degradation](/backend/knowledge-cards/degradation/)：訊號斷一層、其他層仍可用
- multi-tenant 環境的 quota / 隔離
- 跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是治理輸入、4.11 是 pipeline 執行
- 反模式：pipeline 是黑盒、無 self-monitoring；agent 直連 vendor 無 collector 中介；ingest 滿時直接 drop 無告警

## 概念定位

Telemetry pipeline 是把訊號從 service process 帶到查詢與告警面的資料路徑，責任是讓採集、轉換、寫入、儲存與查詢各層都有可觀測的邊界。

這一頁處理的是觀測系統本身的可靠性。當 pipeline 是黑盒，訊號消失時團隊需要額外排查服務是否真的沒事件，或 agent、collector、ingest、query 哪一層失效。

## 核心判讀

判讀 telemetry pipeline 時，先看每一層是否有健康訊號，再看滿載時是否能降級。

重點訊號包括：

- agent、collector、ingest、storage、query 是否各自有 SLI
- buffer 與 backpressure 是否能保住高價值訊號
- multi-tenant quota 是否能隔離單一服務爆量
- collector 是否保留 vendor-neutral 的轉換空間

## 判讀訊號

- 訊號間歇性消失、需要人工判斷是 pipeline 還是 service 問題
- agent 升版需要 service 重啟、運維成本高
- ingest 拒收（429）發生時、應用層無感
- 切換 vendor 需要改所有 service 的 instrumentation
- pipeline 自身無 SLI、健康度靠經驗判斷

## 交接路由

- 04.7 cardinality / cost：pipeline 各層的 quota
- 05 部署：collector 部署形態（DaemonSet / sidecar / gateway）
- 06.4 chaos：pipeline 故障模擬作為 chaos 場景
- 04.15 cost attribution：pipeline 各層的成本歸屬
