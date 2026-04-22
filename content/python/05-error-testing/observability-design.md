---
title: "5.6 Hook 系統可觀測性設計"
date: 2026-03-04
description: "日誌架構、錯誤可見性、健康監控：讓 44 個 Hook 的運行狀態透明可追蹤"
weight: 6
---

[上一章](../error-infrastructure/)介紹了 `run_hook_safely` 這個頂層例外處理器，解決了「44 個 Hook 各自處理錯誤」的問題。但「捕獲錯誤」只是可觀測性的第一步。真正的問題是：

> 當 44 個 Hook 每天執行數百次，你怎麼知道它們運行正常？出了問題你怎麼找到原因？

本章從三個維度建立 Hook 系統的可觀測性：

| 維度       | 解決的問題             | 核心機制                          |
| ---------- | ---------------------- | --------------------------------- |
| 日誌架構   | 每次執行的痕跡在哪裡？ | Structured Logging + Log Rotation |
| 錯誤可見性 | 出錯了誰來告訴用戶？   | stderr 輸出 + Fallback 策略       |
| 健康監控   | 系統整體是否正常？     | 執行時間追蹤 + 日誌清理           |

---

## 一、日誌架構設計

### 1.1 需求分析

Hook 日誌系統和一般應用程式的日誌有兩個根本差異：

| 差異     | 一般應用程式 | Hook 系統                |
| -------- | ------------ | ------------------------ |
| 生命週期 | 長時間運行   | 每次觸發執行一次（秒級） |
| 實例數量 | 1-3 個服務   | 44 個獨立腳本            |
| 日誌量   | 大量、持續   | 少量、離散               |
| 讀者     | 運維團隊     | 開發者自己               |

這些差異決定了日誌架構的選擇：不需要集中式日誌服務，但需要**按 Hook 名稱隔離**和**按時間自動清理**。

### 1.2 目錄結構設計

```
.claude/hook-logs/
├── acceptance-gate-hook/
│   ├── acceptance-gate-hook-20260304-091523.log
│   ├── acceptance-gate-hook-20260304-091845.log
│   └── .cleanup_trigger           # 清理觸發計數器
├── command-entrance-gate-hook/
│   ├── command-entrance-gate-hook-20260304-091523.log
│   └── ...
└── phase-completion-gate-hook/
    └── ...
```

每個 Hook 有獨立的日誌目錄。每次執行產生一個獨立的日誌檔案，檔名包含時間戳。這個設計的好處：

- **隔離性**：排查問題時只需看特定 Hook 的目錄
- **時間線**：按檔名排序就能看到執行歷史
- **清理**：按目錄或按時間清理都很容易

### 1.3 日誌系統初始化

```python
def setup_hook_logging(hook_name: str) -> logging.Logger:
    """建立並設定 Hook 日誌系統"""
    if not hook_name:
        hook_name = DEFAULT_HOOK_NAME

    sanitized_name = _sanitize_hook_name(hook_name)
    root_dir = _find_project_root()
    log_base_dir = root_dir / ".claude" / "hook-logs" / sanitized_name

    # 建立日誌目錄（失敗時降級，不拋出異常）
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

這段程式碼有幾個值得注意的設計決策。

**Named Logger**：使用 `logging.getLogger(hook_name)` 取得 named logger，而非 root logger。這確保每個 Hook 的日誌設定互不干擾：

```python
# 每個 Hook 有自己的 logger 實例
logger_a = logging.getLogger("acceptance-gate-hook")
logger_b = logging.getLogger("command-entrance-gate-hook")
# 兩者的 handlers、level、format 完全獨立
```

**Handler 清理**：每次初始化前先清除舊的 handlers。這防止同一個 logger 被重複配置（例如在測試中多次呼叫 `setup_hook_logging`）：

```python
def _clear_logger_handlers(logger: logging.Logger) -> None:
    """清除 logger 的所有 handlers"""
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
```

注意 `logger.handlers[:]` 的切片複製。直接遍歷 `logger.handlers` 並在迴圈中 `removeHandler` 會修改列表長度，導致跳過元素。這是 Python 中遍歷時修改集合的經典陷阱。

**環境變數控制**：透過 `HOOK_DEBUG` 環境變數切換日誌詳細程度，不需要修改程式碼：

```bash
# 正常模式：stdout 只顯示 WARNING 以上
python3 my-hook.py

# 除錯模式：stdout 顯示所有等級
HOOK_DEBUG=true python3 my-hook.py
```

### 1.4 雙通道輸出

每個 logger 配置兩個 handler，分別負責不同用途：

```python
def _setup_logger_handlers(logger, log_base_dir, sanitized_name, is_debug):
    """為 logger 配置 handlers"""
    # 檔案 handler：記錄所有等級，供事後分析
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file_path = log_base_dir / f"{sanitized_name}-{timestamp}.log"
    file_handler = _create_file_handler(log_file_path)
    if file_handler:
        logger.addHandler(file_handler)

    # 控制台 handler：正常模式只顯示 WARNING+，除錯模式顯示全部
    logger.addHandler(_create_stream_handler(is_debug))
```

| Handler       | 輸出目標 | 等級                           | 格式                                    | 用途     |
| ------------- | -------- | ------------------------------ | --------------------------------------- | -------- |
| FileHandler   | 日誌檔案 | DEBUG                          | `[2026-03-04 09:15:23] DEBUG - message` | 事後分析 |
| StreamHandler | stdout   | WARNING（正常）/ DEBUG（除錯） | `[WARNING] message`                     | 即時回饋 |

為什麼 StreamHandler 輸出到 **stdout** 而非 stderr？這和 Claude Code 的 Hook 系統規則有關：

| 輸出管道 | Claude Code 的解讀              |
| -------- | ------------------------------- |
| stdout   | 正常訊息，顯示為 `hook success` |
| stderr   | 錯誤訊息，顯示為 `hook error`   |

日誌中的 WARNING 訊息是給開發者的提醒，不是 Hook 執行失敗。如果把 WARNING 輸出到 stderr，Claude Code 會把它當成錯誤。所以 StreamHandler 必須走 stdout。

### 1.5 Hook 名稱淨化

Hook 名稱會用於檔案系統路徑（目錄名和檔名），所以需要淨化：

```python
def _sanitize_hook_name(name: str) -> str:
    """淨化 hook 名稱，移除無法用於檔案系統的字元"""
    if not name:
        return DEFAULT_HOOK_NAME

    for char in ["<", ">", "|"]:
        name = name.replace(char, "-")
    name = name.replace("/", "-").replace("\\", "-")

    # 合併連續 "-" 並移除前後
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip("-")

    return name if name else DEFAULT_HOOK_NAME
```

這是防禦性程式設計的典型例子。雖然目前所有 Hook 的名稱都是合法的檔案名（像 `acceptance-gate-hook`），但**不能假設呼叫端一定傳入合法名稱**。淨化函式確保即使傳入 `<invalid|name>` 也能產生合法的目錄名 `invalid-name`。

### 1.6 專案根目錄定位

日誌目錄在專案根目錄下的 `.claude/hook-logs/`。但 Hook 可能從不同的工作目錄被執行，所以需要動態定位：

```python
def _find_project_root() -> Path:
    """查詢專案根目錄

    優先順序：
    1. 環境變數 CLAUDE_PROJECT_DIR
    2. 從 cwd 向上搜尋 CLAUDE.md（最多 5 層）
    3. os.getcwd() fallback（永不失敗）
    """
    env_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir)

    current_dir = Path.cwd()
    for _ in range(CLAUDE_MD_SEARCH_DEPTH):
        if (current_dir / "CLAUDE.md").exists():
            return current_dir
        parent = current_dir.parent
        if parent == current_dir:
            break
        current_dir = parent

    return Path.cwd()
```

三層 fallback 的設計邏輯：

| 優先級 | 方式               | 適用場景                   | 失敗條件         |
| ------ | ------------------ | -------------------------- | ---------------- |
| 1      | 環境變數           | Claude Code 啟動時自動設定 | 手動執行時未設定 |
| 2      | 向上搜尋 CLAUDE.md | 手動執行、測試             | 在非專案目錄執行 |
| 3      | cwd                | 最後手段                   | 永不失敗         |

注意搜尋深度限制 `CLAUDE_MD_SEARCH_DEPTH = 5`。不做深度限制的話，在 `/` 目錄執行時會遍歷整個檔案系統。5 層足以覆蓋大多數專案結構（`/Users/user/projects/my-app/.claude/hooks/` 需要 4 層）。

---

## 二、錯誤可見性設計

### 2.1 核心問題：靜默失敗

IMP-003 事件是錯誤可見性設計的直接動機。7 個 Hook 因為變數作用域問題（`NameError`）靜默失敗了至少 2 個 session。失敗的流程是：

```
Hook 執行 → NameError → run_hook_safely 捕獲 → 寫入日誌檔案 → 返回 EXIT_ERROR
                                                    ↑
                                              用戶看不到這裡
```

問題出在 `_log_exception` 的初版只寫入日誌檔案：

```python
# W25-005 之前的版本（有缺陷）
def _log_exception(logger, hook_name, tb_str):
    logger.critical(f"Unhandled exception in {hook_name}")
    logger.critical(tb_str)
    # 到這裡就結束了 -- 用戶完全不知道出錯
```

### 2.2 修正：stderr 強制可見

W25-005 在日誌寫入之後加了一行 stderr 輸出：

```python
def _log_exception(logger, hook_name, tb_str):
    """記錄異常 traceback 到日誌"""
    # 1. 寫入日誌檔案（完整 traceback，供事後分析）
    try:
        logger.critical(f"Unhandled exception in {hook_name}")
        logger.critical(tb_str)
    except Exception as logging_error:
        # 日誌系統本身也可能失敗（磁碟滿了、權限問題）
        print(f"Failed to log exception: {logging_error}", file=sys.stdout)
        print(tb_str, file=sys.stdout)

    # 2. 輸出到 stderr，讓 Claude Code 顯示 "hook error"（W25-005 新增）
    print(
        f"[Hook Error] {hook_name} failed unexpectedly. "
        f"Check hook logs for details.",
        file=sys.stderr
    )
```

這個設計的關鍵在於**兩層輸出各司其職**：

| 輸出     | 目標                        | 內容           | 讀者               |
| -------- | --------------------------- | -------------- | ------------------ |
| 日誌檔案 | `.claude/hook-logs/{name}/` | 完整 traceback | 開發者（事後分析） |
| stderr   | Claude Code UI              | 簡短錯誤提示   | 用戶（即時感知）   |

**為什麼不把完整 traceback 輸出到 stderr？** 因為 stderr 的內容會直接顯示在 Claude Code 的對話介面中。一段 20 行的 Python traceback 對用戶來說是噪音。只需要告訴用戶「哪個 Hook 出錯了」和「去哪裡看詳情」就夠了。

### 2.3 日誌系統自身的 Fallback

如果日誌系統本身出了問題（例如磁碟已滿，無法寫入日誌檔案），怎麼辦？

```python
# 目錄建立失敗時的 Fallback
try:
    log_base_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    return _create_fallback_logger(hook_name)  # 降級為純 stdout 輸出

def _create_fallback_logger(hook_name: str) -> logging.Logger:
    """建立 Fallback Logger（僅 StreamHandler）"""
    logger = logging.getLogger(hook_name)
    _clear_logger_handlers(logger)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(_create_stream_handler())
    return logger
```

Fallback Logger 只有 StreamHandler（stdout），沒有 FileHandler。這表示日誌不會被儲存到檔案，但**至少 Hook 能正常運行**，而且重要訊息仍然會出現在控制台。

這體現了一個重要的設計原則：**可觀測性基礎設施的故障不應該導致業務功能中斷**。日誌系統壞了，Hook 仍然要能工作。

### 2.4 IMP-005 的教訓：Import 階段的可見性

IMP-005 暴露了另一個可見性盲區：**import 階段的錯誤**。當模組遷移後 import 路徑沒更新，`ModuleNotFoundError` 在 `run_hook_safely` 之前就發生了：

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# 這一行在 run_hook_safely 之前執行
# 如果失敗，run_hook_safely 根本不會被呼叫
from lib.common_functions import hook_output  # ModuleNotFoundError!

from hook_utils import run_hook_safely

def main() -> int:
    # ...
    return 0

if __name__ == "__main__":
    sys.exit(run_hook_safely(main, "my-hook"))
```

`run_hook_safely` 的保護範圍是 `main()` 函式內部，但 import 發生在模組載入階段。解決方案是在 import 處加入 try-except 防護：

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# Import 防護：確保失敗時有明確的 stderr 輸出
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from hook_utils import run_hook_safely
    from lib.common_functions import hook_output
except ImportError as e:
    print(f"[Hook Import Error] {Path(__file__).name}: {e}", file=sys.stderr)
    sys.exit(1)
```

| 沒有 Import 防護              | 有 Import 防護                                                       |
| ----------------------------- | -------------------------------------------------------------------- |
| Claude Code 顯示 `hook error` | Claude Code 顯示 `hook error`                                        |
| 無法得知是哪個 Hook           | `[Hook Import Error] my-hook.py: No module named 'common_functions'` |
| 無法得知什麼原因              | 精確到模組名稱和檔案名稱                                             |

### 2.5 IMP-006 的教訓：兩條錯誤路徑

IMP-006 案例 D 揭示了一個更隱蔽的問題：Hook 有兩條不同的「失敗路徑」，但只有一條有 stderr 輸出。

```python
def main() -> int:
    # ...驗證邏輯...

    if should_block:
        # 路徑 1：業務邏輯拒絕（有意阻止）
        result = {"error": error_message}
        print(json.dumps(result), file=sys.stdout)
        return 2  # 只有 stdout，沒有 stderr！

    return 0

# run_hook_safely 包裝
# 路徑 2：未預期異常 -- _log_exception 已有 stderr 輸出
```

開發者只考慮了「未預期異常」這條路徑（由 `_log_exception` 處理），忘了「有意阻止」也需要 stderr 輸出。修復：

```python
if should_block:
    result = {"error": error_message}
    print(json.dumps(result), file=sys.stdout)
    # 新增：確保用戶在 Claude Code UI 能看到拒絕原因
    print(f"[Agent Ticket Validation] blocked: {error_message}", file=sys.stderr)
    return 2
```

教訓歸納為一條規則：**Hook 的所有非成功路徑都必須有 stderr 輸出**。不只是 exception，業務邏輯的拒絕也算。

```
Hook 執行結果
├── 成功（return 0）→ stdout 正常訊息
├── 未預期異常（Exception）→ stderr 由 _log_exception 處理
└── 有意阻止（return 非 0）→ stderr 必須有原因說明  ← 容易遺漏
```

---

## 三、健康監控設計

### 3.1 執行時間追蹤

`run_hook_safely` 記錄每次執行的耗時：

```python
def run_hook_safely(main_func, hook_name):
    logger = setup_hook_logging(hook_name)
    start_time = time.time()

    try:
        exit_code = main_func()
        elapsed_time = time.time() - start_time
        logger.debug(f"Hook execution time: {elapsed_time:.2f}s")
        return exit_code
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        elapsed_time = time.time() - start_time
        logger.debug(f"Hook execution time before failure: {elapsed_time:.2f}s")
        tb_str = traceback.format_exc()
        _log_exception(logger, hook_name, tb_str)
        return EXIT_ERROR
```

注意兩處 `elapsed_time` 的記錄位置——成功和失敗路徑各記一次。失敗時記錄「失敗前的執行時間」，可以判斷是立即失敗（import 錯誤，< 0.01s）還是在執行過程中失敗（邏輯錯誤，可能數秒）。

日誌檔案中的記錄：

```
[2026-03-04 09:15:23] DEBUG - Hook execution time: 0.05s       # 正常
[2026-03-04 09:15:24] DEBUG - Hook execution time: 2.34s       # 偏慢，值得關注
[2026-03-04 09:15:25] DEBUG - Hook execution time before failure: 0.00s  # import 階段就失敗了
```

這些數據在 IMP-006 案例 C 的排查中發揮了作用。hookify plugin 的 timeout 設定為 10ms，而 Python 啟動需要約 24ms。比對 Hook 執行時間和 timeout 設定，就能定位超時問題。

### 3.2 日誌自動清理（Log Rotation）

44 個 Hook 每天執行數百次，日誌檔案會快速累積。自動清理機制避免磁碟空間被耗盡：

```python
LOG_RETENTION_DAYS = 7
LOG_CLEANUP_TRIGGER_FREQUENCY = 10

def _cleanup_old_logs(log_base_dir: Path, retention_days: int = LOG_RETENTION_DAYS):
    """清理超期日誌檔案"""
    try:
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        for log_file in log_base_dir.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_time:
                    log_file.unlink()
            except (OSError, ValueError):
                pass
    except OSError:
        pass
```

**為什麼不用 Python 標準庫的 `RotatingFileHandler`？**

`RotatingFileHandler` 按照**單一檔案大小**輪轉，適合長時間運行的服務。但 Hook 系統的日誌模式是每次執行一個新檔案，需要的是按**時間**清理舊檔案。兩者的需求場景不同：

| 機制                     | 適用場景                       | Hook 系統需求 |
| ------------------------ | ------------------------------ | ------------- |
| RotatingFileHandler      | 單一長期運行程序，同一個日誌檔 | 不適用        |
| TimedRotatingFileHandler | 單一程序按時間分割日誌         | 部分適用      |
| 自訂清理                 | 多程序、每次新檔案、按時間保留 | 適用          |

### 3.3 清理頻率控制

每次 Hook 執行都檢查是否需要清理，這本身也有成本。所以用一個 `.cleanup_trigger` 檔案作為計數器，每 N 次呼叫才真正執行清理：

```python
def _setup_logger_handlers(logger, log_base_dir, sanitized_name, is_debug):
    """為 logger 配置 handlers"""
    # 觸發日誌清理（降低頻率）
    cleanup_marker = log_base_dir / ".cleanup_trigger"
    try:
        if cleanup_marker.exists():
            count = int(cleanup_marker.read_text().strip() or "0")
            if count >= LOG_CLEANUP_TRIGGER_FREQUENCY:
                _cleanup_old_logs(log_base_dir)
                cleanup_marker.write_text("0")
            else:
                cleanup_marker.write_text(str(count + 1))
        else:
            cleanup_marker.write_text("1")
    except (OSError, ValueError):
        pass  # 清理失敗不影響日誌功能
```

`LOG_CLEANUP_TRIGGER_FREQUENCY = 10` 表示每 10 次執行才清理一次。這是一個權衡：

| 頻率      | 好處             | 代價                       |
| --------- | ---------------- | -------------------------- |
| 每次（1） | 日誌目錄永遠乾淨 | 每次 Hook 都多一次目錄掃描 |
| 每 10 次  | 幾乎感覺不到開銷 | 最多累積 10 個多餘檔案     |
| 每 100 次 | 開銷最小         | 可能累積數百個多餘檔案     |

**為什麼用檔案而不用記憶體計數器？** 因為 Hook 是獨立程序，每次執行都是新進程。記憶體中的計數器在進程結束後就消失了。檔案是跨進程持久化的最簡單方式。

注意最外層的 `except (OSError, ValueError): pass`。清理機制本身的故障（例如檔案被鎖定、計數器檔案損壞）不應該影響日誌功能。這和 Fallback Logger 的設計原則一致：**輔助功能的故障不阻擋核心功能**。

---

## 四、三個錯誤模式的可觀測性教訓

前面三個維度的設計，很大程度源自三個真實錯誤模式（IMP-003、IMP-005、IMP-006）的教訓。把它們放在一起看，可以提煉出可觀測性設計的通用原則。

### 4.1 IMP-003：作用域迴歸 -- 靜默失敗的代價

| 項目             | 說明                                         |
| ---------------- | -------------------------------------------- |
| **事件**         | 7 個 Hook 因 `NameError` 靜默失敗 2+ session |
| **根因**         | logger 從全域移入 main()，引用者未更新       |
| **可觀測性缺陷** | `_log_exception` 只寫檔案日誌，不輸出 stderr |
| **修正**         | 新增 stderr 輸出（W25-005）                  |
| **通用原則**     | **錯誤必須有用戶可感知的通知管道**           |

詳細的作用域分析見[作用域迴歸案例研究](../../07-refactoring/scope-regression/)。

### 4.2 IMP-005：Import 未同步 -- 保護範圍的盲區

| 項目             | 說明                                        |
| ---------------- | ------------------------------------------- |
| **事件**         | 5 個 Hook 因 `ModuleNotFoundError` 啟動失敗 |
| **根因**         | 模組遷移後 import 路徑未更新                |
| **可觀測性缺陷** | `run_hook_safely` 無法保護 import 階段      |
| **修正**         | 在 import 處加入 try-except + stderr        |
| **通用原則**     | **頂層保護的範圍必須覆蓋所有執行階段**      |

### 4.3 IMP-006：隱性故障 -- 錯誤路徑的完整性

| 項目         | 說明                                       |
| ------------ | ------------------------------------------ |
| **事件**     | 多種不同根因的 hook error 無法區分         |
| **案例 A**   | 函式參數遺漏（部分 call site 缺少 logger） |
| **案例 C**   | Plugin timeout 10ms，Python 啟動需 24ms    |
| **案例 D**   | 有意阻止路徑缺少 stderr                    |
| **通用原則** | **所有非成功路徑都需要可區分的錯誤輸出**   |

### 4.4 共通教訓

三個錯誤模式的共通點，提煉為三條可觀測性設計規則：

**規則 1：錯誤不可靜默**

```python
# 錯誤做法：只寫日誌，用戶不知道
logger.critical(tb_str)

# 正確做法：日誌 + 用戶通知
logger.critical(tb_str)
print(f"[Hook Error] {hook_name} failed", file=sys.stderr)
```

**規則 2：保護必須完整**

```python
# 錯誤做法：只保護 main()
sys.exit(run_hook_safely(main, "hook"))

# 正確做法：import 也要保護
try:
    from lib.module import function
except ImportError as e:
    print(f"[Hook Import Error] {__file__}: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(run_hook_safely(main, "hook"))
```

**規則 3：錯誤要可區分**

```python
# 錯誤做法：所有錯誤用同一種訊息
print("hook error", file=sys.stderr)

# 正確做法：包含 Hook 名稱和錯誤類型
print(f"[Hook Error] {hook_name} failed unexpectedly", file=sys.stderr)
print(f"[Hook Import Error] {filename}: {error}", file=sys.stderr)
print(f"[Agent Validation] blocked: {reason}", file=sys.stderr)
```

---

## 五、完整的可觀測性架構

把前面的設計串在一起，一個 Hook 的完整執行路徑和可觀測性覆蓋如下：

```
Hook 被觸發
│
├─ [階段 1] Import 載入
│  ├─ 成功 → 繼續
│  └─ 失敗 → try-except 捕獲
│            ├─ stderr: [Hook Import Error] hook.py: error
│            └─ sys.exit(1)
│
├─ [階段 2] setup_hook_logging
│  ├─ 成功 → Logger 就緒（FileHandler + StreamHandler）
│  └─ 失敗 → Fallback Logger（僅 StreamHandler）
│
├─ [階段 3] main() 執行
│  ├─ 成功 → logger.debug("execution time: Xs")
│  │         return exit_code
│  ├─ 業務拒絕 → stderr: [Hook Name] blocked: reason
│  │             return 2
│  └─ 未預期異常 → logger.critical(traceback)
│                   stderr: [Hook Error] hook failed
│                   return 1
│
└─ [階段 4] 日誌清理（每 10 次觸發）
   └─ 清理 7 天前的日誌檔案
```

每個階段都有對應的可觀測性機制。沒有任何執行路徑是「靜默」的。

---

## 思考題

1. 為什麼 `_cleanup_old_logs` 使用 `mtime`（修改時間）而非 `ctime`（建立時間）來判斷過期？在什麼情況下兩者會不同？

2. 如果兩個 Hook 同時執行（例如同時觸發的 PreToolUse Hook），它們的日誌會互相干擾嗎？提示：思考 `logging.getLogger(hook_name)` 的行為。

3. 目前的清理計數器用檔案系統實作。如果改用原子操作（例如 `os.rename`），能否解決並行存取的 race condition？值得嗎？

## 實作練習

1. **寫一個日誌分析腳本**：掃描 `.claude/hook-logs/` 目錄，統計每個 Hook 的平均執行時間、失敗次數、最後一次執行時間。

2. **實作 RotatingFileHandler 版本**：修改 `setup_hook_logging`，改用單一日誌檔 + `RotatingFileHandler`（按大小輪轉），並比較和目前方案的優缺點。

3. **加入健康檢查端點**：寫一個 `hook-health-check.py` 腳本，檢查每個 Hook 目錄的最新日誌是否包含 `CRITICAL` 等級的記錄，輸出健康報告。

---

_上一章：[頂層例外處理機制](../error-infrastructure/)_
_相關：[重構陷阱與防護](../../07-refactoring/refactoring-pitfalls/) -- IMP-003/005/006 的重構角度分析_
_相關：[作用域迴歸案例研究](../../07-refactoring/scope-regression/) -- IMP-003 的完整技術分析_
