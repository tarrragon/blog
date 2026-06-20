---
title: "容器化資源設計"
date: 2026-06-20
description: "Container 的 memory / CPU / 磁碟限制設計 — 資源限制設太緊 OOMKill、設太鬆擠壓其他服務、overlay filesystem 的 I/O 影響"
weight: 1
tags: ["devops", "capacity-planning", "container", "docker", "resource-limit", "oomkill"]
---

Container 的資源限制是容量規劃在容器化環境的落地。每個 container 設定 memory limit、CPU limit 和磁碟 I/O 控制，確保單一 container 不會吃光 host 資源影響其他服務。限制設太緊觸發 OOMKill 或 CPU throttle，設太鬆等於沒有限制。

## Memory 限制設計

### 觀察 baseline

在限制之前先觀察服務的真實記憶體使用。用 `docker stats` 看 container 的 MEM USAGE，跑至少 24 小時涵蓋日常操作和定期 job（降採樣、清理）。

Baseline 包含：

- 應用程式本身的 heap + stack
- Runtime 開銷（Go 的 GC metadata、JVM 的 metaspace、Python 的 interpreter）
- 內嵌資料庫的 page cache（如 SQLite 的 `PRAGMA cache_size`）
- HTTP server 的連線 buffer

### 設定 limit

```text
Memory limit = baseline peak × 1.5（安全係數）
```

安全係數 1.5 是經驗值 — 預留 burst 時的記憶體波動（如大 batch 的 JSON 反序列化、查詢結果集暫存）。安全係數太大浪費資源、太小在 burst 時 OOMKill。

### OOMKill 排查

OOMKill 的症狀是 container 突然消失、沒有 application log。排查步驟：

```bash
docker inspect <container> | jq '.[0].State.OOMKilled'
# true = 被 OOM killer 終止

dmesg | grep -i oom
# kernel log 中的 OOM 記錄、包含被殺的 process 和當時的記憶體使用
```

OOMKill 後的處理：提高 memory limit，或找出記憶體使用異常的原因（memory leak、unbounded cache、大結果集查詢）。

### 不同 runtime 的記憶體特性

| Runtime | 特性                             | 注意事項                                                                  |
| ------- | -------------------------------- | ------------------------------------------------------------------------- |
| Go      | GC 自動管理、GOGC 控制觸發頻率   | `GOMEMLIMIT` 讓 Go runtime 感知 container 的 memory limit、避免 GC 不積極 |
| JVM     | heap + metaspace + native memory | 設 `-Xmx` 小於 container limit（留空間給 native memory）                  |
| Python  | 無 GC 上限、依賴 OS              | 大 DataFrame / 大 dict 可能瞬間超限                                       |
| Node.js | V8 heap limit 預設 ~1.5GB        | 設 `--max-old-space-size` 配合 container limit                            |

## CPU 限制設計

### `--cpus` vs `--cpu-shares`

| 設定               | 行為                                            | 適用場景                            |
| ------------------ | ----------------------------------------------- | ----------------------------------- |
| `--cpus=0.5`       | Hard limit — 最多用 0.5 個 CPU core             | 嚴格隔離、多 container 共用一台主機 |
| `--cpu-shares=512` | Relative weight — 和其他 container 按比例分 CPU | 彈性分配、host 閒置時可用更多       |

### CPU throttle 症狀

CPU throttle 不會 crash（和 OOMKill 不同）。症狀是延遲上升 — request 處理時間從 10ms 變成 100ms，因為 container 的 CPU time 被 cgroup 暫停。

```bash
cat /sys/fs/cgroup/cpu/cpu.stat
# nr_throttled: 被限制的次數
# throttled_time: 累計被暫停的時間（奈秒）
```

I/O bound 的服務（如監控 collector — 主要時間花在 SQLite 寫入和 HTTP 收發）通常不需要嚴格 CPU 限制。CPU 只在查詢處理（JSON 反序列化、聚合計算）時短暫使用。

## 磁碟 I/O 考量

### Overlay filesystem 的寫入放大

Docker 的 overlay2 storage driver 把 container 的寫入操作分層管理。每次寫入新檔案或修改檔案，overlay 在上層（upper layer）建立副本再修改（copy-on-write）。對 SQLite 這類頻繁 fsync 的嵌入式資料庫，overlay 層增加 20-40% 的寫入延遲。

### Volume mount 繞過 overlay

把需要高 I/O 效能的目錄掛載為 host volume（`-v /host/path:/container/path`），寫入直接到 host 檔案系統、繞過 overlay。

適用 volume mount 的場景：

- 嵌入式資料庫的資料目錄（SQLite、BoltDB）
- 需要持久化的 log 檔案
- 大量小檔案寫入（cache 目錄）

不適用 volume mount 的場景（用 overlay 即可）：

- 暫存檔（處理完就刪）
- 只讀的設定檔（`-v config:/config:ro`，overlay 讀取開銷小）

### tmpfs mount

記憶體中的暫存目錄，不寫磁碟。適合不需要持久化的高頻寫入（如 SDK 的離線 buffer、session 暫存）：

```bash
docker run --tmpfs /tmp:size=64m ...
```

## Health Check 設計

Container 的 health check 告訴 orchestrator「這個 container 是否正常運作」。Process 活著但 HTTP 不回應的場景（deadlock、資源耗盡）只靠 process 監控抓不到。

### Dockerfile HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q --spider http://localhost:8080/health || exit 1
```

### Docker Compose healthcheck

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

`start_period` 是啟動寬限期 — container 啟動後前 10 秒的 health check 失敗不算。避免服務還在初始化時就被標記 unhealthy。

### Kubernetes probe 對應

| Docker      | Kubernetes     | 用途                                                    |
| ----------- | -------------- | ------------------------------------------------------- |
| HEALTHCHECK | livenessProbe  | container 是否活著（失敗 → 重啟）                       |
| —           | readinessProbe | container 是否準備好接流量（失敗 → 從 service 移除）    |
| —           | startupProbe   | container 是否完成啟動（失敗 → 重啟、比 liveness 寬容） |

Docker 的 HEALTHCHECK 只有一種、等同 Kubernetes 的 livenessProbe。Kubernetes 的 readinessProbe 和 startupProbe 在 Docker 單機環境沒有對應物 — 它們是多 pod 場景下的流量控制機制。

## 下一步路由

- 監控 collector 的 container 部署實例 → [Container 部署設計](/monitoring/04-collector/container-deployment/)
- 服務探活與自動恢復 → [DevOps 服務探活](/devops/04-service-health/)
- 負載平衡設計 → [DevOps 負載平衡](/devops/01-load-balancing/)
