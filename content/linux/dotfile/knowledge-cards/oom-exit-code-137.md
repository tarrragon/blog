---
title: "OOM killer 與退出碼 137"
date: 2026-07-08
description: "程序或 container 被無預警砍掉、退出碼是 137、或編譯 / 測試在記憶體吃緊時突然死掉、要判斷是不是記憶體不足時回來讀"
weight: 54
tags: ["linux", "container", "memory", "debug", "knowledge-cards"]
---

退出碼 137 代表程序被 SIGKILL（訊號 9）終止：Unix 慣例是被訊號殺掉的退出碼等於 128 加訊號編號，128 + 9 = 137。最常見的來源是 OOM killer——記憶體用盡時，核心（或 container 的 cgroup 記憶體控制器）挑一個程序送 SIGKILL 回收記憶體。看到 137，第一個假設就是「記憶體到頂被砍」，而不是程式自己出錯退出。container 環境裡的資源隔離陷阱不只發生在記憶體，掛載卷的 owner 也有類似的層級落差，見 [Docker named volume 掛載點 owner](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)。

## 概念位置

相鄰的資源隔離概念見 [Docker named volume 掛載點 owner](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)。

## OOM killer 怎麼運作

Linux 在實體記憶體加 swap 都不夠時觸發 OOM killer，依 `oom_score`（吃多少、重不重要）挑一個程序直接 SIGKILL、不給它清理的機會。這跟程式正常結束或收到可捕捉的訊號不同——SIGKILL 不能被攔截或忽略，程序當場消失。在 container 裡還多一層：cgroup 的記憶體上限（`--memory`）被打到時，是這個 container 的 cgroup 觸發 OOM、砍 container 內的程序，host 整體可能還很閒。

## 為什麼可用量比設定的上限小

給 container 設 `--memory=256m` 不等於裡面的程式有 256 MB 可用。cgroup 計的是這個 group 的**總量**——包含 runtime（如 node、JVM）本身的常駐佔用、page cache、堆疊。runtime 底噪先吃掉一截，程式真正能配的空間就少於設定值，且這個差額完全取決於用哪個 runtime、其常駐多大。所以「256m 上限下配到約 200 MB 就觸頂」是那個環境的 runtime 底噪決定的、不是通則。

## 判讀訊號

- **退出碼 137、無 stack trace、程序當場消失** → OOM killer 的簽名。查 `dmesg` / journal 找 `Out of memory: Killed process` 確認。
- **container 退 137、host `free` 看起來還有餘** → cgroup 記憶體上限被打到、不是 host OOM。調高 `--memory` 或降低工作負載峰值。
- **編譯 / 測試在記憶體尖峰時偶發被砍** → build 的瞬間峰值超過可用記憶體。RAM 留餘裕、配 swap 當緩衝、或降平行度（`make -j` 調小）。

## 邊界

不是所有 137 都是 OOM——任何來源的 SIGKILL 都給 137，例如 `docker stop` 超時後強殺、`kill -9`、orchestrator 的 liveness 逾時。判別靠 `dmesg` 有沒有 OOM 記錄：有就是記憶體、沒有就往其他 SIGKILL 來源查。記憶體規劃的完整取捨（peak 抓法、swap 當安全網）見 [遠端 agent 工作機選型](/linux/tools/remote/agent-workstation-home-vs-vps/) 的 CPU/RAM 段。
