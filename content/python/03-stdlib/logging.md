---
title: "3.5 logging - 日誌系統"
description: "結構化日誌輸出與除錯"
weight: 5
---

# logging - 日誌系統

`logging` 模組提供了靈活的日誌記錄功能。相較於 `print()`，日誌系統提供了等級控制、格式化和輸出目標管理等功能。

## 為什麼用 logging 而非 print？

```python
# 使用 print 的問題
print("Processing started")        # 無法控制輸出等級
print(f"Error: {error}")          # 無法區分一般訊息和錯誤
print("Debug: x =", x)            # 生產環境也會輸出

# 使用 logging 的好處
import logging
logger = logging.getLogger(__name__)

logger.info("Processing started")   # 可以控制等級
logger.error(f"Error: {error}")    # 明確標示為錯誤
logger.debug(f"x = {x}")           # 只在 DEBUG 模式輸出
```

## 日誌等級

| 等級 | 數值 | 使用時機 |
|------|------|---------|
| DEBUG | 10 | 詳細的除錯資訊 |
| INFO | 20 | 一般的操作資訊 |
| WARNING | 30 | 警告但程式仍可運行 |
| ERROR | 40 | 錯誤但程式仍可運行 |
| CRITICAL | 50 | 嚴重錯誤，程式可能無法繼續 |

## 實際範例：Hook 日誌系統

來自 `.claude/lib/hook_logging.py`：

```python
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_hook_logging(
    hook_name: str,
    log_subdir: Optional[str] = None,
    log_level: Optional[int] = None,
    include_stderr: bool = False
) -> logging.Logger:
    """
    設定 Hook 日誌系統

    Args:
        hook_name: Hook 名稱，用於識別日誌來源
        log_subdir: 日誌子目錄，預設為 hook_name
        log_level: 日誌等級，預設根據環境變數決定
        include_stderr: 是否同時輸出到 stderr

    Returns:
        logging.Logger: 配置好的 Logger 實例
    """
    # 決定日誌等級
    if log_level is None:
        debug_mode = os.getenv("HOOK_DEBUG", "").lower() == "true"
        log_level = logging.DEBUG if debug_mode else logging.INFO

    # 建立 Logger
    logger = logging.getLogger(hook_name)
    logger.setLevel(log_level)

    # 避免重複添加 handler
    if logger.handlers:
        return logger

    # 建立日誌目錄
    project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    subdir = log_subdir or hook_name
    log_dir = Path(project_root) / ".claude" / "hook-logs" / subdir
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日誌檔案路徑
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"{hook_name}-{timestamp}.log"

    # 設定 formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 檔案 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 可選的 stderr handler
    if include_stderr:
        import sys
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

    return logger
```

## 使用 Logger

### 在 Hook 腳本中使用

```python
#!/usr/bin/env python3
from hook_logging import setup_hook_logging

# 初始化 logger
logger = setup_hook_logging("branch-verify")

def main():
    logger.info("Hook started")

    branch = get_current_branch()
    logger.debug(f"Current branch: {branch}")

    if is_protected_branch(branch):
        logger.warning(f"Operating on protected branch: {branch}")

    try:
        # 執行操作
        result = do_something()
        logger.info(f"Operation completed: {result}")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

## 核心概念

### Logger

日誌記錄器，用於發送日誌訊息：

```python
import logging

# 取得 logger（使用模組名稱作為標識）
logger = logging.getLogger(__name__)

# 或使用自訂名稱
logger = logging.getLogger("my_app")
```

### Handler

決定日誌輸出到哪裡：

```python
import logging

logger = logging.getLogger("my_app")

# 輸出到檔案
file_handler = logging.FileHandler("app.log", encoding="utf-8")
logger.addHandler(file_handler)

# 輸出到控制台
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)
```

### Formatter

決定日誌的格式：

```python
import logging

formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

handler = logging.FileHandler("app.log")
handler.setFormatter(formatter)
```

### 格式化字串變數

| 變數 | 說明 |
|------|------|
| `%(asctime)s` | 時間戳 |
| `%(levelname)s` | 日誌等級名稱 |
| `%(name)s` | Logger 名稱 |
| `%(message)s` | 日誌訊息 |
| `%(filename)s` | 檔案名稱 |
| `%(lineno)d` | 行號 |
| `%(funcName)s` | 函式名稱 |

## 實用技巧

### 避免重複 Handler

```python
def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 重要：檢查是否已有 handler
    if logger.handlers:
        return logger

    handler = logging.FileHandler("app.log")
    logger.addHandler(handler)
    return logger
```

### 環境變數控制日誌等級

```python
import os
import logging

def get_log_level() -> int:
    """從環境變數取得日誌等級"""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(get_log_level())
```

### 日誌輪替

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "app.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5           # 保留 5 個備份
)
```

## 日誌檔案結構

Hook 系統的日誌結構：

```
.claude/hook-logs/
├── branch-verify/
│   ├── branch-verify-20240120-153000.log
│   └── branch-verify-20240120-160000.log
├── ticket-quality-gate/
│   └── ticket-quality-gate-20240120-155000.log
└── ...
```

## 最佳實踐

### 1. 使用 `__name__` 作為 Logger 名稱

```python
import logging

# 好：使用模組名稱，便於追蹤
logger = logging.getLogger(__name__)

# 不好：使用固定字串，難以區分來源
logger = logging.getLogger("my_logger")
```

### 2. 在適當的等級記錄訊息

```python
logger.debug("Variable x = %s", x)           # 詳細除錯
logger.info("Processing file %s", filename)  # 一般操作
logger.warning("Config not found, using default")  # 警告
logger.error("Failed to connect: %s", error)  # 錯誤
```

### 3. 使用延遲格式化

```python
# 好：使用 % 格式化（只在需要時才格式化）
logger.debug("Data: %s", expensive_function())

# 不好：f-string 總是會執行
logger.debug(f"Data: {expensive_function()}")
```

## 思考題

1. 為什麼 `setup_hook_logging` 要檢查 `logger.handlers`？
2. `logging.DEBUG` 和 `logging.INFO` 的差別是什麼？什麼時候用哪個？
3. 如何讓日誌同時輸出到檔案和控制台？

## 實作練習

1. 修改 `setup_hook_logging`，添加日誌輪替功能
2. 實作一個裝飾器，自動記錄函式的進入和離開
3. 建立一個日誌分析腳本，統計各等級日誌的數量

---

*上一章：[re - 正規表達式](../regex/)*
*下一章：[argparse - CLI 介面](../argparse/)*
