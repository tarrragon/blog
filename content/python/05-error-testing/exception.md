---
title: "5.1 異常處理策略"
date: 2026-01-20
description: "何時捕獲、何時拋出"
weight: 1
---

# 異常處理策略

異常處理是撰寫穩健程式碼的關鍵。本章介紹 Python 的異常處理機制，以及 Hook 系統中採用的設計策略。

## 基本語法

### try-except

```python
try:
    result = risky_operation()
except SomeException as e:
    handle_error(e)
```

### 完整結構

```python
try:
    result = risky_operation()
except SpecificError as e:
    # 處理特定錯誤
    handle_specific_error(e)
except (TypeError, ValueError) as e:
    # 處理多種錯誤
    handle_type_error(e)
except Exception as e:
    # 處理其他所有錯誤
    handle_unknown_error(e)
else:
    # 沒有錯誤時執行
    process_result(result)
finally:
    # 無論如何都執行
    cleanup()
```

## 常見異常類型

| 異常 | 發生時機 |
|------|---------|
| `FileNotFoundError` | 檔案不存在 |
| `PermissionError` | 權限不足 |
| `ValueError` | 值不合法 |
| `TypeError` | 型別不正確 |
| `KeyError` | 字典鍵不存在 |
| `IndexError` | 索引超出範圍 |
| `JSONDecodeError` | JSON 解析失敗 |
| `TimeoutError` | 操作超時 |

## 實際範例：Git 命令執行

來自 `.claude/lib/git_utils.py`：

```python
import subprocess
from typing import Optional

def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, str]:
    """
    執行 git 命令並返回結果

    Returns:
        tuple[bool, str]: (是否成功, 輸出內容或錯誤訊息)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        # 命令超時
        return False, f"Command timed out after {timeout}s"

    except FileNotFoundError:
        # git 命令不存在
        return False, "git command not found"

    except Exception as e:
        # 其他未預期的錯誤
        return False, str(e)
```

### 設計分析

這個函式展示了 Hook 系統的異常處理策略：

1. **不拋出異常**：返回 `(bool, str)` 元組
2. **捕獲特定異常**：分別處理 `TimeoutExpired` 和 `FileNotFoundError`
3. **兜底處理**：`except Exception` 捕獲其他錯誤
4. **提供有意義的錯誤訊息**：讓呼叫者知道發生了什麼

## Hook 系統的異常哲學

### 為什麼不直接拋出異常？

Hook 腳本需要穩定運行，即使遇到錯誤也要：
1. 給出有意義的反饋
2. 不中斷整個 Claude 工作流程
3. 讓主程式能夠決定如何處理

### `(bool, str)` 返回值模式

```python
# 函式簽名
def validate_something() -> tuple[bool, str]:
    """
    Returns:
        tuple[bool, str]: (成功與否, 訊息)
    """
    pass

# 使用方式
success, message = validate_something()
if success:
    print(f"成功: {message}")
else:
    print(f"失敗: {message}")
```

### 實際應用

```python
def read_hook_input() -> dict:
    """
    從 stdin 讀取 Hook 輸入

    Returns:
        dict: 解析後的 JSON 資料，解析失敗時返回空字典
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}  # 不拋出異常，返回安全的預設值
    except Exception:
        return {}
```

## 異常處理策略

### 策略 1：捕獲並轉換

將異常轉換為返回值：

```python
def safe_divide(a: float, b: float) -> tuple[bool, float]:
    try:
        return True, a / b
    except ZeroDivisionError:
        return False, 0.0
```

### 策略 2：捕獲並記錄

記錄後繼續執行：

```python
def process_files(files: list[str]) -> list[str]:
    results = []
    for file in files:
        try:
            result = process_file(file)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {file}: {e}")
            # 繼續處理其他檔案
    return results
```

### 策略 3：捕獲並重新拋出

添加上下文後重新拋出：

```python
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
```

### 策略 4：使用預設值

提供安全的預設值：

```python
def get_config_value(config: dict, key: str, default: str = "") -> str:
    try:
        return config[key]
    except KeyError:
        return default
```

## 最佳實踐

### 1. 具體優於籠統

```python
# 好：捕獲具體異常
try:
    data = json.load(f)
except json.JSONDecodeError:
    data = {}

# 不好：捕獲所有異常
try:
    data = json.load(f)
except Exception:  # 可能隱藏其他問題
    data = {}
```

### 2. 保留原始異常資訊

```python
# 好：保留原始異常
try:
    process()
except ValueError as e:
    raise RuntimeError(f"Processing failed: {e}") from e

# 不好：丟失原始資訊
try:
    process()
except ValueError:
    raise RuntimeError("Processing failed")
```

### 3. 使用 finally 清理資源

```python
f = None
try:
    f = open("file.txt")
    process(f)
except IOError:
    handle_error()
finally:
    if f:
        f.close()  # 確保關閉檔案

# 更好：使用 with 語句
with open("file.txt") as f:
    process(f)  # 自動關閉
```

### 4. 不要靜默忽略異常

```python
# 不好：完全忽略錯誤
try:
    risky_operation()
except Exception:
    pass  # 什麼都不做

# 好：至少記錄一下
try:
    risky_operation()
except Exception as e:
    logger.warning(f"Operation failed (ignored): {e}")
```

## 自訂異常

```python
class HookError(Exception):
    """Hook 基礎異常"""
    pass

class ValidationError(HookError):
    """驗證錯誤"""
    pass

class ConfigurationError(HookError):
    """配置錯誤"""
    pass

# 使用
def validate_hook(path: str) -> None:
    if not path.endswith(".py"):
        raise ValidationError(f"Invalid hook file: {path}")
```

## 思考題

1. 為什麼 `run_git_command` 不直接拋出異常？
2. 什麼情況下應該使用 `except Exception`？
3. `from e` 在 `raise ... from e` 中的作用是什麼？

## 實作練習

1. 重構一個使用異常的函式，改為返回 `(bool, str)` 模式
2. 實作一個函式，嘗試多種方式載入配置（JSON、YAML、預設值）
3. 寫一個裝飾器，自動捕獲異常並轉換為返回值

---

*下一章：[返回值設計](../return-values/)*
