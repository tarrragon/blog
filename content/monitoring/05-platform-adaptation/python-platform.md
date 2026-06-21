---
title: "Python 平台適配"
date: 2026-06-19
description: "GIL 與 threading、atexit 可靠性、subprocess 監控 — Python SDK 的平台特殊考量"
weight: 3
tags: ["monitoring", "platform", "python", "gil", "threading", "atexit"]
---

Python 的執行模型（GIL 限制並行、atexit 不保證執行、subprocess 獨立 process）讓監控 SDK 在 Python 環境中需要特別處理 flush 的執行方式、程序退出時的事件保存和子程序的監控。

## GIL 與 threading

Python 的 Global Interpreter Lock（GIL）讓同一時間只有一個 thread 執行 Python bytecode。SDK 的 flush 操作（HTTP POST 到 collector）如果在主 thread 執行，會阻塞主程式的其他工作。

SDK 端的適配：

在 daemon thread 中執行 flush。Daemon thread 在主 thread 結束時自動終止，不需要手動 join。SDK 的 flush 計時器在 daemon thread 中運行，buffer 的存取用 threading.Lock 保護。

GIL 對 SDK 的影響比想像的小：HTTP 請求是 I/O bound 操作，CPython 在等待 I/O 時釋放 GIL。所以 flush 的 HTTP POST 在 daemon thread 中執行時，主 thread 可以繼續工作。GIL 只在 CPU-bound 的操作上造成瓶頸 — SDK 的 buffer 操作和事件序列化是 CPU-bound 但耗時極短（微秒級），影響可忽略。

### asyncio 環境

Python 的 asyncio 程式（FastAPI、aiohttp）使用事件迴圈而非 threading。SDK 在 asyncio 環境中應該用 `asyncio.create_task` 而非 threading 執行 flush，避免在事件迴圈中阻塞。

SDK 可以在 init 時自動偵測是否在 asyncio 環境中（檢查 `asyncio.get_running_loop()` 是否存在），自動切換 flush 的執行方式。

## atexit 可靠性

`atexit.register` 在 Python 程序正常退出時執行註冊的清理函式。SDK 在 init 時註冊 atexit handler 做最後一次 flush。

atexit 不執行的場景：

- `os._exit()` 直接終止 process，跳過所有清理
- SIGKILL（`kill -9`）強制終止，作業系統直接回收 process
- 未處理的 fatal signal（SIGSEGV、SIGABRT）導致 crash

對於 SIGTERM 和 SIGINT，Python 預設會執行 atexit handler（前提是 signal handler 沒有被覆蓋）。SDK 可以額外註冊 `signal.signal(signal.SIGTERM, handler)` 確保在收到 SIGTERM 時觸發 flush。

實務影響：`os._exit()` 和 SIGKILL 導致的事件遺失無法避免。使用本地 persistence（[離線 buffer](/monitoring/03-sdk-design/offline-buffer/)）可以降低影響 — 事件在寫入本地檔案後，即使 process 被強制終止，下次啟動時仍可補發。

## 短生命週期腳本

SDK 的預設設計假設長期運行的 app — flush interval 定期觸發、daemon thread 持續運行、atexit 是最後防線。但 Python SDK 的一個重要場景是短命腳本（CI/CD hook、pre-commit hook、CLI 工具的子命令），生命週期可能 < 1 秒。這個場景下 SDK 的行為和長期 app 完全不同。

### 什麼會壞

**flush interval 來不及觸發**。預設 30 秒的 flush interval，但腳本在 200ms 內結束。計時器還沒觸發，buffer 中的事件從未送出。

**daemon thread 隨主 thread 結束**。SDK 用 daemon thread 執行 flush 計時器。Python 的 daemon thread 在最後一個非 daemon thread 結束時被殺 — 不會等待 daemon thread 完成當前工作。如果 flush 正在進行中（HTTP POST 送到一半），daemon thread 被殺，HTTP 請求中斷，事件丟失。

**atexit 的執行順序不確定**。atexit handler 在 daemon thread 被殺之後執行。如果 SDK 的 atexit handler 嘗試在 daemon thread 中 flush，會失敗（thread 已死）。atexit handler 必須在主 thread 中同步 flush。

### 正確的短命腳本模式

```python
from monitor import Monitor

Monitor.init(endpoint="http://localhost:9090/v1/events", app="my-hook")

# 做事...
Monitor.event("hook.run", {"hook": "branch-check"})

# 結束前必須呼叫 close
Monitor.close()  # close 內同步 flush，不依賴 daemon thread
```

`close()` 是唯一可靠的 flush 時機。`close()` 的實作在短命腳本場景下必須：

1. **同步執行 HTTP POST**，不委託給 daemon thread — 主 thread 呼叫 `close()` 時直接在當前 thread 送出
2. **設 HTTP timeout** — 短命腳本不能等太久，3 秒的 timeout 是合理的
3. **flush 失敗時靜默放棄** — 短命腳本的主要職責不是監控，SDK 失敗不應影響腳本的 exit code

`atexit` 仍然註冊，作為開發者忘記呼叫 `close()` 的備份。但 atexit 是 best-effort — 在 `os._exit()` 和 SIGKILL 下不執行。

### flush interval 在短命腳本中的角色

flush interval 對短命腳本無意義 — 腳本在第一次 interval 觸發前就結束了。SDK 可以偵測「init 到 close 的間隔 < flush interval」的模式，在 debug log 中提示開發者考慮降低 interval 或直接依賴 `close()` flush。

但不建議把 flush interval 設為 0（停用）— 同一個 SDK 設定可能同時用於長期 app 和短命腳本，interval 對長期 app 仍然有用。

## Subprocess 監控

Python 程式中的 `subprocess.Popen` 啟動的子程序是獨立的 process，不共享 SDK 的 buffer 和網路連線。子程序的錯誤和事件需要獨立的監控機制。

兩種方式：

**子程序獨立初始化 SDK**：子程序的 Python 腳本自己呼叫 `Monitor.init()`，獨立送事件到 collector。適合子程序是長時間運行的 Python 程式。

**父程序代理**：父程序讀取子程序的 stdout/stderr，從輸出中解析事件（子程序用約定格式印出事件），父程序的 SDK 代理送出。適合子程序是短命的腳本或非 Python 程式。

## 下一步路由

- Go 平台的適配 → [Go 平台適配](/monitoring/05-platform-adaptation/go-platform/)
- 跨平台 timestamp 一致性 → [跨平台 timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)
- 離線 buffer 策略 → [模組三 離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)
