---
title: "模組二：型別系統"
date: 2026-01-20
description: "現代 Python 的型別提示與資料結構"
weight: 2
---

# 模組二：型別系統

Python 3.5+ 引入的型別系統讓程式碼更易讀、更易維護。本模組介紹如何善用型別提示來提升程式碼品質。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [2.1](type-hints/) | Type Hints 基礎 | 為函式添加型別註解 |
| [2.2](optional-union/) | Optional、Union、泛型 | 處理可能為 None 的值 |
| [2.3](dataclass/) | Dataclass 資料結構 | 快速定義資料類別 |
| [2.4](enum/) | Enum 列舉型別 | 定義有限選項集合 |

## 實際範例來源

本模組的範例主要來自：

- `git_utils.py` - 型別提示的實際應用
- `config_loader.py` - Optional 和泛型的使用
- `hook_validator.py` - Dataclass 定義
- `parsers/base.py` - Enum 使用範例

## 為什麼需要型別系統？

```python
# 沒有型別提示
def process(data):
    return data.strip()  # data 是什麼？能呼叫 strip 嗎？

# 有型別提示
def process(data: str) -> str:
    return data.strip()  # 清楚知道是字串
```

## 學習時間

預計 45-60 分鐘
