---
title: "OTel Collector 部署模式：agent / gateway / sidecar 與 pipeline 設計"
date: 2026-06-16
description: "說明 OpenTelemetry Collector 三種部署位置的責任分工、receivers/processors/exporters pipeline 設計，以及 collector 失效、記憶體壓力與 backpressure 的故障演練與容量邊界"
weight: 10
tags: ["backend", "observability", "opentelemetry", "collector", "telemetry-pipeline"]
---

> 本文是 [OpenTelemetry](/backend/04-observability/vendors/opentelemetry/) 的 vendor deep article，深化 overview「Collector 部署模式」段。指令於 2026-06-16 用 `otel/opentelemetry-collector-contrib:0.154.0` 在 docker 實機驗證。

OTel Collector 的核心責任是把「應用程式產生 telemetry」跟「telemetry 送到哪個 backend」這兩件事解耦：應用只負責用 OTLP 把資料吐給 collector，collector 負責接收、處理、轉發。部署這個 collector 的第一個決策是「它擺在哪裡」——同 host、集中 gateway、還是 pod sidecar——而非配置細節；這個位置決定了 buffer 能力、enrichment 時機與失效影響面。

## 問題情境：telemetry 直送 backend 的三個代價

應用程式直接用 vendor SDK 把 telemetry 送到後端，會在規模變大時撞到三個問題。第一是耦合：每個服務都寫死了某個 backend 的 endpoint 與認證，換 backend 要改所有服務重新部署。第二是缺乏 buffer：backend 短暫不可用時，telemetry 直接丟失，因為應用程式不會為了觀測資料保留重試佇列。第三是 enrichment 分散：每個服務各自加 resource attribute、各自做 sampling，標準難統一。

Collector 把這三件事收斂到一個中介層。應用只認 collector 的 OTLP endpoint，換 backend 只改 collector 配置；collector 有 queue 與重試；enrichment 與 sampling 在 collector 統一做。但這個中介層擺在哪裡，決定了它各自解掉多少。

## 核心概念：三種部署位置的責任分工

Collector 的部署位置分三種，差別在「離應用多近」與「聚合多少來源」。

Agent 模式把 collector 跟應用程式放在同一個 host 或同一個 K8s node（DaemonSet）。它的責任是做 local buffer 與 host 層 enrichment：應用透過 localhost 把 telemetry 吐給同機的 collector，延遲極低、不跨網路；collector 補上 host name、container id 這類只有在本機才知道的 resource attribute。agent 的價值是「離應用最近」，應用送出 telemetry 後就不必管後續，buffer 與重試由同機 collector 承擔。

Gateway 模式把 collector 集中部署成一個獨立的服務叢集，跨多個 agent 或多個應用接收 telemetry。它的責任是做需要全域視野的處理：tail-based sampling（要看完整 trace 才決定採不採）、跨來源的 routing（不同 telemetry 送不同 backend）、集中的 rate limit 與成本控制。gateway 的價值是「集中決策」，把只有匯流後才做得到的處理放在這一層。

Sidecar 模式在 K8s 把 collector 當成跟應用 pod 同生命週期的 sidecar container。它的責任跟 agent 相似（local buffer、pod 層 enrichment），差別在隔離粒度是 pod 而非 node：比 DaemonSet agent 更貼近單一 pod（共享 pod 網路、隨 pod 起停），適合需要 pod 級獨立配置或強隔離的場景，代價是每個 pod 都多一份 collector 的資源開銷。

實務上常見的是兩層組合：agent（DaemonSet）做 local buffer + host enrichment，再把資料送到 gateway 叢集做 tail sampling 與 routing。agent 解掉「離應用近、不丟資料」，gateway 解掉「需要全域視野的處理」，兩層各司其職。

## pipeline 模型：receivers / processors / exporters

不論擺在哪個位置，collector 的內部都是同一個 pipeline 模型：telemetry 從 receivers 進來、經過 processors 加工、由 exporters 送出。三者用 `service.pipelines` 依訊號類型（traces / metrics / logs）串接，下面這份配置在 docker 驗證過可正常啟動並端到端流通（`validate --config` 回傳 0、送 5 條 trace 後 debug exporter 完整輸出 spans）：

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 64
  batch:
    timeout: 5s
    send_batch_size: 1024
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [debug]
```

receivers 定義「資料怎麼進來」，OTLP（gRPC 4317 / HTTP 4318）是標準入口。processors 定義「資料怎麼加工」，順序有意義：`memory_limiter` 放最前面，先擋住記憶體爆掉；`batch` 放後面，把零散 span 攢成批次再送，降低下游請求數。exporters 定義「資料送到哪」，正式環境會是 OTLP 到 backend 或某 vendor exporter，這裡用 `debug` 驗證流通。service.pipelines 才是真正生效的接線：只有被掛進某個 pipeline 的元件才會運作，定義了卻沒掛進 pipeline 的元件不生效。

processor 順序是常見踩雷點。`memory_limiter` 要排在第一個，讓它在資料進入後續 processor 前就有機會審查與拒收；`batch` 排在它之後，因為如果 batch 先跑，telemetry 會先在 batch processor 累積成大批，等觸發記憶體限制時壓力已經更高、拒收效果下降。需要 sampling 時，head sampling 可以放 agent 層的 pipeline，tail sampling 必須放 gateway 層（它要匯流完整 trace），且同一 trace 的所有 span 要路由到同一個 gateway 實例（用 trace-id 維度的 load balancing exporter），否則各 gateway 節點各看片段、tail 決策仍不完整。

## Production 故障演練

Collector 失效的影響面取決於部署模式，這是選位置時要先想清楚的。agent 模式下，單一 node 的 collector 掛掉只影響該 node 的應用，且應用送往 localhost 失敗可以 fail-fast；gateway 模式下，gateway 叢集掛掉會影響所有上游 agent，因此 gateway 必須多副本 + 負載均衡，不能單點。演練時要分別注入「單 agent 掛」與「gateway 叢集不可用」，確認前者影響被局限、後者有 agent 層 buffer 兜著。

記憶體壓力是 collector 最常見的故障。telemetry 流入速度超過 exporter 送出速度時，資料在 collector 內累積、記憶體上升，沒有保護會 OOM 被 kill、整段 telemetry 全丟。`memory_limiter` processor 是這道防線，它定期（`check_interval`）檢查記憶體並用兩個閾值分級反應：記憶體超過軟上限（`limit_mib` 減去 `spike_limit_mib`）時強制觸發 GC 並開始拒收，給回收一個緩衝區間；超過硬上限（`limit_mib`）時全面拒收新資料。只設 `limit_mib`、不設 `spike_limit_mib` 是不完整的配置，等於沒有軟性緩衝、直接撞硬牆。演練時用高於 exporter 吞吐的速率灌資料，確認 memory_limiter 在軟上限就介入、collector 存活，而不是 OOM。

Backpressure 的傳遞要驗證到底。當 backend 變慢、exporter queue 滿，collector 的 OTLP receiver 會回壓給上游（gRPC 層用 resource-exhausted 拒收）。在 agent 模式這個回壓會傳到應用的 OTLP exporter，應用 SDK 的 queue 也會滿——此時 SDK 的反應取決於 exporter 配置，要確認 queue-full 策略設為 drop 而非 block，讓 telemetry 被丟棄而非阻塞業務執行緒（各語言 SDK 預設不同，不能假設一定是 drop）。演練要確認「backend 慢 → collector 回壓 → 應用丟 telemetry 但業務不受影響」這條鏈成立，避免觀測系統的壓力反噬主流程。

## Capacity / cost 邊界

agent 與 gateway 的成本曲線不同，選型要對著規模看。agent（DaemonSet）的成本是「每個 node 一份 collector」的固定開銷：node 多時總開銷隨 node 數線性成長，但每份 collector 只處理本機流量、單份負載可控。gateway 的成本是「集中叢集」：份數少但每份要扛匯流後的總流量，要按總 telemetry 吞吐量做容量規劃與水平擴展。

兩層架構的成本判讀是：agent 層用最小配置（夠做 buffer + enrichment 即可，`limit_mib` 設小），把重處理（tail sampling、大量 routing）集中到 gateway，讓 gateway 的擴展跟總流量綁定、agent 的開銷跟 node 數綁定。把 tail sampling 誤放在 agent 層是常見的成本錯誤——agent 看不到完整 trace、做不了正確的 tail sampling，還白白吃掉每個 node 的記憶體。

gateway 層的 processor 是攔截高 cardinality attribute 的有效位置：在 telemetry 流入 backend 前用 `attributes` / `transform` processor 把高 cardinality label（user id、request id 當 metric label）移除或降維，比讓它流到 backend 後才治理便宜。高 cardinality 的 attribute 會在下游 backend 炸開成本，是另一條要在 collector 攔截的成本線。這條跟 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/) 對齊。

## 整合 / 下一步

Collector 部署模式是 OTel 落地的第一個決策，它的下游是 sampling 策略與 backend 選型。決定了 agent + gateway 兩層後，tail sampling 的設計接到 gateway 層的 pipeline；exporter 指向哪個 backend 則回到 [何時改走其他服務](/backend/04-observability/vendors/opentelemetry/#何時改走其他服務) 的 vendor portability 判讀。

pipeline 的訊號治理與資料品質回到 [4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/) 與 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)；cardinality 攔截回到 [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)。

## 相關連結

- [OpenTelemetry 服務頁](/backend/04-observability/vendors/opentelemetry/)
- [4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/)
- [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)
- [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)
