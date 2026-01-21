---
title: "案例：並行 I/O 操作"
date: 2026-01-21
description: "用 asyncio.gather 和 TaskGroup 實現高效的並行 I/O 操作"
weight: 2
---

# 案例：並行 I/O 操作

本案例基於 `.claude/lib/git_utils.py` 的實際程式碼，展示如何用 `asyncio.gather` 和 `TaskGroup` 實現高效的並行 I/O 操作。

## 先備知識

- [1.1 非同步 Subprocess](../async-subprocess/)
- [1.2 協程與 Task 管理](../../coroutines-tasks/)

## 問題背景

### 現有設計

`git_utils.py` 的 `get_worktree_list()` 取得 worktree 列表後，如果要檢查每個 worktree 的狀態，需要逐一呼叫：

```python
from git_utils import run_git_command, get_worktree_list

def check_all_worktrees_sync() -> dict[str, str]:
    """
    同步版本：依序檢查每個 worktree 的狀態

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    worktrees = get_worktree_list()
    results = {}

    for wt in worktrees:
        path = wt["path"]
        # Every call blocks until completion
        success, output = run_git_command(["status", "-s"], cwd=path)
        results[path] = output if success else "error"

    return results

def get_all_branches_sync() -> dict[str, str]:
    """
    同步版本：依序取得每個 worktree 的分支名稱

    Returns:
        dict[str, str]: {路徑: 分支名} 映射
    """
    worktrees = get_worktree_list()
    results = {}

    for wt in worktrees:
        path = wt["path"]
        # Each command waits for the previous one
        success, output = run_git_command(["branch", "--show-current"], cwd=path)
        results[path] = output if success else "unknown"

    return results
```

### 這個設計的優點

- **簡單直覺**：循序執行，容易理解和除錯
- **錯誤處理明確**：每個操作的結果立即可用
- **資源友善**：一次只執行一個進程

### 這個設計的限制

當 worktree 數量增加時：

- **執行時間線性增長**：10 個 worktree，每個 0.2 秒 = 2 秒
- **無法利用 I/O 等待時間**：等待一個命令完成時，CPU 閒置
- **使用者體驗差**：大量 worktree 時響應緩慢

```python
import time

def benchmark_sync(worktrees: list[str]) -> float:
    """測量同步版本的執行時間"""
    start = time.perf_counter()

    for path in worktrees:
        # Simulate I/O wait (actual git command)
        run_git_command(["status", "-s"], cwd=path)

    return time.perf_counter() - start

# 10 worktrees, each taking 0.2s
# Total: 10 * 0.2 = 2.0 seconds
```

## 進階解決方案

### 設計目標

1. **並行執行**多個獨立的 I/O 操作
2. **正確處理**部分失敗的情況
3. **支援取消**和超時機制

### 實作步驟

#### 步驟 1：使用 asyncio.gather

`asyncio.gather` 是並行執行多個協程最直接的方式：

```python
import asyncio
from typing import Optional

async def async_run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: float = 10.0
) -> tuple[bool, str]:
    """
    非同步執行 git 命令（詳見上一章）
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

async def check_all_worktrees_basic(worktrees: list[str]) -> dict[str, str]:
    """
    使用 asyncio.gather 並行檢查所有 worktree

    Args:
        worktrees: worktree 路徑列表

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    async def check_one(path: str) -> tuple[str, str]:
        """Check a single worktree and return (path, status)"""
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path
        )
        return path, output if success else "error"

    # Create tasks for all worktrees
    tasks = [check_one(path) for path in worktrees]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks)

    # Convert list of tuples to dict
    return dict(results)

# Usage example
async def demo_basic():
    worktrees = ["/path/to/repo1", "/path/to/repo2", "/path/to/repo3"]

    # All three checks run in parallel
    # If each takes 0.2s, total time is ~0.2s, not 0.6s
    statuses = await check_all_worktrees_basic(worktrees)

    for path, status in statuses.items():
        print(f"{path}: {'clean' if not status else status}")
```

**重點說明**：

- `asyncio.gather(*tasks)` 同時啟動所有協程
- 等待所有協程完成後，返回結果列表
- 結果順序與輸入任務順序一致

#### 步驟 2：處理錯誤（return_exceptions）

預設情況下，`gather` 在遇到第一個異常時會傳播該異常。使用 `return_exceptions=True` 可以收集所有結果，包括異常：

```python
async def check_all_worktrees_safe(
    worktrees: list[str]
) -> dict[str, str | Exception]:
    """
    安全版本：使用 return_exceptions 處理部分失敗

    即使某些 worktree 檢查失敗，仍然返回其他的結果。

    Args:
        worktrees: worktree 路徑列表

    Returns:
        dict: {路徑: 狀態或例外} 映射
    """
    async def check_one(path: str) -> tuple[str, str]:
        """Check with potential exception"""
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path,
            timeout=5.0  # Shorter timeout
        )

        if not success:
            # Raise exception for failed commands
            raise RuntimeError(f"Git command failed: {output}")

        return path, output

    tasks = [check_one(path) for path in worktrees]

    # return_exceptions=True: exceptions become results, not propagated
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, handling both successes and exceptions
    output = {}
    for path, result in zip(worktrees, results):
        if isinstance(result, Exception):
            output[path] = f"error: {result}"
        else:
            # result is (path, status) tuple
            _, status = result
            output[path] = status if status else "clean"

    return output

async def demo_error_handling():
    """示範錯誤處理"""
    worktrees = [
        "/valid/repo1",      # Works
        "/invalid/path",     # Fails
        "/valid/repo2",      # Works
    ]

    results = await check_all_worktrees_safe(worktrees)

    for path, status in results.items():
        if status.startswith("error:"):
            print(f"[FAILED] {path}: {status}")
        else:
            print(f"[OK] {path}: {status}")

# Output:
# [OK] /valid/repo1: clean
# [FAILED] /invalid/path: error: Git command failed: ...
# [OK] /valid/repo2: M file.txt
```

**`return_exceptions` 行為對比**：

```python
async def compare_exception_handling():
    async def might_fail(n: int) -> int:
        if n == 2:
            raise ValueError(f"Task {n} failed")
        return n * 10

    tasks = [might_fail(i) for i in range(5)]

    # Without return_exceptions (default)
    try:
        results = await asyncio.gather(*tasks)  # Raises ValueError
    except ValueError as e:
        print(f"Caught: {e}")  # Only see first error, others lost

    # With return_exceptions=True
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # results: [0, 10, ValueError('Task 2 failed'), 30, 40]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i}: Failed - {result}")
        else:
            print(f"Task {i}: Success - {result}")
```

#### 步驟 3：使用 TaskGroup（Python 3.11+）

Python 3.11 引入的 `TaskGroup` 提供更好的結構化並行控制：

```python
import asyncio
from typing import Optional

async def check_all_worktrees_taskgroup(
    worktrees: list[str]
) -> dict[str, str]:
    """
    使用 TaskGroup 並行檢查所有 worktree

    TaskGroup 特性：
    - 任一任務失敗時，自動取消其他任務
    - 明確的作用域（context manager）
    - 異常聚合（ExceptionGroup）

    Args:
        worktrees: worktree 路徑列表

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    results: dict[str, str] = {}

    async def check_and_store(path: str) -> None:
        """Check worktree and store result in shared dict"""
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path
        )
        results[path] = output if success else "error"

    async with asyncio.TaskGroup() as tg:
        for path in worktrees:
            tg.create_task(check_and_store(path))

    # All tasks complete when exiting the context
    return results

async def demo_taskgroup():
    """示範 TaskGroup 的基本用法"""
    worktrees = ["/repo1", "/repo2", "/repo3"]

    try:
        results = await check_all_worktrees_taskgroup(worktrees)
        for path, status in results.items():
            print(f"{path}: {status}")
    except* Exception as eg:
        # Python 3.11+ except* syntax for ExceptionGroup
        for exc in eg.exceptions:
            print(f"Task failed: {exc}")
```

**TaskGroup 的錯誤處理模式**：

```python
async def taskgroup_error_demo():
    """示範 TaskGroup 的異常處理"""

    async def task_might_fail(name: str, should_fail: bool) -> str:
        await asyncio.sleep(0.1)
        if should_fail:
            raise ValueError(f"{name} failed!")
        return f"{name} succeeded"

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_might_fail("A", False))
            tg.create_task(task_might_fail("B", True))   # Will fail
            tg.create_task(task_might_fail("C", False))  # Gets cancelled
    except* ValueError as eg:
        print(f"Caught {len(eg.exceptions)} errors:")
        for exc in eg.exceptions:
            print(f"  - {exc}")

# When B fails:
# 1. TaskGroup cancels C (even though it would succeed)
# 2. Waits for all tasks to finish
# 3. Raises ExceptionGroup with the ValueError
```

#### 步驟 4：並行與循序的混合模式

實際應用中，常需要混合並行和循序操作：

```python
async def check_worktrees_batched(
    worktrees: list[str],
    batch_size: int = 5
) -> dict[str, str]:
    """
    分批並行處理：控制同時執行的任務數量

    適用場景：
    - 避免同時開啟過多進程
    - 防止 API rate limiting
    - 控制資源使用

    Args:
        worktrees: worktree 路徑列表
        batch_size: 每批並行數量

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    results: dict[str, str] = {}

    # Process in batches
    for i in range(0, len(worktrees), batch_size):
        batch = worktrees[i:i + batch_size]

        async def check_one(path: str) -> tuple[str, str]:
            success, output = await async_run_git_command(
                ["status", "-s"],
                cwd=path
            )
            return path, output if success else "error"

        # Process batch in parallel
        batch_results = await asyncio.gather(
            *[check_one(path) for path in batch]
        )

        # Collect results
        results.update(dict(batch_results))

    return results

async def check_worktrees_semaphore(
    worktrees: list[str],
    max_concurrent: int = 5
) -> dict[str, str]:
    """
    使用 Semaphore 限制並行數量

    比分批更靈活：任務完成後立即啟動新任務，
    而不是等整批完成。

    Args:
        worktrees: worktree 路徑列表
        max_concurrent: 最大同時執行數

    Returns:
        dict[str, str]: {路徑: 狀態} 映射
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def check_with_limit(path: str) -> tuple[str, str]:
        """Check worktree with concurrency limit"""
        async with semaphore:
            # At most max_concurrent tasks run this block
            success, output = await async_run_git_command(
                ["status", "-s"],
                cwd=path
            )
            return path, output if success else "error"

    # Launch all tasks (they'll wait at semaphore if needed)
    tasks = [check_with_limit(path) for path in worktrees]
    results = await asyncio.gather(*tasks)

    return dict(results)

async def pipeline_example():
    """
    示範流水線模式：前一步的輸出是後一步的輸入
    """
    # Step 1: Get worktree list (single operation)
    worktrees = await async_get_worktree_list()
    paths = [wt["path"] for wt in worktrees]

    # Step 2: Check status in parallel
    statuses = await check_all_worktrees_basic(paths)

    # Step 3: For dirty repos, get detailed diff (parallel)
    dirty_paths = [p for p, s in statuses.items() if s]

    async def get_diff(path: str) -> tuple[str, str]:
        success, diff = await async_run_git_command(["diff"], cwd=path)
        return path, diff if success else ""

    diffs = dict(await asyncio.gather(
        *[get_diff(p) for p in dirty_paths]
    ))

    return {"statuses": statuses, "diffs": diffs}
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
並行 I/O 操作工具 - 完整範例

展示如何用 asyncio.gather 和 TaskGroup 實現高效的並行 Git 操作。
"""

import asyncio
import time
from typing import Optional

# ===== Core async function =====

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

# ===== Parallel strategies =====

async def parallel_with_gather(
    worktrees: list[str],
    return_exceptions: bool = False
) -> dict[str, str]:
    """
    Strategy 1: asyncio.gather

    Args:
        worktrees: worktree 路徑列表
        return_exceptions: 是否將異常作為結果返回

    Returns:
        dict[str, str]: 檢查結果
    """
    async def check_one(path: str) -> tuple[str, str]:
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path
        )
        return path, output if success else "error"

    tasks = [check_one(path) for path in worktrees]
    results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    output = {}
    for path, result in zip(worktrees, results):
        if isinstance(result, Exception):
            output[path] = f"exception: {result}"
        else:
            _, status = result
            output[path] = status if status else "clean"

    return output

async def parallel_with_taskgroup(worktrees: list[str]) -> dict[str, str]:
    """
    Strategy 2: TaskGroup (Python 3.11+)

    One task fails -> all cancelled
    """
    results: dict[str, str] = {}

    async def check_and_store(path: str) -> None:
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path
        )
        results[path] = output if success else "error"

    async with asyncio.TaskGroup() as tg:
        for path in worktrees:
            tg.create_task(check_and_store(path))

    return results

async def parallel_with_semaphore(
    worktrees: list[str],
    max_concurrent: int = 5
) -> dict[str, str]:
    """
    Strategy 3: Semaphore for rate limiting
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def check_with_limit(path: str) -> tuple[str, str]:
        async with semaphore:
            success, output = await async_run_git_command(
                ["status", "-s"],
                cwd=path
            )
            return path, output if success else "error"

    tasks = [check_with_limit(path) for path in worktrees]
    results = await asyncio.gather(*tasks)

    return dict(results)

# ===== Practical helpers =====

async def get_worktree_status_report() -> dict:
    """
    生成完整的 worktree 狀態報告

    Returns:
        dict: 包含狀態、分支、變更的完整報告
    """
    # Step 1: Get worktree list
    worktrees = await async_get_worktree_list()
    paths = [wt["path"] for wt in worktrees]

    if not paths:
        return {"error": "No worktrees found"}

    # Step 2: Parallel operations
    async def get_status(path: str) -> tuple[str, str]:
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path
        )
        return path, output if success else "error"

    async def get_branch(path: str) -> tuple[str, str]:
        success, output = await async_run_git_command(
            ["branch", "--show-current"],
            cwd=path
        )
        return path, output if success else "unknown"

    async def get_last_commit(path: str) -> tuple[str, str]:
        success, output = await async_run_git_command(
            ["log", "-1", "--format=%s"],
            cwd=path
        )
        return path, output if success else "unknown"

    # Execute all queries in parallel
    status_task = asyncio.gather(*[get_status(p) for p in paths])
    branch_task = asyncio.gather(*[get_branch(p) for p in paths])
    commit_task = asyncio.gather(*[get_last_commit(p) for p in paths])

    statuses, branches, commits = await asyncio.gather(
        status_task, branch_task, commit_task
    )

    # Combine results
    report = {}
    for wt in worktrees:
        path = wt["path"]
        status_dict = dict(statuses)
        branch_dict = dict(branches)
        commit_dict = dict(commits)

        report[path] = {
            "branch": branch_dict.get(path, "unknown"),
            "status": status_dict.get(path, "error"),
            "is_clean": not status_dict.get(path, "error"),
            "last_commit": commit_dict.get(path, "unknown"),
        }

    return report

# ===== Benchmark =====

async def benchmark_strategies(worktrees: list[str]) -> dict[str, float]:
    """
    比較不同策略的執行時間
    """
    results = {}

    # Strategy 1: Sequential (baseline)
    start = time.perf_counter()
    for path in worktrees:
        await async_run_git_command(["status", "-s"], cwd=path)
    results["sequential"] = time.perf_counter() - start

    # Strategy 2: gather
    start = time.perf_counter()
    await parallel_with_gather(worktrees)
    results["gather"] = time.perf_counter() - start

    # Strategy 3: TaskGroup
    start = time.perf_counter()
    await parallel_with_taskgroup(worktrees)
    results["taskgroup"] = time.perf_counter() - start

    # Strategy 4: Semaphore
    start = time.perf_counter()
    await parallel_with_semaphore(worktrees, max_concurrent=3)
    results["semaphore(3)"] = time.perf_counter() - start

    return results

# ===== Demo =====

async def demo():
    """示範並行 I/O 操作"""
    print("=== 並行 I/O 操作示範 ===\n")

    # Get worktrees
    print("1. 獲取 worktree 列表:")
    worktrees = await async_get_worktree_list()
    paths = [wt["path"] for wt in worktrees]

    for wt in worktrees:
        branch = wt.get("branch", "detached")
        print(f"   - {branch}: {wt['path']}")
    print()

    if len(paths) >= 1:
        # Benchmark
        print("2. 效能比較:")
        times = await benchmark_strategies(paths)
        for strategy, elapsed in times.items():
            print(f"   {strategy}: {elapsed:.3f}s")

        speedup = times["sequential"] / times["gather"]
        print(f"   加速比: {speedup:.1f}x")
        print()

        # Full report
        print("3. 完整狀態報告:")
        report = await get_worktree_status_report()
        for path, info in report.items():
            status = "clean" if info["is_clean"] else "dirty"
            print(f"   [{info['branch']}] {path}")
            print(f"       狀態: {status}")
            print(f"       最新提交: {info['last_commit'][:50]}...")

if __name__ == "__main__":
    asyncio.run(demo())
```

### 使用範例

#### 基本使用

```python
import asyncio

async def main():
    # Get all worktree paths
    worktrees = await async_get_worktree_list()
    paths = [wt["path"] for wt in worktrees]

    # Check all in parallel
    statuses = await parallel_with_gather(paths)

    for path, status in statuses.items():
        print(f"{path}: {status or 'clean'}")

asyncio.run(main())
```

#### 處理大量 worktree

```python
async def check_many_worktrees(paths: list[str]):
    """處理大量 worktree 時使用 semaphore 限制並行數"""
    # Limit to 10 concurrent git processes
    results = await parallel_with_semaphore(paths, max_concurrent=10)

    clean_count = sum(1 for s in results.values() if not s or s == "clean")
    dirty_count = len(results) - clean_count

    print(f"Clean: {clean_count}, Dirty: {dirty_count}")
    return results
```

#### 與錯誤重試結合

```python
async def check_with_retry(
    path: str,
    max_retries: int = 3
) -> tuple[str, str]:
    """帶重試的檢查"""
    for attempt in range(max_retries):
        success, output = await async_run_git_command(
            ["status", "-s"],
            cwd=path,
            timeout=5.0
        )

        if success:
            return path, output

        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))  # Backoff

    return path, "error: max retries exceeded"

async def check_all_with_retry(paths: list[str]) -> dict[str, str]:
    """所有檢查都帶重試機制"""
    tasks = [check_with_retry(p) for p in paths]
    results = await asyncio.gather(*tasks)
    return dict(results)
```

## 設計權衡

| 面向 | asyncio.gather | TaskGroup | Semaphore |
|------|----------------|-----------|-----------|
| Python 版本 | 3.4+ | 3.11+ | 3.4+ |
| 錯誤處理 | `return_exceptions` | 自動取消其他任務 | 同 gather |
| 取消行為 | 需手動處理 | 結構化取消 | 需手動處理 |
| 程式碼可讀性 | 中等 | 較高 | 中等 |
| 並行控制 | 無內建限制 | 無內建限制 | 可限制數量 |
| 適用場景 | 一般並行 | 全有或全無 | 需要限流 |

### 選擇指南

```text
需要並行執行多個獨立 I/O 操作？
├── 是 → 是否需要「一個失敗全部取消」？
│        ├── 是 → 使用 TaskGroup
│        └── 否 → 是否需要限制並行數量？
│                 ├── 是 → 使用 Semaphore + gather
│                 └── 否 → 使用 gather（可選 return_exceptions）
└── 否 → 直接使用 await
```

## 什麼時候該用這個技術？

✅ **適合使用**：

- 多個獨立的 I/O 操作（HTTP 請求、檔案讀取、資料庫查詢）
- 需要等待所有操作完成
- 操作之間沒有依賴關係
- 單一操作耗時較長（> 10ms）

❌ **不建議使用**：

- CPU 密集計算（應用 multiprocessing）
- 操作之間有依賴關係（應用循序執行或流水線）
- 單一操作極快（overhead 可能大於收益）
- 外部服務有嚴格的 rate limit（需要更精細的控制）

## 練習

### 基礎練習

#### 練習 1：用 gather 同時讀取多個設定檔

```python
async def read_configs(paths: list[str]) -> dict[str, str]:
    """
    並行讀取多個設定檔

    提示：使用 aiofiles 或 asyncio.to_thread
    """
    # Your implementation here
    pass
```

#### 練習 2：實作 worktree 狀態快取

```python
class WorktreeCache:
    """
    快取 worktree 狀態，避免頻繁查詢

    提示：
    - 使用 dict 儲存狀態
    - 設定過期時間
    - 過期時重新並行查詢
    """
    def __init__(self, ttl_seconds: float = 30.0):
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = ttl_seconds

    async def get_status(self, path: str) -> str:
        # Your implementation here
        pass

    async def get_all_statuses(self, paths: list[str]) -> dict[str, str]:
        # Your implementation here
        pass
```

### 進階練習

#### 練習 3：實作帶有重試邏輯的並行下載器

```python
async def parallel_download(
    urls: list[str],
    max_concurrent: int = 5,
    max_retries: int = 3
) -> dict[str, bytes | Exception]:
    """
    並行下載多個 URL，支援重試

    提示：
    - 使用 Semaphore 限制並行數
    - 實作指數退避（exponential backoff）
    - 使用 aiohttp 進行非同步 HTTP 請求
    """
    # Your implementation here
    pass
```

### 挑戰題

#### 練習 4：實作 semaphore 限制並行數量的 TaskGroup

```python
class BoundedTaskGroup:
    """
    限制最大並行數的 TaskGroup

    使用方式：
        async with BoundedTaskGroup(max_concurrent=5) as tg:
            for item in items:
                tg.create_task(process(item))

    提示：
    - 結合 Semaphore 和 TaskGroup
    - 保持 TaskGroup 的錯誤處理語義
    """
    def __init__(self, max_concurrent: int):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tg: asyncio.TaskGroup | None = None

    async def __aenter__(self):
        # Your implementation here
        pass

    async def __aexit__(self, *args):
        # Your implementation here
        pass

    def create_task(self, coro):
        # Your implementation here
        pass
```

#### 練習 5：實作監控儀表板

建立一個即時監控多個 Git repo 狀態的工具：

```python
async def monitor_repos(
    repos: list[str],
    interval: float = 5.0,
    on_change: callable = None
):
    """
    每隔 interval 秒並行檢查所有 repo
    狀態變化時呼叫 on_change callback

    提示：
    - 使用 asyncio.sleep 控制間隔
    - 比較前後狀態找出變化
    - 支援 Ctrl+C 優雅退出
    """
    # Your implementation here
    pass
```

## 延伸閱讀

- [asyncio.gather 官方文件](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- [TaskGroup 官方文件](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup)
- [Semaphore 官方文件](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore)
- [PEP 654 - Exception Groups](https://peps.python.org/pep-0654/) - TaskGroup 的異常處理基礎

---

*上一章：[非同步 Subprocess](../async-subprocess/)*
*下一章：[同步/非同步橋接](../sync-async-bridge/)*
