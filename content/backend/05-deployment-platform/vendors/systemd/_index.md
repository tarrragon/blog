---
title: "systemd"
date: 2026-05-01
description: "Linux init system、VM / 單機 service lifecycle"
weight: 3
tags: ["backend", "deployment", "vendor"]
---

systemd 是 Linux 主流 init system、承擔三個責任：service unit lifecycle（start / stop / restart / reload）、signal + journald + cgroups 整合、socket activation + timer（cron 替代）。設計取捨偏向「OS-level 整合 + 單機資源管理 + dependency graph」、適合 VM / bare metal 上單機服務、不需要 cluster orchestration 的場景。

對「VM / bare metal 服務管理、邊緣 / appliance、單機 lifecycle + journal + cgroups」這條路徑、systemd 是 Linux 主流選擇。

## 本章目標

讀完本章後、你應該能：

1. 寫 service unit file、配置 Type / Restart / ExecStart
2. 設計 signal handling + graceful shutdown
3. 用 journald + journalctl 查 logs
4. 設定 cgroups v2 resource limit
5. 用 socket activation / timer 替代 inetd / cron

## 最短路徑：5 分鐘把 systemd service 跑起來

```bash
# 1. 建 unit file（需 root 或 sudo）
cat > /etc/systemd/system/myapp.service <<'UNIT'
[Unit]
Description=My Application
After=network.target

[Service]
ExecStart=/usr/bin/myapp --config /etc/myapp/config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# 2. 啟用 + 啟動
systemctl daemon-reload
systemctl enable --now myapp

# 3. 驗證
systemctl status myapp
journalctl -u myapp -f
```

## 日常操作與決策形狀

### Unit file 設計

子議題：

- Unit type：service / socket / timer / target / mount / path
- Service Type：simple / forking / oneshot / notify / dbus
- Restart：no / on-failure / on-abnormal / always
- ExecStart / ExecStop / ExecReload
- 對應指令：`systemctl cat myapp.service`、`systemctl edit`

### systemctl 指令

子議題：

- Lifecycle：start / stop / restart / reload / enable / disable
- Status：status / is-active / is-enabled / list-units
- Reload after edit：daemon-reload
- 對應指令範例：`systemctl status myapp`、`systemctl list-units --failed`

### journald 日誌

子議題：

- 結構化日誌（kv pairs）
- journalctl filter（-u / --since / -p / -f）
- 對應 logging：persistent vs runtime journal
- 跟外部 log forwarder（Vector / Fluent Bit）對接

## 進階主題（按需閱讀）

### Signal handling + graceful shutdown

子議題：

- SIGTERM（default stop signal）/ SIGKILL（force kill after timeout）
- TimeoutStopSec：grace period
- 應用程式要 trap SIGTERM 做 cleanup
- 對應 [Platform lifecycle contract](/backend/05-deployment-platform/platform-lifecycle-contract/)（concept 通用）

### cgroups v2 + resource limit

子議題：

- CPUQuota / MemoryMax / IOWeight / TasksMax
- Slice unit（樹狀 resource 限制）
- 跟 Kubernetes 的 resource limit 對比（K8s 用 cgroups 但抽象更高）
- 對應指令：`systemd-cgls`、`systemd-cgtop`

### Socket activation

子議題：

- 用 .socket unit 持有 listening socket、service 啟動時繼承
- 啟動延遲：socket 一直在、service 按需起
- 替代 inetd
- 適合 occasional service / low-traffic

### systemd timer

子議題：

- .timer unit 替代 cron
- OnCalendar / OnUnitActiveSec / RandomizedDelaySec
- 跟對應 .service unit 配對
- 比 cron 強：journal log / dependency / 失敗 restart

### Portable services + systemd-run

子議題：

- systemd-run：ad-hoc 跑 transient unit
- Portable services：把 service + image 一起搬
- systemd-nspawn 容器（systemd 自家輕量容器）

### 跟 container 整合

子議題：

- 跑 podman container 在 systemd（quadlet / generators）
- Docker daemon 由 systemd 管
- K8s kubelet 由 systemd 管（cluster node）
- 對應 single-node container management

## 排錯快速判讀

### Service start failure

操作原則：先 `systemctl status`、再 `journalctl -u` 看 log。

```bash
systemctl status myapp                # 看 Active state + Main PID + 最近 log
journalctl -u myapp --since=-5m       # 最近 5 分鐘的完整 log
```

### Restart loop

操作原則：Restart 配置不當 + StartLimit 觸發。判讀：`systemctl status` 看 restart count + RateLimit。

### journald disk full

操作原則：journal storage 超 SystemMaxUse 設定。判讀：`journalctl --disk-usage`、`/etc/systemd/journald.conf` 設限。

### cgroup OOM

操作原則：MemoryMax 超過、系統 OOM kill。判讀：`journalctl -k` 看 kernel oom 訊息。

### Dependency 不對

操作原則：unit 依賴 network / db 但 After= 沒設。判讀：`systemctl list-dependencies myapp`。

## 何時改走其他服務

| 需求形狀                      | 改走                                                               |
| ----------------------------- | ------------------------------------------------------------------ |
| 多實例 cluster                | [Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)  |
| Container workflow 為主       | [Docker](/backend/05-deployment-platform/vendors/docker/) / Podman |
| Process supervisor（非 init） | supervisord / runit                                                |
| Cron-only 場景                | 純 cron / systemd timer                                            |
| Non-Linux（Windows / macOS）  | Windows Service / launchd                                          |
| 邊緣 K8s                      | K3s（systemd 上跑 K3s）                                            |

## 不在本頁內的主題

- 完整 unit file directive reference
- systemd internals（dbus / pid 1）
- 各 distro systemd 版本差異
- systemd-resolved / systemd-networkd 等其他 component

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                                        | 對 systemd 的對應                                                         |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [5.C9 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) | systemd 服務切換要靠 ExecStop / TimeoutStopSec / SIGTERM trap 等價 drain  |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)               | 小規模 VM 服務首選 systemd、跨規模升階到 K8s 時要保留 unit-level 回退腳本 |

**待補 systemd 案例**：大規模 fleet（HashiCorp Nomad 跟 systemd 整合）、IoT / edge appliance 案例、systemd portable services 落地案例。

## 下一步路由

- 上游概念：[5.1 container runtime](/backend/05-deployment-platform/container-runtime/)
- 平行 vendor：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)、[Docker](/backend/05-deployment-platform/vendors/docker/)
- 下游能力：[06 reliability](/backend/06-reliability/)（graceful shutdown）、[4 observability](/backend/04-observability/)（journald）
