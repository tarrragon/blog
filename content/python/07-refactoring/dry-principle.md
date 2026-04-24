---
title: "DRY 原則與共用程式庫"
date: 2026-03-04
description: "學習識別重複程式碼並建立共用模組，含模組演進與漸進遷移策略"
weight: 73
---

_上一章：[程式碼壞味道偵測](/python/07-refactoring/code-smells/)_

DRY (Don't Repeat Yourself) 是軟體開發的核心原則之一。本章基於 Error Pattern IMP-001，學習如何識別重複程式碼並建立共用模組。後半部分以 v0.31.0 的模組演進和遷移實戰為例，示範共用庫如何隨系統成長持續演進。

## 問題背景

### 症狀

相同功能在多個檔案中重複實作：

```python
# hooks/pre_commit.py
def run_git_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

# hooks/post_merge.py  -- 完全相同
# hooks/branch_check.py  -- 完全相同
# hooks/worktree_guardian.py  -- 完全相同
```

四個檔案中存在完全相同的函式定義。

### 5 Why 分析

1. Why 1: 相同的 run_git_command 函式在 4 個檔案中重複
2. Why 2: 每個 Hook 獨立開發，沒有共用模組
3. Why 3: 缺乏 Hook 系統的架構設計和共用程式庫規劃
4. Why 4: 快速開發時複製貼上最快
5. Why 5: **缺乏 DRY 原則的強制檢查機制**

## DRY 原則核心

重複程式碼的四大壞處：**修改需改多處**、**容易不一致**、**增加維護成本**、**測試困難**。

DRY 的完整含義不只是「不要複製貼上」：

> Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.
>
> -- Andy Hunt & Dave Thomas, _The Pragmatic Programmer_

這意味著不只是程式碼，還包括業務邏輯、資料定義、設定內容。

## 識別重複程式碼

```bash
# 找出重複的函式定義
grep -rh "^def " .claude/hooks/*.py | sort | uniq -c | sort -rn | head -20

# 範例輸出：
#    4 def run_git_command(cmd):
#    3 def get_current_branch():
#    2 def parse_worktree_line(line):
```

| 重複類型 | 範例                 | 處理方式       |
| -------- | -------------------- | -------------- |
| 完全相同 | 複製貼上的程式碼     | 抽取到共用模組 |
| 結構相同 | 相似但參數不同       | 抽取並參數化   |
| 概念相同 | 做同樣的事但實作不同 | 統一介面       |

## 建立共用程式庫

### 模組結構

```
.claude/lib/
├── __init__.py           # 公開介面
├── git_utils.py          # Git 操作
├── config_loader.py      # 配置載入
├── hook_io.py            # 輸入輸出
└── hook_logging.py       # 日誌系統
```

### 抽取共用函式

從重複程式碼中抽取，加上完整的型別標註和 docstring：

```python
# lib/git_utils.py
"""Git 操作工具模組。"""

import subprocess
from pathlib import Path
from typing import List, Optional

def run_git_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    check: bool = False
) -> str:
    """執行 Git 命令並回傳輸出。

    Args:
        cmd: Git 命令列表，例如 ["git", "status"]
        cwd: 工作目錄，預設為當前目錄
        check: 是否在命令失敗時拋出異常
    """
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, check=check
    )
    return result.stdout.strip()

def get_current_branch(cwd: Optional[Path] = None) -> str:
    """取得當前分支名稱。"""
    return run_git_command(["git", "branch", "--show-current"], cwd=cwd)
```

### 更新使用處

```python
# hooks/pre_commit.py（重構後）
from lib.git_utils import run_git_command, get_current_branch

def check_branch():
    current_branch = get_current_branch()
    # 使用共用函式，不再重複定義
```

## 抽取技巧

### 處理微小差異

當重複程式碼有微小差異時，使用參數化：

```python
# 重構前：三個檔案各自的版本
# hooks/file_a.py
def parse_worktree_line(line):
    return line[9:]                        # 不 strip

# hooks/file_b.py
def parse_worktree_line(line):
    return line[9:].strip()                # 有 strip

# hooks/file_c.py
def parse_worktree_line(line):
    return line.removeprefix("worktree ")  # 用 Python 3.9+ API

# 重構後：統一實作，支援選項
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str, strip: bool = True) -> str:
    """解析 worktree 輸出行。"""
    result = line.removeprefix(WORKTREE_PREFIX)
    return result.strip() if strip else result
```

### 使用高階函式

當邏輯結構相同但操作不同時：

```python
from pathlib import Path
from typing import Callable

# 重構前
def check_all_python_files():
    for file in Path(".").glob("**/*.py"):
        if validate_python(file): print(f"OK: {file}")

def check_all_yaml_files():
    for file in Path(".").glob("**/*.yaml"):
        if validate_yaml(file): print(f"OK: {file}")

# 重構後
def check_files(pattern: str, validator: Callable[[Path], bool]) -> None:
    for file in Path(".").glob(pattern):
        if validator(file): print(f"OK: {file}")

check_files("**/*.py", validate_python)
check_files("**/*.yaml", validate_yaml)
```

## 共用模組設計原則

| 原則                 | 做法                                                                             | 反面教材                           |
| -------------------- | -------------------------------------------------------------------------------- | ---------------------------------- |
| **單一職責**         | `git_utils.py`（Git 操作）、`config_loader.py`（配置載入）。模組名稱即可看出職責 | `utils.py`（什麼都放，職責不明確） |
| **穩定的介面**       | 透過 `__init__.py` 定義公開 API，內部可自由重構                                  | 讓使用者直接 import 內部實作細節   |
| **完整的 docstring** | 每個公開函式都要有 docstring（Args/Returns/Raises）                              | 只有程式碼，沒有使用說明           |
| **充分的測試**       | 每個共用函式都要有對應的單元測試                                                 | 重構後不跑測試就上線               |

## 模組演進：從 4 個到 7+ 個

共用程式庫不是一次建完就結束，而是隨著系統成長持續演進。

### 模組演進表

| 版本    | 模組                | 職責                         | 說明                           |
| ------- | ------------------- | ---------------------------- | ------------------------------ |
| v0.28.0 | `git_utils.py`      | Git 命令執行、分支管理       | 消除 4 處 run_git_command 重複 |
| v0.28.0 | `hook_io.py`        | Hook JSON 輸入讀取、輸出生成 | 統一 stdin/stdout 處理         |
| v0.28.0 | `config_loader.py`  | YAML 配置檔案載入            | 支援 PyYAML fallback JSON      |
| v0.28.0 | `hook_logging.py`   | 日誌設定                     | 統一日誌格式                   |
| v0.31.0 | `hook_utils.py`     | 統一日誌 + 頂層例外處理      | 取代分散的兩套日誌系統         |
| v0.31.0 | `hook_messages.py`  | 訊息常數集中管理             | 消除 19 個 Hook 的硬編碼訊息   |
| v0.31.0 | `hook_validator.py` | Hook 健康檢查                | 驗證 import 和執行狀態         |

### 演進的驅動力

每次新增模組都有明確的驅動力，而非預先設計：

**v0.28.0（初建期）**：四個函式重複 → 建立四個共用模組。

**v0.31.0（成熟期）**：Hook 數量從 7 個成長到 40+ 個，新的重複模式浮現：

1. **日誌系統分裂**：`hook_logging.py` 和 `common_functions.setup_hook_logging` 兩套實作並存，40+ 個 Hook 各自選用。最終建立 `hook_utils.py` 統一取代
2. **訊息散落各處**：19 個 Hook 各自硬編碼使用者訊息 → 建立 `hook_messages.py` 集中管理

這驗證了「至少重複兩次再抽取」的 Rule of Three 原則：模組是在真實需求驅動下自然長出來的。

## 漸進遷移策略

共用庫建立後，需要將現有使用者逐步遷移。「一次全改」風險太高，以下是 W22 遷移 40+ 個 Hook 到新日誌系統的實戰策略。

### 分批遷移計畫

| 批次      | 範圍     | 檔案數 | 策略                     |
| --------- | -------- | ------ | ------------------------ |
| W22-001.2 | 主力遷移 | 14 個  | 按 Hook 事件類型分組遷移 |
| W22-001.3 | 補漏     | 3 個   | 掃描殘留的舊 import      |

### 每個 Hook 的遷移三步驟

```python
# === 步驟 1：替換 import ===
# 遷移前
from lib.common_functions import setup_hook_logging
# 遷移後
from hook_utils import setup_hook_logging

# === 步驟 2：包裹主函式 ===
# 遷移前
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"執行失敗: {e}")
        sys.exit(1)
# 遷移後
from hook_utils import run_hook_safely
if __name__ == "__main__":
    sys.exit(run_hook_safely(main, "my-hook"))

# === 步驟 3：驗證 ===
uv run python hook-name.py < /dev/null
```

### 為什麼分批而非一次全改

| 一次全改                     | 分批遷移                 |
| ---------------------------- | ------------------------ |
| 改動 40+ 個檔案，review 困難 | 每批 14-3 個，可仔細確認 |
| 一個錯誤影響所有 Hook        | 錯誤影響範圍有限         |
| 無法中途暫停                 | 每批獨立可交付           |
| 回滾等於全部回滾             | 只回滾出問題的批次       |

## 遷移陷阱：IMP-005

模組遷移最常見的陷阱是 **import 路徑未同步更新**。這個問題在系統中發生過兩次，我們將其記錄為 Error Pattern IMP-005。

### 症狀

模組從目錄 A 移到目錄 B 後，部分使用者的 import 忘記更新：

```python
# 遷移前（同目錄）
from common_functions import hook_output  # OK

# 遷移後（模組移到 lib/，但 import 未更新）
from common_functions import hook_output  # ModuleNotFoundError!

# 正確的遷移後 import
from lib.common_functions import hook_output  # OK
```

### 為什麼容易遺漏

1. **py_compile 不偵測 import 問題**：只檢查語法，不解析模組路徑
2. **部分 Hook 不常觸發**：SessionStart Hook 只在啟動時執行，測試不容易覆蓋
3. **多源錯誤疊加**：多個 Hook 同時報錯，修完幾個就以為全部修好

### 遷移前強制檢查清單

```bash
# 1. 列出所有引用舊路徑的檔案
grep -r "from common_functions import" .claude/hooks/*.py

# 2. 逐一更新每個引用者的 import 路徑

# 3. 逐一驗證（不能只跑其中幾個！）
for f in .claude/hooks/*.py; do
    uv run python "$f" < /dev/null 2>&1 | grep -q "Error" && echo "FAIL: $f"
done
```

### Import 防護機制

在 Hook 入口加 try-except，讓 import 失敗時顯示具體原因：

```python
try:
    from hook_utils import setup_hook_logging
except ImportError as e:
    print(f"[Hook Import Error] {Path(__file__).name}: {e}", file=sys.stderr)
    sys.exit(1)
```

## 實際案例統計

v0.28.0 初建共用庫：

| 函式                | 重複次數 | 重構後           |
| ------------------- | -------- | ---------------- |
| run_git_command     | 4        | 1 (git_utils.py) |
| get_current_branch  | 3        | 1 (git_utils.py) |
| parse_worktree_line | 2        | 1 (git_utils.py) |
| load_json           | 2        | 1 (hook_io.py)   |

總計消除數百行重複程式碼。

v0.31.0 持續演進：

| 項目               | 重複次數          | 重構後               |
| ------------------ | ----------------- | -------------------- |
| setup_hook_logging | 2 套系統          | 1 (hook_utils.py)    |
| run_hook_safely    | 40+ 處 try-except | 1 (hook_utils.py)    |
| 使用者訊息字串     | 19 個 Hook 散落   | 1 (hook_messages.py) |

## 常見錯誤

### 錯誤 1：過早抽象

只用一次就抽出去是過度抽象。**原則**：至少重複兩次再抽取（Rule of Three）。

### 錯誤 2：強行統一

不同概念硬塞進同一個函式（靠 mode 參數切換）。**解決**：不同概念應該是不同的函式。

### 錯誤 3：忽略測試

重構時沒有先寫測試，導致引入新 bug。**原則**：先寫測試，確保重構不改變行為。

### 錯誤 4：遷移不徹底

模組搬家後只更新「自己知道的」使用處。**原則**：用 grep 列出所有引用，逐一更新並驗證（詳見 IMP-005）。

## 實作練習

### 練習 1：識別重複

找出以下程式碼的可抽取重複：

```python
# file1.py
def process_user_data(user):
    if not user.get("name"):
        return {"error": "缺少姓名"}
    if not user.get("email"):
        return {"error": "缺少信箱"}
    return {"success": True, "data": user}

# file2.py
def process_order_data(order):
    if not order.get("product"):
        return {"error": "缺少商品"}
    if not order.get("quantity"):
        return {"error": "缺少數量"}
    return {"success": True, "data": order}
```

<details>
<summary>參考答案</summary>

```python
def validate_required_fields(data: dict, required_fields: list) -> dict:
    """驗證必填欄位。"""
    for field in required_fields:
        if not data.get(field):
            return {"error": f"缺少{field}"}
    return {"success": True, "data": data}

def process_user_data(user: dict) -> dict:
    return validate_required_fields(user, ["name", "email"])

def process_order_data(order: dict) -> dict:
    return validate_required_fields(order, ["product", "quantity"])
```

</details>

### 練習 2：規劃遷移策略

20 個 Hook 要從 `from common_functions import setup_logging` 遷移到 `from hook_utils import setup_hook_logging`，請規劃遷移策略。

<details>
<summary>參考答案</summary>

```bash
# 1. 盤點
grep -rl "from common_functions import" .claude/hooks/*.py | wc -l

# 2. 分批（按事件類型）
# 第一批：SessionStart hooks（啟動就能看到）
# 第二批：UserPromptSubmit hooks
# 第三批：PreToolUse / PostToolUse hooks

# 3. 逐批執行，每批完成後 commit

# 4. 全量掃描（不可省略！防止 IMP-005）
grep -r "from common_functions import" .claude/hooks/*.py
# 預期輸出：空
```

</details>

## 小結

- DRY 原則要求每個知識只有單一權威來源，用 `grep` 識別重複的函式定義
- 不要過早抽象，至少重複兩次再抽取（Rule of Three）
- 建立結構清晰的共用程式庫，重構前先寫測試確保行為不變
- 共用庫隨系統成長持續演進，大規模遷移採用分批策略
- 模組搬家後必須全量 `grep` 引用並逐一驗證，防止 IMP-005 陷阱

_下一章：[配置分離與常數管理](/python/07-refactoring/constants-management/)_

---

_文件版本：v0.31.1_
_建立日期：2026-03-04_
