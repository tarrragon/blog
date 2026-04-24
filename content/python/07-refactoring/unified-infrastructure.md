---
title: "大規模統一化重構"
date: 2026-03-04
description: "從 44 種不同實作到統一基礎設施：日誌、訊息、風格的三階段漸進式重構"
weight: 75
---


前面幾章的重構案例都在解決局部問題：提取常數、分離配置、消除重複。本章探討一個更大的挑戰：當系統中有 **44 個獨立腳本**，各自發展出不同的基礎設施實作時，如何系統性地統一它們？

這是 W22-W24 開發週期中實際執行的三階段統一化重構。每個階段解決一個維度的分歧，最終讓所有 Hook 共享同一套基礎設施。

## 問題全貌

### 44 個 Hook，N 種實作

Hook 系統經過數個版本的有機成長，累積了大量不一致：

```python
# Hook A：用 common_functions 的 setup_hook_logging
from lib.common_functions import setup_hook_logging
logger = setup_hook_logging("hook-a")

# Hook B：用 hook_logging 的 setup_hook_logging（不同模組，同名函式）
from lib.hook_logging import setup_hook_logging
logger = setup_hook_logging("hook-b")

# Hook C：直接用 logging 模組
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hook D：print 大法
def log(msg):
    print(f"[hook-d] {msg}")
```

不只日誌，訊息和錯誤處理也是如此：

| 維度          | 分歧數量          | 常見變體                                       |
| ------------- | ----------------- | ---------------------------------------------- |
| 日誌初始化    | 3 種              | common_functions / hook_logging / 直接 logging |
| 錯誤處理      | 3 種              | try-except 包 main / 不處理 / 自訂裝飾器       |
| 使用者訊息    | 19 個檔案各自定義 | 每個 Hook 硬編碼自己的字串（共 57+ 個）        |
| logger 作用域 | 2 種              | 模組級全域 / main() 內區域                     |

### 為什麼要統一

分歧帶來的實際問題：

1. **修改成本倍增**：改一個日誌格式，要改 44 個檔案
2. **行為不一致**：有的 Hook 失敗時靜默，有的會 crash
3. **難以排查問題**：每個 Hook 的日誌格式不同，無法統一搜尋
4. **新 Hook 沒有範本**：寫新 Hook 時不知道該參考哪個

## 統一化模式

三階段統一化遵循一個共同的模式：

```
1. 建立統一介面    → 寫一個所有人都要用的模組
2. 漸進式遷移      → 逐批將現有 Hook 切換到新介面
3. 驗證           → 確認行為一致
4. 處理例外       → 處理少數無法直接遷移的情況
```

這個模式的關鍵在於**不一次改完**。每個階段只統一一個維度，確認穩定後再進入下一個。

## 第一階段：統一日誌（W22）

### 設計統一介面

目標是用一個模組取代三套日誌實作。核心 API 只有兩個函式：

```python
# hook_utils.py — 統一日誌模組

def setup_hook_logging(hook_name: str) -> logging.Logger:
    """建立並設定 Hook 日誌系統

    - 建立日誌目錄 .claude/hook-logs/{hook_name}/
    - 建立帶時間戳的日誌檔案
    - 配置 FileHandler + StreamHandler
    """

def run_hook_safely(main_func: Callable[[], int], hook_name: str) -> int:
    """安全執行 Hook 函式，頂層例外處理

    - 呼叫 setup_hook_logging 取得 logger
    - 執行 main_func，捕獲所有 Exception
    - 異常時記錄完整 traceback，返回 1
    """
```

`setup_hook_logging` 封裝了所有日誌配置細節：

```python
def setup_hook_logging(hook_name: str) -> logging.Logger:
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

幾個設計決策值得注意：

| 決策                     | 理由                                                 |
| ------------------------ | ---------------------------------------------------- |
| `_sanitize_hook_name`    | Hook 名稱可能包含 `/` 等特殊字元，不能直接用作目錄名 |
| `_clear_logger_handlers` | 避免重複呼叫時 handler 累加                          |
| Fallback logger          | 目錄建立失敗時仍可輸出到 stdout，不會 crash          |
| `HOOK_DEBUG` 環境變數    | 開發時可開啟 DEBUG 級別的 stream 輸出                |

### `run_hook_safely`：一行搞定錯誤處理

這是統一化的核心武器。原本每個 Hook 自己寫 try-except：

```python
# 重構前：每個 Hook 自己處理
if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except Exception as e:
        # 有的寫日誌，有的 print，有的什麼都不做
        print(f"Error: {e}")
        sys.exit(1)
```

統一後：

```python
# 重構後：一行搞定
if __name__ == "__main__":
    sys.exit(run_hook_safely(main, "acceptance-gate"))
```

`run_hook_safely` 內部處理三個邊界：

- **返回值驗證**：`main()` 可能回傳 `None` 或布林值，`run_hook_safely` 會將非整數返回值轉換為 `0`（成功）或 `1`（失敗），確保 `sys.exit` 收到合法的退出碼
- **不攔截 `SystemExit`**：刻意的 `sys.exit()` 呼叫不該被吃掉
- **不攔截 `KeyboardInterrupt`**：Ctrl+C 中斷不該被捕獲

所有其他 `Exception` 子類別都被捕獲、記錄到日誌、返回錯誤碼 1。

### 遷移策略

不可能一次改完 44 個檔案。按風險分批：

| 批次    | 範圍            | 策略               |
| ------- | --------------- | ------------------ |
| 第 1 批 | 5 個低風險 Hook | 驗證新模組行為正確 |
| 第 2 批 | 15 個中等複雜度 | 建立遷移信心       |
| 第 3 批 | 剩餘所有 Hook   | 批量遷移           |

每批遷移後執行全量測試，確認無迴歸。

## 第二階段：統一訊息（W23）

### 問題：硬編碼訊息散落各處

日誌統一後，下一個問題浮現：每個 Hook 的使用者訊息各自定義。

```python
# command-entrance-gate-hook.py
print("錯誤：未找到待處理的 Ticket\n建議操作: 執行 /ticket create")

# acceptance-gate-hook.py
print("[ERROR] 子任務未全部完成\nTicket: {}\n請先完成所有子任務")

# main-thread-edit-restriction-hook.py
print("編輯操作受限")
```

同樣的問題：改一個訊息格式要翻遍所有 Hook。訊息重複時會出現不一致。

### 集中管理：hook_messages.py

建立一個訊息常數模組，按職責分類：

```python
# lib/hook_messages.py

class CoreMessages:
    """所有 Hook 共用的通用訊息"""
    HOOK_START = "{hook_name} 啟動"
    INPUT_EMPTY = "輸入為空，預設允許"
    JSON_PARSE_ERROR = "JSON 解析錯誤，預設允許: {error}"

class GateMessages:
    """5 個 Gate Hook 的阻擋/警告訊息"""
    TICKET_NOT_FOUND_ERROR = """錯誤：未找到待處理的 Ticket

    為什麼阻止執行：
      開發命令必須有對應的 Ticket，確保工作可追蹤和驗收。

    建議操作:
      1. 執行 /ticket create 建立新 Ticket
      2. 或執行 /ticket track claim {id} 認領現有 Ticket"""

class WorkflowMessages:
    """工作流指導 Hook 的訊息"""
    EXTERNAL_QUERY_DETECTED = "檢測到 {tool_name} 調用"

class QualityMessages:
    """品質檢查 Hook 的訊息"""
    # ...
```

### 分類原則

| 類別               | 包含的 Hook     | 訊息特徵             |
| ------------------ | --------------- | -------------------- |
| CoreMessages       | 所有 Hook       | 啟動、錯誤、預設行為 |
| GateMessages       | 5 個 Gate Hook  | 阻擋、警告、建議操作 |
| WorkflowMessages   | 5 個工作流 Hook | 流程指導、步驟說明   |
| QualityMessages    | 品質檢查 Hook   | 掃描結果、改善建議   |
| ValidationMessages | 驗證 Hook       | 格式檢查、合規結果   |

使用方式：

```python
# 重構前
print("錯誤：未找到待處理的 Ticket\n建議操作: ...")

# 重構後
from lib.hook_messages import GateMessages
print(GateMessages.TICKET_NOT_FOUND_ERROR)
```

參數化的訊息用 `format()` ：

```python
# 帶參數的訊息
print(GateMessages.TICKET_NOT_CLAIMED_ERROR.format(ticket_id="0.31.0-W2-001"))
```

### 效果

| 指標         | 重構前                             | 重構後                     |
| ------------ | ---------------------------------- | -------------------------- |
| 訊息定義位置 | 散落 19 個檔案（57+ 個硬編碼字串） | 集中 1 個模組（45 個常數） |
| 修改訊息格式 | 逐檔搜尋修改                       | 改一處生效                 |
| 訊息一致性   | 同概念 2-3 種措辭                  | 每個概念一個定義           |
| 新 Hook 訊息 | 自行發明                           | 複用現有類別               |

## 第三階段：統一風格（W24）

### 問題：logger 初始化位置不一致

日誌模組和訊息常數統一後，16 個 Hook 的 logger 初始化位置仍然不一致：

```python
# 風格 A：模組級初始化（13 個 Hook）
logger = setup_hook_logging("my-hook")  # 最外層

def helper():
    logger.info("working...")           # 引用全域 logger

def main():
    helper()
    return 0

# 風格 B：main() 內初始化（3 個 Hook）
def helper(logger):
    logger.info("working...")           # 接收 logger 參數

def main():
    logger = setup_hook_logging("my-hook")
    helper(logger)
    return 0
```

目標是統一為風格 B。理由是：模組級初始化的 `logger` 會在 `import` 時立即建立日誌目錄和檔案，即使這個模組只是被其他工具引用而不是作為 Hook 執行。將 `logger` 移入 `main()` 可以確保只有**真正執行**時才初始化日誌系統。

### 事故：7 個 Hook 靜默失敗

統一風格的過程中發生了一個典型的作用域迴歸 bug。把 `logger` 從模組級移到 `main()` 內部後，引用全域 `logger` 的 helper 函式觸發了 `NameError`：

```python
# 修改後（有 bug）
def check_acceptance_criteria(ticket_path):
    logger.info(f"Checking {ticket_path}")  # NameError!

def main():
    logger = setup_hook_logging("acceptance-gate-hook")
    result = check_acceptance_criteria(path)
```

更危險的是，`run_hook_safely` 的頂層 try-except 捕獲了 `NameError`（它是 `Exception` 的子類別），寫入日誌檔案，返回錯誤碼。用戶完全看不到任何異常。**7 個 Hook 在至少 2 個 session 中靜默失敗**。

> 這個事故的完整分析見下一章：[重構陷阱與防護](/python/07-refactoring/refactoring-pitfalls/)

### 修正：逐一分析影響範圍

正確的做法是在修改作用域**之前**，用 AST 分析或 grep 找出所有引用 `logger` 的非 main 函式，然後為每個函式加入 `logger` 參數：

```python
def check_acceptance_criteria(ticket_path, logger):  # 加入參數
    logger.info(f"Checking {ticket_path}")

def main():
    logger = setup_hook_logging("acceptance-gate-hook")
    result = check_acceptance_criteria(path, logger)  # 傳遞 logger
```

修正規模：7 個 Hook、41 個函式、+143/-81 行。

### 事故後的改善

這次事故直接促成了 `_log_exception` 的 stderr 輸出改善（W25-005）：在寫入日誌檔案之外，額外輸出一行到 `sys.stderr`，確保即使 `run_hook_safely` 捕獲了異常，用戶也能在終端看到 `[Hook Error]` 提示。

## 重構後的標準樣板

三階段統一完成後，每個 Hook 的結構變得極為一致：

```python
#!/usr/bin/env python3
"""Hook 說明文件"""

import sys
import json
from pathlib import Path

# 引入統一基礎設施
# Hook 不是安裝的套件，需要手動把 hooks/ 目錄加入 Python 搜尋路徑
# 這樣才能 import 同目錄下的 hook_utils 和 lib/ 子模組
_hooks_dir = Path(__file__).parent
if _hooks_dir not in [p for p in sys.path if Path(p) == _hooks_dir]:
    sys.path.insert(0, str(_hooks_dir))

from hook_utils import run_hook_safely, setup_hook_logging
from lib.hook_messages import GateMessages, CoreMessages

# 常數定義
EXIT_SUCCESS = 0
EXIT_BLOCK = 2

# ---- 業務邏輯 ----

def check_something(data, logger):
    """每個 helper 都接收 logger 參數"""
    logger.info(CoreMessages.HOOK_START.format(hook_name="my-hook"))
    # ...

def main():
    logger = setup_hook_logging("my-hook")
    # 讀取輸入、執行檢查、輸出結果
    return EXIT_SUCCESS

# ---- 入口 ----
if __name__ == "__main__":
    sys.exit(run_hook_safely(main, "my-hook"))
```

對比重構前後：

| 面向         | 重構前                   | 重構後                    |
| ------------ | ------------------------ | ------------------------- |
| 日誌初始化   | 3 種模組 + 散裝 logging  | `setup_hook_logging` 一行 |
| 錯誤處理     | 自寫 try-except 或不處理 | `run_hook_safely` 一行    |
| 使用者訊息   | 硬編碼在各檔案           | 引用 `hook_messages` 常數 |
| logger 傳遞  | 全域變數                 | 參數傳遞                  |
| 入口點       | 5-15 行樣板              | 1 行                      |
| 新 Hook 開發 | 參考哪個都不確定         | 複製標準樣板              |

## 統一化的通用教訓

### 教訓 1：先建介面，再遷移

不要試圖「就地重構」現有程式碼。先寫好新模組，測試通過，然後逐步切換。

```
錯誤路徑：邊改邊用 → 半成品狀態 → 新舊混合更亂
正確路徑：新模組獨立完成 → 逐批遷移 → 舊模組標記棄用
```

### 教訓 2：分批遷移，每批驗證

44 個 Hook 一次改完的風險太高。分批的目的不只是降低風險，更是建立信心。第一批 5 個成功後，第二批 15 個就能更快。

### 教訓 3：統一風格是最危險的一步

統一「介面」（W22 日誌、W23 訊息）相對安全，因為是新增模組再切換引用。統一「風格」（W24 作用域）涉及修改現有程式碼的結構，牽一髮動全身。

| 風險等級 | 操作類型               | 範例                       |
| -------- | ---------------------- | -------------------------- |
| 低       | 新增模組 + 替換 import | W22 新增 hook_utils.py     |
| 中       | 替換訊息字串           | W23 硬編碼 → 常數引用      |
| 高       | 修改變數作用域         | W24 全域 logger → 參數傳遞 |

### 教訓 4：安全網要先到位

W24 的事故之所以嚴重，是因為安全網（stderr 輸出）在事故**之後**才補上。正確的順序應該是：

```
1. 先確認安全網（stderr 輸出、測試覆蓋）
2. 再執行風險操作（作用域修改）
3. 最後清理（移除棄用程式碼）
```

## 量化成果

三階段統一化的最終成果：

| 指標              | 統一前                  | 統一後                    |
| ----------------- | ----------------------- | ------------------------- |
| 日誌模組          | 3 個                    | 1 個 (hook_utils.py)      |
| 錯誤處理模式      | 3 種                    | 1 種 (run_hook_safely)    |
| 訊息定義位置      | 19 個檔案（57+ 個字串） | 1 個 (hook_messages.py)   |
| logger 初始化風格 | 2 種                    | 1 種 (main 內 + 參數傳遞) |
| 新 Hook 開發時間  | ~30 分鐘                | ~10 分鐘                  |
| Hook 入口樣板     | 5-15 行                 | 1 行                      |

## 思考題

1. 如果你的系統有 100 個腳本而不是 44 個，統一化策略會有什麼不同？
2. `run_hook_safely` 選擇返回錯誤碼而不是重新拋出異常，這個設計在什麼情境下會是錯誤的？
3. 訊息常數用 class 分類（`GateMessages`、`WorkflowMessages`）而不是單一字典，有什麼優缺點？

## 實作練習

1. 為一組 3 個以上的腳本設計統一日誌模組，包含 `setup_logging` 和 `run_safely` 兩個函式
2. 掃描一個多檔案專案，找出所有硬編碼的使用者訊息字串，規劃集中管理方案
3. 嘗試用本章的分批遷移策略，將練習 2 的訊息逐批遷移到常數模組

## 小結

- 大規模統一化的核心模式：**建立統一介面 -> 分批遷移 -> 驗證 -> 處理例外**
- 統一「介面」（新增模組 + 替換引用）風險低，統一「風格」（修改現有結構）風險高
- `run_hook_safely` 一行取代 44 套自寫的錯誤處理，確保行為一致
- 訊息集中化用 Messages 類別按使用者角色分組，消除散落的硬編碼字串
- 分批遷移不只降低風險，更是建立信心的過程
- 安全網（stderr 輸出、測試覆蓋）必須在風險操作**之前**到位

---

*上一章：[配置分離與常數管理](/python/07-refactoring/constants-management/)*
*下一章：[重構陷阱與防護](/python/07-refactoring/refactoring-pitfalls/)*
*相關：[5.5 頂層例外處理機制](/python/05-error-testing/error-infrastructure/)*
