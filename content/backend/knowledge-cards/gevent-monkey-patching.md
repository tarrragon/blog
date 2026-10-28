---
title: "Gevent Monkey Patching（gevent 的猴子補丁）"
date: 2026-10-28
description: "Locust 的吞吐量從加壓一開始就不隨使用者數增加而 worker 的 CPU 很低、一個 worker 程序的 CPU 到頂，或要判斷某個 Python 函式庫是否會卡住 Locust 的 worker 時讀"
weight: 500
tags: ["backend", "performance", "load-test", "python", "knowledge-card"]
---

gevent 是 Python 的協程函式庫，它讓一個 Python 程序同時執行很多個 greenlet（輕量的協程）：一個 greenlet 等網路 I/O 時讓出執行權，其他 greenlet 接著跑。猴子補丁（monkey patching）是 gevent 讓既有程式碼也能這樣讓出執行權的做法：在程式執行期間，把標準函式庫裡會阻塞的函式（`socket`、`ssl`、`time.sleep`、`select` 這類）換成 gevent 的版本，換過之後，呼叫這些函式的程式碼不必改寫，等待時就會讓出執行權。Locust 的每個虛擬使用者是一個 greenlet，所以一個 worker 程序跑得了很多個使用者，前提是使用者的 I/O 經過被替換的函式；不成立時，worker 在受測服務還沒到上限之前就先卡住，是 [Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 的一種。

## 概念位置

greenlet 的切換由協程自己交出執行權觸發，不由作業系統搶佔：一個 greenlet 不呼叫會讓出的函式，其他 greenlet 就一直等。這帶來兩個邊界。第一個是 patch 管不到的 I/O：用 C 寫的擴充模組在編譯過的程式碼裡直接做網路呼叫，不經過 Python 的 `socket`，gevent 換不到它，呼叫期間整個程序的所有 greenlet 都停住；Locust 官方文件〈Testing other systems/protocols〉寫明，用了在 C 裡做 I/O 的函式庫，結果是一個 worker 程序只跑得了一個使用者。第二個是 CPU 運算：大量的 JSON 解析、加解密、本地計算不做 I/O，也就不讓出執行權，跑的期間其他使用者都在等。所有 greenlet 都在同一個作業系統執行緒上輪流執行，所以一個 Python 程序最多用到一顆 CPU 核心，要用更多核心就要多開程序（Locust 的多個 worker、`--processes`）。worker 程序的 CPU 用滿那一顆核心時，延遲裡混進了施壓端自己排隊的時間（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 的〈概念位置〉）。

patch 要在其他模組取得原本的函式之前做：一個模組在 patch 之前就 `from socket import socket`，它手上拿的是原本的阻塞版本。Locust 在 `import locust` 時自己呼叫 `monkey.patch_all()`（原始碼 `locust/__init__.py`，設了環境變數 `LOCUST_SKIP_MONKEY_PATCH` 才跳過），而 locustfile 是在 Locust 已經載入之後才被匯入，所以 locustfile 不必自己在第一行呼叫。

## 可觀察訊號與例子

patch 管不到的 I/O 的樣子是：從加壓一開始，吞吐量就不隨使用者數增加，延遲隨使用者數上升，而 worker 的 CPU 很低。使用者都在排隊等同一個被卡住的程序，不是 CPU 不夠。CPU 運算的樣子相反：一個 worker 程序的 CPU 用滿一顆核心（作業系統上看到那個程序接近 100%，多核心機器的整體使用率仍然很低），延遲上升；這時多開 worker 程序才提高吞吐量，加使用者只讓延遲繼續上升。兩種樣子在報告上都像受測服務變慢，所以判讀延遲之前要先看 worker 程序的 CPU 與受測服務那一端的指標。

例子：locustfile 用 `psycopg2` 直接查 PostgreSQL 量資料庫的容量。`psycopg2` 經由 C 寫的 libpq 做網路呼叫，gevent 換不到，每個查詢期間整個 worker 停住，Locust 量到的每秒查詢數跟只有一個使用者時差不多。gRPC 的 Python 函式庫同樣在 C 裡做 I/O，Locust 文件的 gRPC 範例因此先呼叫 `grpc_gevent.init_gevent()`，讓 gRPC 改用 gevent 的事件迴圈。

## 設計責任

寫 locustfile 的人在 Locust 裡用 HTTP 以外的 client 函式庫之前，查它的 I/O 是經由 Python 的標準函式庫還是 C 擴充：純 Python、用 `socket` 的函式庫多半直接可用；在 C 裡做 I/O 的，要找它的 gevent 整合（gRPC 的 `init_gevent`），或換成純 Python 的替代品，或把呼叫放進 gevent 的 threadpool（呼叫在另一個作業系統執行緒裡等待，主執行緒上的 greenlet 照樣切換；threadpool 解決的是等待時其他使用者停住，Python 程式碼的執行仍然在一顆核心上，CPU 運算的上限不因此提高）。patch 管不到的 I/O 與 CPU 運算這兩種卡住，都在加壓的第一段就出現，所以判讀容量的數字之前，要看到第一段的吞吐量隨使用者數增加。執行壓測的人照每個程序只用一顆核心估 worker 程序的數量，量法見 [Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)：施壓端的 CPU 或程序先到頂時，量到的上限屬於施壓端。
