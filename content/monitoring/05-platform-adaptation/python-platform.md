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

## Subprocess 監控

Python 程式中的 `subprocess.Popen` 啟動的子程序是獨立的 process，不共享 SDK 的 buffer 和網路連線。子程序的錯誤和事件需要獨立的監控機制。

兩種方式：

**子程序獨立初始化 SDK**：子程序的 Python 腳本自己呼叫 `Monitor.init()`，獨立送事件到 collector。適合子程序是長時間運行的 Python 程式。

**父程序代理**：父程序讀取子程序的 stdout/stderr，從輸出中解析事件（子程序用約定格式印出事件），父程序的 SDK 代理送出。適合子程序是短命的腳本或非 Python 程式。

## 下一步路由

- Go 平台的適配 → [Go 平台適配](/monitoring/05-platform-adaptation/go-platform/)
- 跨平台 timestamp 一致性 → [跨平台 timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)
- 離線 buffer 策略 → [模組三 離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)
