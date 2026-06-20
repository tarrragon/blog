---
title: "Container 部署設計"
date: 2026-06-20
description: "Docker 部署 collector 的設計 — SQLite 在 overlay filesystem 的 I/O 考量、volume mount、graceful shutdown、資源限制"
weight: 13
tags: ["monitoring", "collector", "docker", "container", "deployment", "sqlite"]
---

Container 部署讓 collector 完全隔離於 host 環境，開源使用者用 `docker run` 一行部署，不需要安裝 Go 或管理 binary 版本。但 SQLite 在 container 中有特殊的 I/O 和持久化考量 — overlay filesystem 的寫入延遲和 container 生命週期對資料持久性的影響需要在部署設計中處理。

## Dockerfile 設計

Multi-stage build 把編譯環境和執行環境分離。Build stage 用 Go 官方 image 編譯 binary，runtime stage 只包含 binary 和必要的 CA 憑證。

```dockerfile
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /collector ./cmd/collector

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata
COPY --from=build /collector /usr/local/bin/collector
RUN adduser -D -u 1000 monitor
USER monitor
EXPOSE 8080
ENTRYPOINT ["collector"]
```

最終 image 包含 Go binary（~15MB）+ alpine base（~7MB）+ ca-certificates，總大小目標 < 25MB。用 `scratch` 替代 `alpine` 可以再小 7MB，但失去 shell debug 能力。

## SQLite 在 Container 中的 I/O 考量

Docker 的 overlay2 storage driver 在每次 fsync 時經過 overlay 層。SQLite 的 WAL mode 依賴 fsync 確保寫入持久性 — 每筆 transaction commit 觸發一次 fsync。Overlay 層增加的延遲讓每筆 fsync 慢 20-40%（取決於 host 的 storage driver 和檔案系統）。

### Volume mount 繞過 overlay

把 SQLite 的資料目錄掛載為 host volume（`-v /host/data:/data`），SQLite 直接寫 host 檔案系統、繞過 overlay 層。寫入效能和同機部署的 binary 版本相當。

不用 volume mount 的風險：container 刪除時 overlay 層的資料一起消失。`docker rm` = 所有事件資料消失。即使只是 `docker run` 新版本的 image 也會建立新 container，舊 container 的資料不會自動遷移。

## Volume Mount 設計

兩個目錄分開掛載，職責和權限不同：

| Mount | Container 路徑 | Host 路徑（範例）  | 權限       | 內容                                           |
| ----- | -------------- | ------------------ | ---------- | ---------------------------------------------- |
| 資料  | `/data`        | `./monitor-data`   | read-write | SQLite DB + WAL + 匯出檔                       |
| 設定  | `/config`      | `./monitor-config` | read-only  | retention config + rule config + sensor config |

Container 內用非 root user（UID 1000）執行。Host 的 volume 目錄 ownership 需要對應：

```bash
mkdir -p monitor-data monitor-config
chown 1000:1000 monitor-data
```

## Graceful Shutdown

`docker stop` 送 SIGTERM → collector 收到後執行 shutdown 序列：

1. 停止接受新的 HTTP request
2. 等待 in-flight request 完成（context timeout）
3. Flush pending writes（channel 中排隊的事件）
4. SQLite WAL checkpoint（把 WAL 內容合併回主 DB 檔案）
5. 關閉 DB connection
6. 退出

`docker stop` 預設等 10 秒後送 SIGKILL。如果 WAL checkpoint 在大量未 checkpoint 的資料下需要超過 10 秒，Docker Compose 可以調 `stop_grace_period: 30s`。

SQLite 的 WAL 設計支援 crash recovery — SIGKILL 後 WAL 檔案仍在，下次開啟 DB 時自動 replay。但非 graceful shutdown 可能丟失 channel 中尚未寫入的事件（已收到 HTTP 202 但還在 buffer 中的事件）。

## 資源限制

| 資源   | 建議值（自用）    | 建議值（小團隊）  | 理由                                       |
| ------ | ----------------- | ----------------- | ------------------------------------------ |
| Memory | 256MB             | 512MB             | Collector + SQLite page cache + Go runtime |
| CPU    | 0.5 核            | 1 核              | I/O bound、CPU 通常不是瓶頸                |
| 磁碟   | volume mount 容量 | volume mount 容量 | 保留策略控制、和 host 磁碟共享             |

Memory 限制設太緊會觸發 OOMKill — container 突然消失且無 log。設定 memory limit 前先觀察 collector 的 baseline 記憶體使用（`docker stats`），再乘以 1.5 安全係數。Container 資源限制的通用設計原則見 [DevOps 容器化資源設計](/devops/05-capacity-planning/container-resource-design/)。

## Docker Compose 範例

```yaml
services:
  collector:
    image: tarrragon/monitor:latest
    ports:
      - "8080:8080"
    volumes:
      - ./monitor-data:/data
      - ./monitor-config:/config:ro
    environment:
      - MONITOR_STORAGE=sqlite
      - MONITOR_DB_PATH=/data/events.db
    restart: unless-stopped
    stop_grace_period: 30s
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

`restart: unless-stopped` 讓 container 在 crash 或 host 重啟後自動恢復。`healthcheck` 讓 Docker 偵測 collector 是否真的在回應 — 只有 process 活著但 HTTP 不回應的場景也會被標記為 unhealthy。

## 和同機部署的效能對照

| 指標                  | 同機 binary | Container + volume mount         | Container 無 volume（overlay） |
| --------------------- | ----------- | -------------------------------- | ------------------------------ |
| 寫入吞吐（Mac SSD）   | ~5,000/sec  | ~4,500/sec（-10%）               | ~3,000/sec（-40%）             |
| 寫入吞吐（Linux VPS） | ~3,000/sec  | ~2,700/sec（-10%）               | ~1,800/sec（-40%）             |
| 查詢延遲              | baseline    | baseline（volume = 直接讀 host） | +20%（overlay 讀取開銷小）     |
| 啟動時間              | < 100ms     | < 500ms（container 啟動開銷）    | 同左                           |
| 記憶體額外開銷        | 0           | ~10-20MB（container runtime）    | 同左                           |

Volume mount 後效能差異只有 ~10%（Go HTTP handler 的 overhead 大於 volume mount 的 overhead）。不用 volume mount 時 overlay fs 的 fsync 開銷顯著 — 寫入吞吐降 40%。

## 何時用 container、何時用 binary

| 場景                    | 建議             | 理由                              |
| ----------------------- | ---------------- | --------------------------------- |
| 開源使用者快速試用      | Container        | `docker run` 一行、不需裝 Go      |
| 長期自用部署            | Binary + systemd | 效能最佳、無 container overhead   |
| CI/CD 測試環境          | Container        | 可拋棄式、每次乾淨環境            |
| Kubernetes 部署         | Container        | pod spec 標準化                   |
| Raspberry Pi / 邊緣設備 | Binary           | 低資源環境避免 container overhead |

## 下一步路由

- SQLite 效能基準的詳細數字 → [SQLite Backend 效能基準](/monitoring/04-collector/sqlite-performance-baseline/)
- 可插拔 Storage Backend 架構 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- 容器化資源設計的通用原則 → [DevOps 容器化資源設計](/devops/05-capacity-planning/container-resource-design/)
- 服務探活和自動恢復 → [DevOps 服務探活](/devops/04-service-health/)
