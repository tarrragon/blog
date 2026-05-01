---
title: "4.11 Telemetry Pipeline 架構"
date: 2026-05-01
description: "把 log / metric / trace 的 agent → collector → ingest → storage → query 分層治理"
weight: 11
---

## 大綱

- 為何要把 telemetry 當 pipeline 看：每層有獨立失敗模式與成本邊界
- 分層責任：agent（採集）、collector（聚合 / 轉換）、ingest（寫入 buffer）、storage（保留 / 查詢）、query（dashboard / alert）
- buffer 與 backpressure：collector 端緩衝、ingest 滿時的降級策略
- OpenTelemetry Collector 的角色：vendor-neutral 中介層
- pipeline 失敗時的 graceful degradation：訊號斷一層、其他層仍可用
- multi-tenant 環境的 quota / 隔離
- 跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是治理輸入、4.11 是 pipeline 執行
- 反模式：pipeline 是黑盒、無 self-monitoring；agent 直連 vendor 無 collector 中介；ingest 滿時直接 drop 無告警

## 判讀訊號

- 訊號間歇性消失、無法判斷是 pipeline 還是 service 問題
- agent 升版需要 service 重啟、運維成本高
- ingest 拒收（429）發生時、應用層無感
- 切換 vendor 需要改所有 service 的 instrumentation
- pipeline 自身無 SLI、健康度靠經驗判斷

## 交接路由

- 04.7 cardinality / cost：pipeline 各層的 quota
- 05 部署：collector 部署形態（DaemonSet / sidecar / gateway）
- 06.4 chaos：pipeline 故障模擬作為 chaos 場景
- 04.15 cost attribution：pipeline 各層的成本歸屬
