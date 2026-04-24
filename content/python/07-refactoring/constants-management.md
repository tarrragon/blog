---
title: "配置分離與常數管理"
date: 2026-03-04
description: "學習消除三種硬編碼問題：魔法數字、配置混合、散落訊息"
weight: 74
---


*上一章：[DRY 原則與共用程式庫](/python/07-refactoring/dry-principle/)*

硬編碼問題不只是魔法數字。當專案成長到數十個模組時，三種不同形態的硬編碼會同時出現：看不懂的數字、混在邏輯裡的配置資料、散落各處的使用者訊息。本章整合 Error Pattern IMP-002（魔法數字）和 ARCH-001（配置與邏輯混合）的實戰經驗，並加入 W23 訊息集中化的完整案例。

---

## 三種硬編碼問題

在維護 19 個 Hook 模組的過程中，我們遇到了三種不同但相關的硬編碼問題：

| 類型     | Error Pattern | 典型症狀                               | 危害                             |
| -------- | ------------- | -------------------------------------- | -------------------------------- |
| 魔法數字 | IMP-002       | `line[9:]`、`sleep(3)`、`range(5)`     | 無法理解數字含義，修改時容易遺漏 |
| 配置混合 | ARCH-001      | 800 行檔案中 400 行是配置資料          | 配置散落各處，同一資料有多個版本 |
| 散落訊息 | W23 發現      | 57+ 個硬編碼中文字串散落在 19 個檔案中 | 訊息不一致，無法統一維護         |

三種問題的共同根因：**開發時為求快速，把應該集中管理的資料直接寫在邏輯程式碼裡。**

---

## 一、消除魔法數字 (IMP-002)

魔法數字是程式碼中無法理解含義的字面值：

```python
def parse_worktree_line(line: str) -> str:
    if line.startswith("worktree "):
        return line[9:]  # 為什麼是 9？
    return line

if len(branch) > 50:    # 為什麼是 50？
    raise Error("分支名稱過長")

time.sleep(3)           # 為什麼等 3 秒？
```

問題不只是可讀性。當前綴改成 `"work tree "` 時，`line[9:]` 不會自動更新，產生隱蔽的 bug。

### 三種消除方法

**方法 1：len() 動態計算（最安全）**

```python
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str) -> str:
    if line.startswith(WORKTREE_PREFIX):
        return line[len(WORKTREE_PREFIX):]
    return line
```

前綴改變時切片自動正確，不需要同步更新數字。

**方法 2：removeprefix（最簡潔，Python 3.9+）**

```python
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str) -> str:
    return line.removeprefix(WORKTREE_PREFIX)
```

不需要先檢查 `startswith`，沒有前綴時安全返回原字串。

**方法 3：IntEnum 管理相關常數群組**

```python
from enum import IntEnum

class Limits(IntEnum):
    MAX_BRANCH_LENGTH = 50
    MAX_COMMIT_MSG_LENGTH = 72
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

if len(branch) > Limits.MAX_BRANCH_LENGTH:
    raise ValueError("分支名稱過長")
```

### 常見處理對照

| 場景     | 壞            | 好                           |
| -------- | ------------- | ---------------------------- |
| 字串切片 | `line[7:]`    | `line.removeprefix(PREFIX)`  |
| 時間限制 | `sleep(3)`    | `sleep(RETRY_DELAY_SECONDS)` |
| 大小限制 | `len(x) > 50` | `len(x) > MAX_BRANCH_LENGTH` |
| 重試次數 | `range(5)`    | `range(MAX_RETRIES)`         |

### 可接受的例外

不是所有數字都需要命名：

```python
if count == 0:               # 可接受：0 在布林邏輯中
if text.find("key") == -1:   # 可接受：-1 作為找不到的標記
half = total / 2              # 可接受：明顯的數學常數
```

判斷標準：**如果閱讀者需要思考「這個數字為什麼是這個值」，就應該命名。**

---

## 二、YAML 配置分離 (ARCH-001)

### 問題識別

單一 Hook 檔案超過 800 行，其中約一半是硬編碼的配置資料：

```python
# user_prompt_submit.py (847 行，配置佔 400+)
PROTECTED_BRANCHES = ["main", "master", "develop"]
ALLOWED_PATTERNS = ["feat/*", "fix/*", "chore/*"]
ERROR_MESSAGES = {
    "branch_not_allowed": "分支名稱不符合規範",
    "missing_ticket": "缺少 Ticket 引用",
    # ... 數百行配置
}

def main():
    # 實際邏輯只有 200 行
    pass
```

更嚴重的是，同一份配置在多個檔案中各自定義，彼此不一致：

```python
# file1.py
PROTECTED_BRANCHES = ["main", "master"]
# file2.py
PROTECTED_BRANCHES = ["main", "master", "develop"]  # 多了 develop！
```

### 判斷標準

| 問題                 | 若答「是」 | 放置位置               |
| -------------------- | ---------- | ---------------------- |
| 會隨環境改變？       | 是         | YAML 配置檔            |
| 非工程師可能修改？   | 是         | YAML 配置檔            |
| 是業務規則？         | 是         | 程式碼常數檔（附註解） |
| 與程式邏輯緊密耦合？ | 是         | 程式碼內常數           |

簡單記憶：**資料放配置，邏輯留程式碼。**

### 實作：config_loader 模式

**步驟 1：抽離配置到 YAML**

```yaml
# config/branch_rules.yaml
protected_branches:
  - main
  - master
  - develop

allowed_patterns:
  - "feat/*"
  - "fix/*"
  - "chore/*"

error_messages:
  branch_not_allowed: "分支名稱不符合規範"
  missing_ticket: "缺少 Ticket 引用"
```

**步驟 2：建立載入器（含快取）**

```python
# lib/config_loader.py
from pathlib import Path
from typing import Any, Dict
import yaml

_config_cache: Dict[str, Any] = {}

def load_config(filename: str) -> Dict[str, Any]:
    """載入 YAML 配置檔案（含快取）。"""
    if filename in _config_cache:
        return _config_cache[filename]

    config_path = Path(__file__).parent.parent / "config" / filename
    if not config_path.exists():
        raise FileNotFoundError(f"配置檔案不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _config_cache[filename] = config
    return config
```

**步驟 3：在 Hook 中使用**

```python
from lib.config_loader import load_config

def check_branch():
    config = load_config("branch_rules.yaml")
    if current_branch in config["protected_branches"]:
        print(f"錯誤: {config['error_messages']['branch_not_allowed']}")
        return False
    return True
```

重構後結構：847 行的單一檔案拆成約 200 行純邏輯 + `config/` 目錄的 YAML 檔 + 共用的 `config_loader.py`。

### 常見錯誤

**過度配置化** -- 把程式邏輯也放進配置檔：

```yaml
# 錯誤：這是邏輯，不是資料
process_steps:
  - name: "validate"
    function: "validate_input"
```

**缺乏預設值** -- 沒有處理配置缺失：

```python
timeout = config["timeout"]        # KeyError!
timeout = config.get("timeout", 30)  # 正確
```

---

## 三、訊息集中化 (W23)

消除魔法數字和分離配置後，還有一種硬編碼藏在邏輯裡：使用者訊息字串。

W23 審計發現 19 個 Hook 中散落了 57+ 個硬編碼中文字串：

```python
# hook_a.py
print("錯誤：未找到待處理的 Ticket")
print("建議執行 /ticket create 建立新 Ticket")

# hook_b.py
print("錯誤：未找到待處理的 Ticket")  # 同一訊息，略有不同
print("請先建立 Ticket 再執行")
```

同一個錯誤概念有 2-3 種不同措辭，修改一則訊息需要搜尋所有檔案。

### Messages 類別模式

解決方案：建立 `hook_messages.py`，用類別分組管理所有訊息常數。

```python
# lib/hook_messages.py
class CoreMessages:
    """Hook 執行通用訊息 - 所有 Hook 共用"""
    HOOK_START = "{hook_name} 啟動"
    INPUT_EMPTY = "輸入為空，預設允許"
    JSON_PARSE_ERROR = "JSON 解析錯誤，預設允許: {error}"

class GateMessages:
    """Gate Hook 阻擋訊息 - 5 個 gate hooks 使用"""
    TICKET_NOT_FOUND_ERROR = """錯誤：未找到待處理的 Ticket
建議: 執行 /ticket create 建立新 Ticket"""

    TICKET_NOT_CLAIMED_ERROR = """錯誤：Ticket {ticket_id} 尚未認領
建議: 執行 /ticket track claim {ticket_id} 認領"""

class WorkflowMessages:
    """工作流指導訊息 - 5 個工作流 hooks 使用"""
    PRE_FIX_EVAL_REQUIRED = """[強制] 修復前評估
  1. 執行 /pre-fix-eval
  2. 派發 incident-responder 分析"""
```

最終產出 7 個 Messages 類別，管理約 45 個訊息常數。

### 使用方式

Hook 中引用常數，使用 `.format()` 填入動態值：

```python
from lib.hook_messages import GateMessages

def validate_ticket(ticket_id: str):
    if not is_claimed(ticket_id):
        print(GateMessages.TICKET_NOT_CLAIMED_ERROR.format(
            ticket_id=ticket_id
        ))
        return False
    return True
```

### 組織原則

| 分類依據   | 類別名稱             | 涵蓋範圍                        |
| ---------- | -------------------- | ------------------------------- |
| 核心通用   | `CoreMessages`       | 所有 Hook 共用的啟動、錯誤訊息  |
| 阻擋訊息   | `GateMessages`       | 5 個 Gate Hook 的阻止原因和建議 |
| 工作流指導 | `WorkflowMessages`   | 5 個工作流 Hook 的流程提示      |
| 品質檢查   | `QualityMessages`    | 5 個品質 Hook 的檢查結果        |
| 驗證相關   | `ValidationMessages` | 驗證 Hook 的成功/失敗訊息       |

分類原則：**按使用者角色和觸發情境分組，而不是按技術功能。**

### 命名規範

| 常數類型      | 命名規則              | 範例                            |
| ------------- | --------------------- | ------------------------------- |
| 訊息常數      | 大寫蛇形              | `TICKET_NOT_FOUND_ERROR`        |
| Messages 類別 | PascalCase + Messages | `GateMessages`                  |
| 格式化佔位符  | `{variable_name}`     | `"Ticket {ticket_id} 尚未認領"` |

### W23 實際數據

| 指標           | 重構前            | 重構後                |
| -------------- | ----------------- | --------------------- |
| 硬編碼訊息位置 | 散落 19 個檔案    | 集中 1 個檔案         |
| 訊息總數       | 57+ 個（含重複）  | 45 個（去重後）       |
| 修改訊息需搜尋 | 所有 Hook 檔案    | 只需 hook_messages.py |
| 訊息一致性     | 同概念 2-3 種措辭 | 每個概念一個定義      |

---

## 決策框架

遇到硬編碼時，用這張表判斷該怎麼處理：

| 硬編碼類型   | 識別特徵               | 處理方式                            | 存放位置             |
| ------------ | ---------------------- | ----------------------------------- | -------------------- |
| 魔法數字     | 裸露的數字或字串切片   | 具名常數、`len()`、`removeprefix()` | 同檔案頂部或常數模組 |
| 配置資料     | 清單、規則表、業務參數 | 抽離到 YAML 配置檔                  | `config/` 目錄       |
| 使用者訊息   | 字串直接嵌入邏輯       | 提取到 Messages 類別                | `lib/*_messages.py`  |
| 程式邏輯常數 | 與邏輯緊密耦合的值     | 具名常數，保留在程式碼              | 檔案頂部             |

### 決策流程

```
發現硬編碼
    |
    v
會隨環境改變？ ─是→ YAML 配置檔
    |
    否
    v
是使用者看到的文字？ ─是→ Messages 類別
    |
    否
    v
是無法理解的數字？ ─是→ 具名常數 / len() / removeprefix()
    |
    否
    v
保留原樣（程式邏輯的一部分）
```

---

## 完整重構範例

### 重構前

```python
def validate_branch(branch):
    if len(branch) > 50:
        return False
    if branch.startswith("refs/heads/"):
        branch = branch[11:]
    for i in range(3):
        if check_remote(branch):
            return True
        time.sleep(2)
    return False
```

### 重構後

```python
MAX_BRANCH_LENGTH = 50
REFS_HEADS_PREFIX = "refs/heads/"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

def validate_branch(branch: str) -> bool:
    """驗證分支名稱。"""
    if len(branch) > MAX_BRANCH_LENGTH:
        return False
    branch = branch.removeprefix(REFS_HEADS_PREFIX)
    for attempt in range(MAX_RETRIES):
        if check_remote(branch):
            return True
        time.sleep(RETRY_DELAY_SECONDS)
    return False
```

四個魔法數字全部消除，每個值的含義一目了然。

---

## 檢測方法

```bash
# 找出數字切片（潛在魔法數字）
grep -rn "\[[0-9]*:\]" hooks/*.py

# 找出 sleep 和 range 中的硬編碼
grep -rn "sleep([0-9]" hooks/*.py
grep -rn "range([0-9]" hooks/*.py

# 找出硬編碼中文字串（潛在散落訊息）
grep -rn '[一-龥]' hooks/*.py
```

---

## 實作練習

找出以下程式碼中的三種硬編碼問題，並提出修正方案：

```python
def process_hook_result(result_line):
    if result_line.startswith("status: "):
        status = result_line[8:]
    else:
        status = "unknown"

    if len(status) > 100:
        print("狀態文字過長，已截斷")
        status = status[:97] + "..."

    VALID_STATUSES = ["pass", "fail", "skip", "error"]
    if status not in VALID_STATUSES:
        print("無效的狀態值: " + status)
        return None
    return status
```

<details>
<summary>參考答案</summary>

三種硬編碼問題：

1. **魔法數字**：`result_line[8:]`、`100`、`97`
2. **配置資料**：`VALID_STATUSES` 清單應該可配置
3. **散落訊息**：`"狀態文字過長，已截斷"`、`"無效的狀態值: "`

```python
from lib.config_loader import load_config

STATUS_PREFIX = "status: "
MAX_STATUS_LENGTH = 100
ELLIPSIS = "..."

class HookResultMessages:
    STATUS_TRUNCATED = "狀態文字過長，已截斷"
    INVALID_STATUS = "無效的狀態值: {status}"

def process_hook_result(result_line: str) -> str | None:
    status = result_line.removeprefix(STATUS_PREFIX)
    if status == result_line:
        status = "unknown"

    if len(status) > MAX_STATUS_LENGTH:
        print(HookResultMessages.STATUS_TRUNCATED)
        truncate_at = MAX_STATUS_LENGTH - len(ELLIPSIS)
        status = status[:truncate_at] + ELLIPSIS

    config = load_config("hook_rules.yaml")
    if status not in config["valid_statuses"]:
        print(HookResultMessages.INVALID_STATUS.format(status=status))
        return None
    return status
```

</details>

---

## 小結

- 硬編碼問題有三種形態：魔法數字、配置混合、散落訊息
- 魔法數字用 `len()`、`removeprefix()`、`IntEnum` 消除
- 配置資料用 YAML 檔案集中管理，透過 `config_loader` 載入
- 使用者訊息用 Messages 類別集中化，按角色和情境分組
- 決策關鍵：**會隨環境改變 → 配置檔；是使用者文字 → Messages；是裸露數字 → 常數**

*下一章：[大規模統一化重構](/python/07-refactoring/unified-infrastructure/)*

---

*文件版本：v0.31.1*
*建立日期：2026-03-04*
