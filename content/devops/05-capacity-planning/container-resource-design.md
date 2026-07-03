---
title: "容器化資源設計"
date: 2026-07-03
description: "把容量規劃落到容器上時，怎麼定 memory 與 CPU 限制不觸發 OOMKill 或 throttle、以及 overlay filesystem 對高頻寫入的 I/O 影響"
weight: 6
tags: ["devops", "capacity-planning", "container", "docker", "resource-limit", "oomkill"]
---

容器的資源限制是容量規劃在容器化環境的落地：把「這個服務需要多少資源」這個規劃結果，轉成每個容器的 memory limit、CPU limit 與磁碟 I/O 控制，確保單一容器不會吃光 host 資源、拖垮同一台上的其他服務。這條限制設太緊會觸發 OOMKill 或 CPU throttle、設太鬆等於沒設，所以限制值不是拍板一個數字，是從服務的真實用量推出來的。

## Memory 限制：從 baseline 推，不從猜

Memory limit 要從觀察到的真實用量推，不是憑感覺配。做法是先讓服務在沒有硬限制的情況下跑至少 24 小時、涵蓋日常操作與定期 job（降採樣、清理），用 `docker stats` 看容器的 `MEM USAGE` 抓出 baseline。這個 baseline 不只是應用程式本身的 heap 與 stack，還要含 runtime 的開銷（Go 的 GC metadata、JVM 的 metaspace、Python 的 interpreter）、內嵌資料庫的 page cache、以及 HTTP server 的連線 buffer——這些加起來才是服務真正佔用的記憶體。

有了 baseline，limit 常用的起點是峰值乘上一個安全係數：

```text
Memory limit = baseline peak × 1.5
```

1.5 是經驗值，預留 burst 時的記憶體波動（大 batch 的 JSON 反序列化、查詢結果集暫存）。係數太大浪費資源、太小在 burst 時 OOMKill。OOMKill 的症狀很好認也很難查——容器突然消失、沒有 application log，因為它是被 kernel 的 OOM killer 直接砍掉、應用來不及寫任何東西。確認是不是 OOMKill 靠兩條指令：

```bash
docker inspect <container> | jq '.[0].State.OOMKilled'   # true = 被 OOM killer 終止
dmesg | grep -i oom                                       # kernel log 裡被殺的 process 與當時記憶體
```

確認之後的處理是提高 limit、或找出記憶體異常的根因（memory leak、unbounded cache、大結果集查詢）——單純調高 limit 只在 baseline 估太低時對，遇到 leak 只是把 OOMKill 延後。

不同 runtime 的記憶體特性也要納入 limit 設計。Go 的 GC 自動管理、但預設不感知容器的 limit，要設 `GOMEMLIMIT` 讓它在逼近上限時積極回收；JVM 的 `-Xmx` 要設得小於容器 limit、留空間給 heap 之外的 native memory；Python 沒有 GC 上限、大 DataFrame 或大 dict 可能瞬間超限；Node.js 的 V8 heap 預設約 1.5GB、要用 `--max-old-space-size` 配合容器 limit。共通的原則是 runtime 若不感知容器 limit，就會在 host 還有記憶體、但容器已達上限時被 OOMKill。

## CPU 限制：hard limit 還是相對權重

CPU 限制有兩種語意，對應不同的隔離需求。`--cpus=0.5` 是 hard limit，最多用 0.5 個核心、超過就被 throttle，適合多容器共用一台主機、要嚴格隔離的場景；`--cpu-shares=512` 是相對權重，跟其他容器按比例分 CPU、host 閒置時可以用更多，適合彈性分配。選哪種取決於「這個容器的 CPU 用量需不需要一個硬上限」。

CPU throttle 跟 OOMKill 的差別是它不會 crash——症狀是延遲上升，請求處理時間從 10ms 變 100ms，因為容器的 CPU time 被 cgroup 暫停了。要確認有沒有被 throttle，看 cgroup 的統計：

```bash
cat /sys/fs/cgroup/cpu/cpu.stat   # nr_throttled 被限制次數、throttled_time 累計暫停奈秒
```

I/O bound 的服務（例如主要時間花在磁碟寫入與 HTTP 收發的收集器）通常不需要嚴格的 CPU 限制，CPU 只在查詢處理（JSON 反序列化、聚合計算）時短暫用到。對這類服務設太緊的 hard limit，反而會在偶爾的計算尖峰上製造不必要的延遲。

## 磁碟 I/O：overlay 的寫入放大

容器的磁碟 I/O 有一個容易被忽略的成本：overlay filesystem 的寫入放大。Docker 的 overlay2 storage driver 把容器的寫入分層管理，每次寫入或修改檔案，overlay 在上層建立副本再改（copy-on-write）。對 SQLite 這類頻繁 fsync 的嵌入式資料庫，這層 copy-on-write 會增加 20% 到 40% 的寫入延遲——一個看起來只是「換個存放位置」的決定，實際上改變了資料庫的寫入效能。

需要高 I/O 效能的目錄，用 host volume 掛載繞過 overlay：`-v /host/path:/container/path` 讓寫入直接落到 host 檔案系統。適合走 volume 的是嵌入式資料庫的資料目錄（SQLite、BoltDB）、要持久化的 log、大量小檔案的 cache 目錄；不需要的是暫存檔（處理完就刪）與唯讀設定檔（overlay 讀取開銷小）。若連磁碟都不需要碰、只要記憶體中的暫存，用 tmpfs：

```bash
docker run --tmpfs /tmp:size=64m ...
```

tmpfs 適合不需持久化的高頻寫入（SDK 的離線 buffer、session 暫存）——寫在記憶體、完全不碰磁碟、也不吃 overlay 的放大。

## 容器的健康檢查掛在探活模組

容器層的 health check（Dockerfile 的 `HEALTHCHECK`、Compose 的 `healthcheck`）告訴 orchestrator 這個容器是否正常運作，並用一段啟動寬限期（`start_period`）避免服務還在初始化就被判死。這一層的完整設計——health check 要探到多深、`HEALTHCHECK` 等同 Kubernetes 的哪種 probe、readiness 與 startup 在單機 Docker 為什麼沒有對應物——是 [模組四 服務探活](/devops/04-service-health/) 的主題，容器資源設計只需知道健康檢查是容器生命週期的一部分、跟資源限制一起構成「容器跑得穩」的條件。探到不健康之後的自動重啟、liveness 與 readiness 的語意分界，見 [模組四 Liveness 與 Readiness](/devops/04-service-health/liveness-vs-readiness/)。

## 下一步路由

- 資源限制值的上游——容量怎麼算出來 → [規模拐點判斷](/devops/05-capacity-planning/scaling-inflection-point/)
- 容器的健康檢查、probe 語意與自動重啟 → [模組四 服務探活](/devops/04-service-health/)
- 監控 collector 的容器部署實例 → [Container 部署設計](/monitoring/04-collector/container-deployment/)
