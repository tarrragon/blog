---
title: "模組三：標準庫實戰"
description: "Python 標準庫的常用模組實戰應用"
weight: 3
---

# 模組三：標準庫實戰

Python 的「電池內建」哲學意味著標準庫提供了豐富的工具。本模組介紹 Hook 系統中最常用的標準庫模組。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [3.1](pathlib/) | pathlib - 路徑操作 | 物件導向的路徑處理 |
| [3.2](json/) | json - 序列化 | 資料的讀寫與轉換 |
| [3.3](subprocess/) | subprocess - 執行外部命令 | 呼叫系統命令 |
| [3.4](regex/) | re - 正規表達式 | 文字模式匹配 |
| [3.5](logging/) | logging - 日誌系統 | 結構化日誌輸出 |
| [3.6](argparse/) | argparse - CLI 介面 | 命令列參數解析 |

## 實際範例來源

| 模組 | 範例來源 |
|------|---------|
| pathlib | 全部 Hook 檔案 |
| json | `hook_io.py` |
| subprocess | `git_utils.py` |
| re | `markdown_link_checker.py` |
| logging | `hook_logging.py` |
| argparse | `hook_validator.py` |

## 學習建議

這些模組可以獨立學習，建議按實際需求選擇閱讀順序：

- **處理檔案** → 先讀 pathlib
- **呼叫 Git** → 先讀 subprocess
- **解析文字** → 先讀 re
- **建立 CLI** → 先讀 argparse

## 學習時間

每章節約 15-20 分鐘，全模組約 90-120 分鐘
