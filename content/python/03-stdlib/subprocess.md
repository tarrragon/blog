---
title: "3.3 subprocess - 執行外部命令"
description: "呼叫系統命令和外部程式"
weight: 3
---

# subprocess - 執行外部命令

`subprocess` 模組讓你從 Python 程式中執行外部命令。在 Hook 系統中，主要用於執行 Git 命令。

## 基本用法

### subprocess.run()

最推薦的方式，Python 3.5+ 引入：

```python
import subprocess

# 基本執行
result = subprocess.run(["ls", "-la"])

# 捕獲輸出
result = subprocess.run(
    ["ls", "-la"],
    capture_output=True,
    text=True
)
print(result.stdout)  # 標準輸出
print(result.stderr)  # 錯誤輸出
print(result.returncode)  # 返回碼
```

## 實際範例：Git 操作

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

    Args:
        args: git 命令參數列表（不含 'git'）
        cwd: 執行目錄，預設為當前目錄
        timeout: 命令超時時間（秒）

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
        return False, f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return False, "git command not found"
    except Exception as e:
        return False, str(e)
```

使用範例：

```python
# 取得當前分支
success, output = run_git_command(["branch", "--show-current"])
if success:
    print(f"Current branch: {output}")

# 取得專案根目錄
success, output = run_git_command(["rev-parse", "--show-toplevel"])

# 取得 worktree 列表
success, output = run_git_command(["worktree", "list", "--porcelain"])
```

## 重要參數

### capture_output

捕獲標準輸出和錯誤輸出：

```python
# 捕獲輸出
result = subprocess.run(
    ["git", "status"],
    capture_output=True,  # 等同於 stdout=PIPE, stderr=PIPE
    text=True
)

# 等價寫法
result = subprocess.run(
    ["git", "status"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

### text

將輸出解碼為字串（而非 bytes）：

```python
# text=False（預設）
result = subprocess.run(["echo", "hello"], capture_output=True)
print(result.stdout)  # b'hello\n'（bytes）

# text=True
result = subprocess.run(["echo", "hello"], capture_output=True, text=True)
print(result.stdout)  # 'hello\n'（str）
```

### cwd

指定工作目錄：

```python
result = subprocess.run(
    ["git", "status"],
    cwd="/path/to/repo",
    capture_output=True,
    text=True
)
```

### timeout

設定超時時間（秒）：

```python
try:
    result = subprocess.run(
        ["long_running_command"],
        timeout=10,
        capture_output=True
    )
except subprocess.TimeoutExpired:
    print("Command timed out!")
```

### check

自動檢查返回碼：

```python
try:
    # 如果返回碼非零，拋出 CalledProcessError
    result = subprocess.run(
        ["git", "status"],
        check=True,
        capture_output=True,
        text=True
    )
except subprocess.CalledProcessError as e:
    print(f"Command failed with return code {e.returncode}")
    print(f"Error output: {e.stderr}")
```

## 錯誤處理

### 常見異常

```python
import subprocess

def safe_run_command(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        return False, "Command timed out"

    except FileNotFoundError:
        return False, f"Command not found: {args[0]}"

    except PermissionError:
        return False, f"Permission denied: {args[0]}"

    except Exception as e:
        return False, str(e)
```

## 安全考量

### 避免 shell=True

```python
# 危險：使用者輸入可能導致命令注入
user_input = "file.txt; rm -rf /"
subprocess.run(f"cat {user_input}", shell=True)  # 危險！

# 安全：使用列表傳遞參數
subprocess.run(["cat", user_input])  # 安全
```

### 驗證輸入

```python
def run_git_command(args: list[str]) -> tuple[bool, str]:
    # 驗證第一個參數是否為有效的 git 子命令
    valid_commands = ["status", "branch", "log", "diff", "rev-parse"]
    if args and args[0] not in valid_commands:
        return False, f"Invalid git command: {args[0]}"
    # ...
```

## 進階用法

### 管道（Pipe）

```python
# 模擬 "ls -la | grep .py"
ls_process = subprocess.run(
    ["ls", "-la"],
    capture_output=True,
    text=True
)

grep_process = subprocess.run(
    ["grep", ".py"],
    input=ls_process.stdout,
    capture_output=True,
    text=True
)
```

### 環境變數

```python
import os

# 自訂環境變數
env = os.environ.copy()
env["MY_VAR"] = "value"

result = subprocess.run(
    ["my_script.sh"],
    env=env,
    capture_output=True
)
```

## 實際應用：分支資訊

```python
def get_current_branch() -> Optional[str]:
    """獲取當前分支名稱"""
    success, output = run_git_command(["branch", "--show-current"])
    return output if success and output else None

def get_project_root() -> str:
    """獲取專案根目錄"""
    success, output = run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else os.getcwd()

def get_worktree_list() -> list[dict]:
    """獲取所有 worktree 列表"""
    success, output = run_git_command(["worktree", "list", "--porcelain"])
    if not success:
        return []

    worktrees = []
    current_worktree = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current_worktree:
                worktrees.append(current_worktree)
            current_worktree = {"path": line[9:]}  # 移除 "worktree " 前綴
        elif line.startswith("branch "):
            branch_ref = line[7:]  # 移除 "branch " 前綴
            if branch_ref.startswith("refs/heads/"):
                branch_ref = branch_ref[11:]
            current_worktree["branch"] = branch_ref

    if current_worktree:
        worktrees.append(current_worktree)

    return worktrees
```

## 最佳實踐

### 1. 使用列表而非字串

```python
# 好
subprocess.run(["git", "commit", "-m", "Fix bug"])

# 不好
subprocess.run("git commit -m 'Fix bug'", shell=True)
```

### 2. 設定合理的超時

```python
# 為長時間運行的命令設定超時
subprocess.run(["long_task"], timeout=300)  # 5 分鐘
```

### 3. 處理所有可能的錯誤

```python
def robust_run(args):
    try:
        result = subprocess.run(args, ...)
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)
```

## 思考題

1. 為什麼 `run_git_command` 返回 `tuple[bool, str]` 而不是直接拋出異常？
2. `shell=True` 有什麼風險？什麼情況下必須使用？
3. 如何實作一個可以同時執行多個命令的函式？

## 實作練習

1. 寫一個函式，執行命令並即時顯示輸出（不等待完成）
2. 實作一個命令重試機制（失敗時自動重試 N 次）
3. 寫一個函式，執行多個命令並收集所有結果

---

*上一章：[json - 序列化](../json/)*
*下一章：[re - 正規表達式](../regex/)*
