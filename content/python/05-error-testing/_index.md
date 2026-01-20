---
title: "模組五：錯誤處理與測試"
description: "穩健程式碼的基石：異常處理和單元測試"
weight: 5
---

# 模組五：錯誤處理與測試

穩健的程式碼需要妥善處理錯誤情況，並透過測試確保品質。本模組介紹 Python 的異常處理策略和測試技巧。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [5.1](exception/) | 異常處理策略 | 何時捕獲、何時拋出 |
| [5.2](return-values/) | 返回值設計 | `(bool, str)` 模式的應用 |
| [5.3](unittest/) | unittest 基礎 | 撰寫第一個測試 |
| [5.4](mock/) | Mock 與測試隔離 | 隔離外部依賴 |

## 實際範例來源

| 主題 | 範例來源 |
|------|---------|
| 異常處理 | `git_utils.py` |
| 返回值設計 | Hook 系統的 `(bool, str)` 模式 |
| unittest | `tests/` 目錄 |
| Mock | `test_hook_io.py` |

## 核心理念

```python
# Hook 系統的返回值設計模式
def validate_something() -> tuple[bool, str]:
    """
    返回 (成功與否, 訊息)
    - True, "成功訊息" - 驗證通過
    - False, "錯誤訊息" - 驗證失敗
    """
    if some_condition:
        return True, "驗證通過"
    return False, "驗證失敗：原因說明"
```

## 學習路徑

```
異常處理 → 返回值設計 → unittest 基礎 → Mock 技巧
```

## 學習時間

預計 60-75 分鐘
