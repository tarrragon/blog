---
title: "消除魔法數字"
description: "學習用具名常數替代難以理解的數字"
weight: 74
---

# 消除魔法數字

「魔法數字」(Magic Number) 是程式碼中難以理解其含義的數字常數。本章基於 Error Pattern IMP-002，學習如何識別和消除魔法數字。

## 問題背景

### 症狀

程式碼中出現無法理解其含義的數字或字串切片：

```python
# 看到 line[9:] 無法理解為什麼是 9
def parse_worktree_line(line: str) -> str:
    if line.startswith("worktree "):
        return line[9:]  # 魔法數字：為什麼是 9？
    return line

# 其他常見的魔法數字
if len(branch) > 50:  # 為什麼是 50？
    raise Error("分支名稱過長")

time.sleep(3)  # 為什麼等 3 秒？

for i in range(5):  # 為什麼重試 5 次？
    try_operation()
```

### 5 Why 分析

1. Why 1: 程式碼中出現難以理解的數字 `line[9:]`
2. Why 2: 開發時知道 "worktree " 長度是 9，直接寫數字
3. Why 3: 快速開發時忽略可讀性
4. Why 4: 沒有程式碼審查機制檢查魔法數字
5. Why 5: **缺乏「自文件化程式碼」的開發習慣和規範**

## 為什麼魔法數字是問題

### 1. 可讀性差

```python
# 閱讀這段程式碼時的疑問
if response_time > 3000:  # 3000 是什麼？毫秒？秒？
    timeout_handler()
```

### 2. 維護困難

```python
# 需要修改逾時時間時，要找出所有 3000
if response_time > 3000:
    ...
if average_time > 3000:
    ...
# 這兩個 3000 是同一個概念嗎？
```

### 3. 容易出錯

```python
# "worktree " 是 9 個字元，但如果前綴改了呢？
WORKTREE_PREFIX = "work tree "  # 改成 10 個字元
return line[9:]  # 忘記更新！
```

## 解決方案

### 方法 1：使用 len() 動態計算

最安全的做法，讓程式碼自己計算長度：

```python
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str) -> str:
    """解析 worktree 輸出行。"""
    if line.startswith(WORKTREE_PREFIX):
        return line[len(WORKTREE_PREFIX):]
    return line
```

優點：
- 前綴改變時，切片自動正確
- 程式碼自文件化

### 方法 2：使用具名常數

當需要預計算以提升效能時：

```python
WORKTREE_PREFIX = "worktree "
WORKTREE_PREFIX_LEN = len(WORKTREE_PREFIX)  # 9

def parse_worktree_line(line: str) -> str:
    """解析 worktree 輸出行。"""
    if line.startswith(WORKTREE_PREFIX):
        return line[WORKTREE_PREFIX_LEN:]
    return line
```

### 方法 3：使用 removeprefix (Python 3.9+)

最優雅的解決方案：

```python
WORKTREE_PREFIX = "worktree "

def parse_worktree_line(line: str) -> str:
    """解析 worktree 輸出行。"""
    return line.removeprefix(WORKTREE_PREFIX)
```

優點：
- 不需要先檢查 startswith
- 沒有前綴時安全返回原字串
- 程式碼最簡潔

## 常見魔法數字處理

### 字串長度

```python
# 壞
text = line[7:]

# 好
PREFIX = "status "
text = line.removeprefix(PREFIX)
# 或
text = line[len(PREFIX):]
```

### 時間限制

```python
# 壞
time.sleep(3)
if elapsed > 30000:
    timeout()

# 好
RETRY_DELAY_SECONDS = 3
TIMEOUT_MS = 30000

time.sleep(RETRY_DELAY_SECONDS)
if elapsed > TIMEOUT_MS:
    timeout()
```

### 大小限制

```python
# 壞
if len(branch) > 50:
    raise Error("分支名稱過長")

# 好
MAX_BRANCH_LENGTH = 50  # Git 建議的分支名稱長度

if len(branch) > MAX_BRANCH_LENGTH:
    raise Error("分支名稱過長")
```

### 重試次數

```python
# 壞
for i in range(5):
    if try_operation():
        break

# 好
MAX_RETRIES = 5

for attempt in range(MAX_RETRIES):
    if try_operation():
        break
```

### 索引和位置

```python
# 壞
parts = line.split()
if len(parts) > 2:
    return parts[2]

# 好
# 定義清晰的欄位索引
FIELD_STATUS = 0
FIELD_PATH = 1
FIELD_BRANCH = 2

parts = line.split()
if len(parts) > FIELD_BRANCH:
    return parts[FIELD_BRANCH]
```

## 進階技巧

### 使用 Enum 管理相關常數

當有一組相關的數值常數時：

```python
from enum import IntEnum

class Limits(IntEnum):
    """系統限制常數。"""
    MAX_BRANCH_LENGTH = 50
    MAX_COMMIT_MSG_LENGTH = 72
    MAX_FILE_SIZE_MB = 100
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

# 使用
if len(branch) > Limits.MAX_BRANCH_LENGTH:
    raise ValueError("分支名稱過長")

for _ in range(Limits.MAX_RETRIES):
    try_operation()
```

### 使用 dataclass 組織配置

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class GitConfig:
    """Git 相關配置。"""
    max_branch_length: int = 50
    max_commit_msg_length: int = 72
    default_remote: str = "origin"

CONFIG = GitConfig()

# 使用
if len(branch) > CONFIG.max_branch_length:
    raise ValueError("分支名稱過長")
```

### 常數命名規範

| 命名模式 | 用途 | 範例 |
|---------|------|------|
| MAX_* | 最大限制 | MAX_RETRIES |
| MIN_* | 最小限制 | MIN_PASSWORD_LENGTH |
| DEFAULT_* | 預設值 | DEFAULT_TIMEOUT |
| *_PREFIX | 字串前綴 | WORKTREE_PREFIX |
| *_SUFFIX | 字串後綴 | LOG_SUFFIX |

## 檢測方法

### 找出數字切片

```bash
# 找出可能的魔法數字（數字切片）
grep -rn "\[[0-9]*:\]" .claude/hooks/*.py
grep -rn "\[:[0-9]*\]" .claude/hooks/*.py

# 範例輸出：
# hooks/worktree.py:23:    return line[9:]
# hooks/branch.py:45:    name = ref[:50]
```

### 找出硬編碼數字

```bash
# 找出 sleep 中的硬編碼
grep -rn "sleep([0-9]" .claude/hooks/*.py

# 找出 range 中的硬編碼
grep -rn "range([0-9]" .claude/hooks/*.py

# 找出比較中的硬編碼
grep -rn "> [0-9][0-9]" .claude/hooks/*.py
grep -rn "< [0-9][0-9]" .claude/hooks/*.py
```

### 程式碼審查清單

- [ ] 是否有裸露的數字（0、1 除外）？
- [ ] 是否有字串切片使用硬編碼索引？
- [ ] 是否有 sleep、range 使用硬編碼數字？
- [ ] 是否有比較運算使用硬編碼閾值？

## 特殊情況

### 可接受的魔法數字

某些數字本身就是自文件化的：

```python
# 可接受：0 和 1 在布林邏輯中
if count == 0:
    return "無資料"

# 可接受：-1 作為找不到的標記
index = text.find("keyword")
if index == -1:
    print("找不到")

# 可接受：明顯的數學常數
half = total / 2
doubled = value * 2
```

### 不要過度命名

```python
# 過度：為明顯的值命名
ZERO = 0
ONE = 1
TWO = 2

# 這樣只是增加閱讀負擔
if count == ZERO:
    ...
```

### 權衡：可讀性 vs 簡潔

```python
# 如果只用一次，有時直接寫註解更清楚
time.sleep(3)  # 等待資料庫連線穩定

# 如果多處使用，定義常數
DB_CONNECTION_DELAY = 3  # 秒
time.sleep(DB_CONNECTION_DELAY)
```

## 重構範例

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
# 定義常數
MAX_BRANCH_LENGTH = 50
REFS_HEADS_PREFIX = "refs/heads/"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

def validate_branch(branch: str) -> bool:
    """驗證分支名稱。

    Args:
        branch: 分支名稱（可能包含 refs/heads/ 前綴）

    Returns:
        是否為有效的分支
    """
    if len(branch) > MAX_BRANCH_LENGTH:
        return False

    # 移除 refs/heads/ 前綴
    branch = branch.removeprefix(REFS_HEADS_PREFIX)

    # 重試檢查遠端
    for attempt in range(MAX_RETRIES):
        if check_remote(branch):
            return True
        time.sleep(RETRY_DELAY_SECONDS)

    return False
```

## 實作練習

### 練習 1：識別魔法數字

找出以下程式碼中的魔法數字：

```python
def process_log(log_line):
    timestamp = log_line[:19]
    level = log_line[20:27]
    message = log_line[29:]

    if len(message) > 500:
        message = message[:497] + "..."

    return {
        "time": timestamp,
        "level": level.strip(),
        "msg": message
    }
```

<details>
<summary>參考答案</summary>

魔法數字：
- `[:19]` - timestamp 長度
- `[20:27]` - level 位置
- `[29:]` - message 起始位置
- `500` - 訊息長度限制
- `497` - 截斷位置
- `"..."` - 省略符號

重構後：

```python
# 日誌格式：2024-01-20 12:34:56 [INFO]  Message here
TIMESTAMP_LENGTH = 19  # "2024-01-20 12:34:56"
LEVEL_START = 20
LEVEL_END = 27  # "[INFO] "
MESSAGE_START = 29

MAX_MESSAGE_LENGTH = 500
ELLIPSIS = "..."

def process_log(log_line: str) -> dict:
    """解析日誌行。"""
    timestamp = log_line[:TIMESTAMP_LENGTH]
    level = log_line[LEVEL_START:LEVEL_END]
    message = log_line[MESSAGE_START:]

    if len(message) > MAX_MESSAGE_LENGTH:
        truncate_at = MAX_MESSAGE_LENGTH - len(ELLIPSIS)
        message = message[:truncate_at] + ELLIPSIS

    return {
        "time": timestamp,
        "level": level.strip(),
        "msg": message
    }
```

</details>

### 練習 2：選擇最佳解法

對於字串前綴處理，哪種方式最好？

```python
# 方案 A
if line.startswith("error: "):
    return line[7:]

# 方案 B
ERROR_PREFIX = "error: "
if line.startswith(ERROR_PREFIX):
    return line[len(ERROR_PREFIX):]

# 方案 C
ERROR_PREFIX = "error: "
return line.removeprefix(ERROR_PREFIX)
```

<details>
<summary>參考答案</summary>

**方案 C 最佳**（Python 3.9+）

理由：
1. 最簡潔，沒有重複的 startswith 檢查
2. 自動處理沒有前綴的情況
3. 常數定義讓前綴值清楚

如果使用 Python 3.8 或更早版本，選擇方案 B。

方案 A 是最不建議的，因為：
1. `7` 是魔法數字
2. 如果前綴改變，需要同時修改兩處

</details>

## 小結

- 魔法數字降低程式碼可讀性和可維護性
- 使用具名常數取代裸露的數字
- 對於字串切片，優先使用 `removeprefix()` 或 `len()`
- 使用 Enum 或 dataclass 組織相關常數
- 不要過度命名明顯的值（0、1、2 等）

## 下一步

- [重構案例研究](../case-study/) - 看完整的重構流程

---

*文件版本：v0.30.0*
*建立日期：2026-01-20*
