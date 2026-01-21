---
title: "案例：非同步 subprocess"
date: 2026-01-21
description: "用 asyncio.create_subprocess_exec 實現非阻塞的外部命令執行"
weight: 1
---

# 案例：非同步 subprocess

本案例基於 `.claude/lib/git_utils.py` 的實際程式碼，展示如何用 asyncio 實現非同步的外部命令執行。

## 先備知識

- [1.1 基礎概念與事件迴圈](../../fundamentals/)
- [1.4 實戰：與同步程式碼整合](../../real-world/)

## 問題背景

### 現有設計

`git_utils.py` 使用同步的 `subprocess.run`：

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
        cwd: 執行目錄
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

def get_current_branch() -> Optional[str]:
    """獲取當前分支名稱"""
    success, output = run_git_command(["branch", "--show-current"])
    return output if success and output else None

def get_worktree_list() -> list[dict]:
    """獲取所有 worktree 列表"""
    success, output = run_git_command(["worktree", "list", "--porcelain"])
    if not success:
        return []
    # ... 解析邏輯
```

### 這個設計的優點

1. **簡單直覺**：同步呼叫，容易理解
2. **錯誤處理完善**：處理超時、檔案不存在等情況
3. **API 清晰**：返回 `(bool, str)` 元組

### 這個設計的限制

**問題：無法並行執行多個 Git 命令**

```python
def check_all_worktrees(worktrees: list[str]) -> dict[str, str]:
    """檢查所有 worktree 的狀態"""
    results = {}
    for worktree in worktrees:
        # 每次呼叫都會阻塞等待
        success, status = run_git_command(["status", "-s"], cwd=worktree)
        results[worktree] = status if success else "error"
    return results

# 如果有 10 個 worktree，每個花 0.5 秒
# 總共需要 5 秒！
```

**問題：阻塞事件迴圈**

```python
async def handle_request():
    # 這會阻塞事件迴圈！
    branch = get_current_branch()
    # 其他協程無法執行
    return {"branch": branch}
```

## 進階解決方案：非同步 subprocess

### 設計目標

1. **非阻塞執行**：不阻塞事件迴圈
2. **並行能力**：可以同時執行多個命令
3. **相容性**：保持與同步版本相似的 API

### 實作步驟

#### 步驟 1：建立非同步命令執行器

```python
import asyncio
from typing import Optional

async def async_run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: float = 10.0
) -> tuple[bool, str]:
    """
    非同步執行 git 命令

    Args:
        args: git 命令參數列表（不含 'git'）
        cwd: 執行目錄
        timeout: 命令超時時間（秒）

    Returns:
        tuple[bool, str]: (是否成功, 輸出內容或錯誤訊息)

    Example:
        success, output = await async_run_git_command(["status"])
    """
    try:
        # 建立非同步子進程
        process = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 等待完成（帶超時）
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return False, f"Command timed out after {timeout}s"

        # 處理結果
        if process.returncode == 0:
            return True, stdout.decode().strip()
        else:
            return False, stderr.decode().strip()

    except FileNotFoundError:
        return False, "git command not found"
    except Exception as e:
        return False, str(e)
```

#### 步驟 2：建立便利函式

```python
async def async_get_current_branch() -> Optional[str]:
    """非同步獲取當前分支名稱"""
    success, output = await async_run_git_command(["branch", "--show-current"])
    return output if success and output else None

async def async_get_project_root() -> str:
    """非同步獲取專案根目錄"""
    import os
    success, output = await async_run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else os.getcwd()

async def async_get_worktree_list() -> list[dict]:
    """非同步獲取 worktree 列表"""
    success, output = await async_run_git_command(
        ["worktree", "list", "--porcelain"]
    )
    if not success:
        return []

    worktrees = []
    current_worktree: dict = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current_worktree:
                worktrees.append(current_worktree)
            current_worktree = {"path": line[9:]}  # len("worktree ") = 9
        elif line.startswith("branch "):
            branch_ref = line[7:]  # len("branch ") = 7
            if branch_ref.startswith("refs/heads/"):
                branch_ref = branch_ref[11:]  # len("refs/heads/") = 11
            current_worktree["branch"] = branch_ref
        elif line == "detached":
            current_worktree["detached"] = True

    if current_worktree:
        worktrees.append(current_worktree)

    return worktrees
```

#### 步驟 3：實現並行執行

```python
async def check_all_worktrees(worktrees: list[str]) -> dict[str, str]:
    """
    並行檢查所有 worktree 的狀態

    Args:
        worktrees: worktree 路徑列表

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    async def check_one(worktree: str) -> tuple[str, str]:
        """檢查單個 worktree"""
        success, status = await async_run_git_command(
            ["status", "-s"],
            cwd=worktree
        )
        return worktree, status if success else "error"

    # 並行執行所有檢查
    tasks = [check_one(wt) for wt in worktrees]
    results = await asyncio.gather(*tasks)

    return dict(results)

async def get_all_branches(worktrees: list[str]) -> dict[str, str]:
    """
    並行獲取所有 worktree 的當前分支

    Args:
        worktrees: worktree 路徑列表

    Returns:
        dict[str, str]: {路徑: 分支名} 映射
    """
    async def get_branch(worktree: str) -> tuple[str, str]:
        success, branch = await async_run_git_command(
            ["branch", "--show-current"],
            cwd=worktree
        )
        return worktree, branch if success else "unknown"

    tasks = [get_branch(wt) for wt in worktrees]
    results = await asyncio.gather(*tasks)

    return dict(results)
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
非同步 Git 操作工具 - 完整範例

展示如何用 asyncio 實現非阻塞的 Git 命令執行。
"""

import asyncio
import os
from typing import Optional

# ===== 核心功能 =====

async def async_run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: float = 10.0
) -> tuple[bool, str]:
    """
    非同步執行 git 命令

    Args:
        args: git 命令參數列表
        cwd: 執行目錄
        timeout: 超時時間（秒）

    Returns:
        (是否成功, 輸出或錯誤訊息)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return False, f"Command timed out after {timeout}s"

        if process.returncode == 0:
            return True, stdout.decode().strip()
        else:
            return False, stderr.decode().strip()

    except FileNotFoundError:
        return False, "git command not found"
    except Exception as e:
        return False, str(e)

# ===== 便利函式 =====

async def async_get_current_branch() -> Optional[str]:
    """獲取當前分支"""
    success, output = await async_run_git_command(["branch", "--show-current"])
    return output if success and output else None

async def async_get_project_root() -> str:
    """獲取專案根目錄"""
    success, output = await async_run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else os.getcwd()

async def async_get_worktree_list() -> list[dict]:
    """獲取 worktree 列表"""
    success, output = await async_run_git_command(
        ["worktree", "list", "--porcelain"]
    )
    if not success:
        return []

    worktrees = []
    current_worktree: dict = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current_worktree:
                worktrees.append(current_worktree)
            current_worktree = {"path": line[9:]}
        elif line.startswith("branch "):
            branch_ref = line[7:]
            if branch_ref.startswith("refs/heads/"):
                branch_ref = branch_ref[11:]
            current_worktree["branch"] = branch_ref
        elif line == "detached":
            current_worktree["detached"] = True

    if current_worktree:
        worktrees.append(current_worktree)

    return worktrees

# ===== 並行操作 =====

async def check_all_worktrees(worktrees: list[str]) -> dict[str, str]:
    """並行檢查所有 worktree 狀態"""
    async def check_one(path: str) -> tuple[str, str]:
        success, status = await async_run_git_command(["status", "-s"], cwd=path)
        return path, status if success else "error"

    tasks = [check_one(wt) for wt in worktrees]
    results = await asyncio.gather(*tasks)
    return dict(results)

async def get_all_branches(worktrees: list[str]) -> dict[str, str]:
    """並行獲取所有 worktree 的分支"""
    async def get_branch(path: str) -> tuple[str, str]:
        success, branch = await async_run_git_command(
            ["branch", "--show-current"],
            cwd=path
        )
        return path, branch if success else "unknown"

    tasks = [get_branch(wt) for wt in worktrees]
    results = await asyncio.gather(*tasks)
    return dict(results)

async def batch_git_commands(
    commands: list[tuple[list[str], Optional[str]]]
) -> list[tuple[bool, str]]:
    """
    批次執行多個 Git 命令

    Args:
        commands: [(args, cwd), ...] 命令列表

    Returns:
        [(success, output), ...] 結果列表
    """
    tasks = [
        async_run_git_command(args, cwd=cwd)
        for args, cwd in commands
    ]
    return await asyncio.gather(*tasks)

# ===== 同步/非同步橋接 =====

def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: float = 10.0
) -> tuple[bool, str]:
    """
    同步版本（相容舊 API）

    在已有事件迴圈的環境中，這會建立新的迴圈執行。
    """
    return asyncio.run(async_run_git_command(args, cwd, timeout))

def get_current_branch() -> Optional[str]:
    """同步版本：獲取當前分支"""
    return asyncio.run(async_get_current_branch())

# ===== 測試 =====

async def demo():
    """示範非同步 Git 操作"""
    print("=== 非同步 Git 操作示範 ===\n")

    # 單一命令
    print("1. 獲取當前分支:")
    branch = await async_get_current_branch()
    print(f"   分支: {branch}\n")

    # 獲取專案根目錄
    print("2. 獲取專案根目錄:")
    root = await async_get_project_root()
    print(f"   根目錄: {root}\n")

    # 獲取 worktree 列表
    print("3. 獲取 worktree 列表:")
    worktrees = await async_get_worktree_list()
    for wt in worktrees:
        branch = wt.get("branch", "detached")
        print(f"   - {branch}: {wt['path']}")
    print()

    # 如果有多個 worktree，示範並行操作
    if len(worktrees) > 1:
        print("4. 並行檢查所有 worktree 狀態:")
        paths = [wt["path"] for wt in worktrees]
        statuses = await check_all_worktrees(paths)
        for path, status in statuses.items():
            print(f"   - {path}:")
            if status:
                for line in status.split("\n"):
                    print(f"       {line}")
            else:
                print("       (clean)")
        print()

    # 批次命令示範
    print("5. 批次執行多個命令:")
    commands = [
        (["config", "user.name"], None),
        (["config", "user.email"], None),
        (["rev-parse", "--short", "HEAD"], None),
    ]
    results = await batch_git_commands(commands)
    labels = ["使用者名稱", "使用者信箱", "當前 commit"]
    for label, (success, output) in zip(labels, results):
        print(f"   {label}: {output if success else '(未設定)'}")

if __name__ == "__main__":
    asyncio.run(demo())
```

### 使用範例

#### 基本使用

```python
import asyncio

async def main():
    # 非同步獲取分支
    branch = await async_get_current_branch()
    print(f"當前分支: {branch}")

    # 非同步獲取 worktree
    worktrees = await async_get_worktree_list()
    print(f"Worktree 數量: {len(worktrees)}")

asyncio.run(main())
```

#### 並行操作

```python
async def check_multiple_repos(repos: list[str]):
    """同時檢查多個 repo 的狀態"""
    tasks = [
        async_run_git_command(["status", "-s"], cwd=repo)
        for repo in repos
    ]

    # 並行執行，等待全部完成
    results = await asyncio.gather(*tasks)

    for repo, (success, output) in zip(repos, results):
        status = "clean" if not output else "dirty"
        print(f"{repo}: {status}")

# 10 個 repo，如果每個花 0.5 秒
# 並行執行只需要約 0.5 秒！
```

#### 與 FastAPI 整合

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/git/branch")
async def get_branch():
    """非同步端點：獲取當前分支"""
    branch = await async_get_current_branch()
    return {"branch": branch}

@app.get("/git/worktrees")
async def get_worktrees():
    """非同步端點：獲取 worktree 列表"""
    worktrees = await async_get_worktree_list()
    return {"worktrees": worktrees}
```

## 效能比較

```python
import time
import asyncio

def sync_check_repos(repos: list[str]) -> float:
    """同步版本：依序檢查"""
    start = time.perf_counter()
    for repo in repos:
        run_git_command(["status", "-s"], cwd=repo)
    return time.perf_counter() - start

async def async_check_repos(repos: list[str]) -> float:
    """非同步版本：並行檢查"""
    start = time.perf_counter()
    tasks = [
        async_run_git_command(["status", "-s"], cwd=repo)
        for repo in repos
    ]
    await asyncio.gather(*tasks)
    return time.perf_counter() - start

# 假設每個 git status 花 0.2 秒
repos = [f"/path/to/repo{i}" for i in range(10)]

sync_time = sync_check_repos(repos)      # ~2.0 秒
async_time = asyncio.run(async_check_repos(repos))  # ~0.2 秒

print(f"同步: {sync_time:.2f}s")
print(f"非同步: {async_time:.2f}s")
print(f"加速: {sync_time / async_time:.1f}x")
```

## 設計權衡

| 面向 | 同步 subprocess | 非同步 subprocess |
|------|-----------------|-------------------|
| 簡單性 | 簡單直覺 | 需要理解 async/await |
| 效能 | 依序執行 | 可並行執行 |
| 相容性 | 到處可用 | 需要事件迴圈 |
| 錯誤處理 | 直覺 | 需要處理非同步異常 |
| 測試 | 簡單 | 需要 pytest-asyncio |
| 記憶體 | 低 | 略高（維護多個進程） |

## 什麼時候該用非同步 subprocess？

✅ **適合使用**：

- 需要同時執行多個外部命令
- 在非同步框架（FastAPI、aiohttp）中執行
- 命令執行時間較長，需要同時做其他事

❌ **不建議使用**：

- 只需要執行單一命令
- 在同步程式碼中（需要額外的橋接）
- 命令執行非常快（< 10ms）

## 進階：使用 TaskGroup（Python 3.11+）

```python
async def check_repos_with_taskgroup(repos: list[str]) -> dict[str, str]:
    """使用 TaskGroup 管理並行任務"""
    results: dict[str, str] = {}

    async with asyncio.TaskGroup() as tg:
        async def check_and_store(repo: str):
            success, output = await async_run_git_command(
                ["status", "-s"],
                cwd=repo
            )
            results[repo] = output if success else "error"

        for repo in repos:
            tg.create_task(check_and_store(repo))

    return results
```

TaskGroup 的優點：
- 更好的異常處理（一個失敗，全部取消）
- 結構化並行（明確的範圍）

## 練習

### 基礎練習

1. 實作 `async_is_clean_repo(path)` 函式，檢查 repo 是否乾淨
2. 實作 `async_get_commit_count(branch)` 函式，獲取分支的 commit 數量

### 進階練習

3. 實作一個 `GitRepo` 類別，封裝非同步 Git 操作
4. 為非同步版本加入重試機制（失敗時自動重試）

### 挑戰題

5. 實作一個監控工具：每 5 秒並行檢查多個 repo 的狀態，有變化時通知

## 延伸閱讀

- [asyncio.create_subprocess_exec](https://docs.python.org/3/library/asyncio-subprocess.html)
- [asyncio.TaskGroup](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup)
- [aiofiles](https://github.com/Tinche/aiofiles) - 非同步檔案操作

---

*上一章：[案例研究索引](../)*
*下一章：[案例：並行 I/O 操作](../parallel-io/)*
