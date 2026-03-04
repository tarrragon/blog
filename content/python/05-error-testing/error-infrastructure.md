---
title: "5.5 頂層例外處理機制"
date: 2026-03-04
description: "run_hook_safely 與統一錯誤基礎設施"
weight: 5
---

# 頂層例外處理機制

前面的章節介紹了異常處理的基本語法和 `(bool, str)` 返回值模式。本章進入實務層面：當你有 44 個 Hook 腳本，每個都可能在不同地方失敗時，如何建立一套**統一的錯誤基礎設施**？

這是 W22-W25 開發週期中建立的機制，解決的核心問題是：

> Hook 失敗時，錯誤不能靜默消失，也不能讓整個工作流程崩潰。

## 問題：44 個 Hook，44 種錯誤處理方式

在統一之前，每個 Hook 腳本各自處理例外：

```python
# hook_a.py — 用 try-except 包整個 main
def main():
    try:
        do_work()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

# hook_b.py — 完全沒有錯誤處理
def main():
    do_work()  # 任何異常直接讓腳本 crash

# hook_c.py — 錯誤寫到檔案但用戶看不到
def main():
    try:
        do_work()
    except Exception as e:
        with open("error.log", "a") as f:
            f.write(str(e))
        # 用戶完全不知道出錯了
```

這造成三個問題：

1. **行為不一致**：有的 Hook 失敗會中斷流程，有的靜默吞掉
2. **重複程式碼**：每個 Hook 各寫一套 try-except
3. **錯誤不可見**：某些 Hook 靜默失敗了好幾個 session 才被發現

## 解決方案：`run_hook_safely`

`hook_utils.py` 提供了一個**頂層例外處理器**，所有 Hook 統一使用：

```python
def run_hook_safely(main_func: Callable[[], int], hook_name: str) -> int:
    """安全執行 Hook 函式，頂層例外處理

    Args:
        main_func: Hook 主入口函式，必須返回 int
        hook_name: Hook 識別名稱

    Returns:
        int: main_func 的返回值（正常），或 1（異常）
    """
    logger = setup_hook_logging(hook_name)

    try:
        exit_code = main_func()
        # 驗證返回值是整數
        if not isinstance(exit_code, int):
            try:
                exit_code = int(exit_code)
            except (ValueError, TypeError):
                exit_code = 0
        return exit_code
    except (KeyboardInterrupt, SystemExit):
        raise  # 這兩個不攔截
    except Exception:
        tb_str = traceback.format_exc()
        _log_exception(logger, hook_name, tb_str)
        return EXIT_ERROR
```

### 每個 Hook 的使用方式

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from hook_utils import run_hook_safely

def main() -> int:
    # 專注於業務邏輯，不需要處理頂層例外
    data = json.load(sys.stdin)
    result = validate(data)
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(run_hook_safely(main, "my-hook-name"))
```

## 設計解析

### 為什麼用 Callable 包裝？

`run_hook_safely` 接收一個**函式**，而不是直接包裝程式碼區塊。這個設計有三個好處：

```python
# 方式 A：直接包裝（不採用）
try:
    # 所有程式碼放在這裡
    data = read_input()
    result = process(data)
    output(result)
except Exception:
    handle_error()

# 方式 B：函式包裝（採用）
def main() -> int:
    data = read_input()
    result = process(data)
    output(result)
    return 0

run_hook_safely(main, "hook-name")
```

| 比較 | 方式 A | 方式 B |
|------|--------|--------|
| 可重用性 | 每個 Hook 各寫一次 | `run_hook_safely` 寫一次，所有 Hook 共用 |
| 測試性 | 無法單獨測試錯誤處理 | 可以測試 `run_hook_safely` 的行為 |
| 關注點分離 | 業務邏輯和錯誤處理混在一起 | Hook 只寫業務邏輯，錯誤處理交給框架 |

這就是[高階函式](../../02-type-system/callable/)在實務中的應用。

### 為什麼 `KeyboardInterrupt` 和 `SystemExit` 要特別處理？

```python
except (KeyboardInterrupt, SystemExit):
    raise  # 不攔截，直接往上傳
except Exception:
    # 只攔截「普通」的程式錯誤
```

Python 的例外繼承結構：

```
BaseException
├── KeyboardInterrupt    ← Ctrl+C
├── SystemExit           ← sys.exit()
└── Exception            ← 所有「普通」例外的父類別
    ├── ValueError
    ├── TypeError
    ├── FileNotFoundError
    └── ...
```

`KeyboardInterrupt` 和 `SystemExit` 不是程式錯誤，它們是**控制信號**：

- `KeyboardInterrupt`：用戶按了 Ctrl+C，意圖是終止程式
- `SystemExit`：程式碼呼叫了 `sys.exit()`，意圖是正常退出

如果攔截了這兩個，用戶按 Ctrl+C 程式不會停，`sys.exit(0)` 也不會退出。這違反了「最小驚訝原則」。

### 返回值型別驗證

```python
if not isinstance(exit_code, int):
    try:
        exit_code = int(exit_code)
    except (ValueError, TypeError):
        exit_code = 0
```

這段防護處理的是：萬一某個 Hook 的 `main()` 返回了非整數（例如 `None` 或字串）。

| main() 返回值 | 處理結果 | 說明 |
|--------------|---------|------|
| `0` | `0` | 正常 |
| `1` | `1` | 正常 |
| `None` | `0` | 忘記寫 return |
| `"0"` | `0` | 字串轉整數 |
| `"abc"` | `0` | 無法轉換，視為成功 |

## stderr vs stdout：Hook 系統的特殊規則

Claude Code 的 Hook 系統對輸出有特殊解讀：

| 輸出管道 | Claude Code 的解讀 |
|---------|-------------------|
| `stdout` | 正常訊息，顯示為 `hook success` |
| `stderr` | 錯誤訊息，顯示為 `hook error` |

這個行為影響了 `_log_exception` 的設計：

```python
def _log_exception(logger, hook_name, tb_str):
    # 1. 寫入日誌檔案（給開發者事後分析）
    try:
        logger.critical(f"Unhandled exception in {hook_name}")
        logger.critical(tb_str)
    except Exception as logging_error:
        print(f"Failed to log exception: {logging_error}", file=sys.stdout)
        print(tb_str, file=sys.stdout)

    # 2. 輸出到 stderr（讓用戶知道出錯了）
    print(
        f"[Hook Error] {hook_name} failed unexpectedly. "
        f"Check hook logs for details.",
        file=sys.stderr
    )
```

**第二行的 stderr 輸出是刻意的**。在 W25-005 之前，所有錯誤只寫入日誌檔案，導致 7 個 Hook 靜默失敗了至少 2 個 session 才被發現。加入 stderr 輸出後，用戶會立刻看到 `hook error` 提示。

### 實際案例

```
# 用戶看到的訊息（W25-005 之前）
SessionStart:startup hook success: Success     ← 看起來正常
SessionStart:startup hook success: Success
# 實際上有 7 個 Hook 在靜默失敗

# W25-005 之後
SessionStart:startup hook success: Success
SessionStart:startup hook error: [Hook Error] acceptance-gate-hook failed unexpectedly.
# 用戶立刻知道有問題
```

> 這個教訓的完整記錄在 IMP-003 錯誤模式中，[模組七的作用域迴歸案例研究](../../07-refactoring/scope-regression/)有詳細分析。

## 日誌系統配置

`run_hook_safely` 背後依賴 `setup_hook_logging` 建立日誌系統：

```python
def setup_hook_logging(hook_name: str) -> logging.Logger:
    """建立並設定 Hook 日誌系統

    功能：
    - 建立日誌目錄 .claude/hook-logs/{hook_name}/
    - 建立日誌檔案 {hook_name}-{YYYYMMDD-HHMMSS}.log
    - 配置 FileHandler + StreamHandler
    """
    sanitized_name = _sanitize_hook_name(hook_name)
    root_dir = _find_project_root()
    log_base_dir = root_dir / ".claude" / "hook-logs" / sanitized_name

    try:
        log_base_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _create_fallback_logger(hook_name)

    logger = logging.getLogger(hook_name)
    _clear_logger_handlers(logger)
    logger.setLevel(logging.DEBUG)

    is_debug = os.getenv("HOOK_DEBUG", "").lower() == "true"
    _setup_logger_handlers(logger, log_base_dir, sanitized_name, is_debug)
    return logger
```

### Fallback 策略

注意 `except OSError` 的處理：目錄建立失敗時不拋出異常，而是返回一個只有 `StreamHandler` 的 fallback logger。這確保**即使檔案系統出問題，日誌功能仍然可用**（只是沒有檔案記錄）。

這體現了 [5.1 異常處理策略](../exception/) 中「策略 4：使用預設值」的原則。

## 統一前後的對比

| 指標 | 統一前（v0.28.0） | 統一後（v0.31.0） |
|------|------------------|------------------|
| 錯誤處理方式 | 44 種不同實作 | 1 個 `run_hook_safely` |
| 靜默失敗風險 | 高（多個 Hook 實際靜默失敗中） | 低（stderr 強制可見） |
| 日誌格式 | 不一致 | 統一時間戳、格式、目錄結構 |
| 新增 Hook 所需程式碼 | ~15 行錯誤處理 | 1 行 `run_hook_safely` 呼叫 |

## 思考題

1. `run_hook_safely` 為什麼選擇返回 `EXIT_ERROR`（整數 1）而不是拋出異常？
2. 如果 `_log_exception` 本身也拋出異常（例如磁碟已滿），會發生什麼？
3. 為什麼 `_create_fallback_logger` 只配 `StreamHandler` 而不是直接返回 `None`？

## 實作練習

1. 寫一個類似 `run_hook_safely` 的裝飾器版本，讓 `@safe_hook` 就能保護函式
2. 擴展 `_log_exception`，讓它在記錄日誌的同時發送通知（例如寫入一個 `.alert` 檔案）
3. 修改 `setup_hook_logging`，加入日誌檔案大小限制（使用 `RotatingFileHandler`）

---

*上一章：[Mock 與測試隔離](../mock/)*
*相關：[作用域迴歸案例研究](../../07-refactoring/scope-regression/) — 這套機制如何在一次重構中暴露出潛在問題*
