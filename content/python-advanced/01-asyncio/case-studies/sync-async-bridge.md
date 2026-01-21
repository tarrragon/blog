---
title: "案例：同步/非同步橋接"
date: 2026-01-21
description: "用 run_in_executor 和 asyncio.run 在同步與非同步程式碼之間建立橋樑"
weight: 3
---

# 案例：同步/非同步橋接

本案例基於 `.claude/lib` 整體架構，展示如何用 `run_in_executor` 和 `asyncio.run` 在同步與非同步程式碼之間建立橋樑。

## 先備知識

- [1.1 非同步 Subprocess](../async-subprocess/)
- [1.4 實戰：與同步程式碼整合](../../real-world/)

## 問題背景

### 現有設計

`.claude/lib` 是一個同步設計的 Python 工具庫，包含多個模組：

```python
# .claude/lib/__init__.py
"""
Claude Hooks 共用程式庫

模組結構:
- git_utils: Git 操作工具（分支、worktree、專案根目錄）
- config_loader: 配置檔案載入
- hook_io: Hook 輸入輸出處理
- hook_validator: Hook 合規性驗證
- markdown_link_checker: Markdown 連結檢查
"""

from .git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
)

from .config_loader import (
    load_config,
    load_agents_config,
)

from .hook_io import (
    read_hook_input,
    write_hook_output,
)
```

這些函式都是同步的：

```python
# git_utils.py - 同步的 subprocess 呼叫
def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, str]:
    """Execute git command and return result"""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr.strip()

# config_loader.py - 同步的檔案 I/O
def load_config(config_name: str) -> dict:
    """Load configuration file"""
    config_dir = get_config_dir()
    yaml_path = config_dir / f"{config_name}.yaml"

    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# hook_validator.py - 同步的檔案驗證
def validate_hook(hook_path: str) -> ValidationResult:
    """Validate a single hook file"""
    with open(hook_path, "r", encoding="utf-8") as f:
        content = f.read()
    # ... validation logic
```

### 這個設計的優點

1. **簡單直覺**：不需要了解 asyncio，任何 Python 開發者都能使用
2. **向後相容**：可以在任何 Python 環境中執行
3. **測試容易**：同步程式碼的測試更直觀
4. **依賴少**：不需要額外的非同步依賴庫

### 這個設計的限制

在非同步環境（如 FastAPI、aiohttp）中使用時：

**問題 1：阻塞事件迴圈**

```python
from fastapi import FastAPI
from lib.git_utils import get_current_branch, get_worktree_list

app = FastAPI()

@app.get("/git/status")
async def get_git_status():
    # BAD: These synchronous calls block the event loop!
    branch = get_current_branch()      # Blocks ~50ms
    worktrees = get_worktree_list()    # Blocks ~50ms

    # During these 100ms, NO other requests can be processed!
    return {"branch": branch, "worktrees": worktrees}
```

**問題 2：無法並行執行**

```python
def validate_all_hooks(hooks_dir: str) -> list[ValidationResult]:
    """Validate all hooks - sequential execution"""
    results = []
    for hook_file in Path(hooks_dir).glob("*.py"):
        # Each validation runs one after another
        result = validate_hook(str(hook_file))  # ~10ms each
        results.append(result)
    return results

# 10 hooks = 100ms total
# With parallelization, could be ~10ms!
```

**問題 3：無法有效利用等待時間**

```python
def check_project_health() -> dict:
    """Check multiple aspects of project health"""
    # All I/O operations execute sequentially
    git_status = run_git_command(["status", "-s"])      # Wait...
    config = load_config("agents")                       # Wait...
    links = check_markdown_links("docs/README.md")       # Wait...

    # Total time = sum of all operations
    return {
        "git": git_status,
        "config": config,
        "links": links
    }
```

## 進階解決方案

### 設計目標

1. **在非同步程式碼中安全地呼叫同步函式**（不阻塞事件迴圈）
2. **在同步程式碼中使用非同步函式**（保持向後相容）
3. **避免巢狀事件迴圈問題**
4. **保持原有 API 不變**

### 實作步驟

#### 步驟 1：run_in_executor - 同步到非同步

`run_in_executor` 將同步函式放到執行緒池中執行，讓事件迴圈可以繼續處理其他任務。

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, Callable, Any

T = TypeVar('T')

# Create a shared thread pool for I/O operations
_io_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="async_io")

async def run_sync_in_executor(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Run a synchronous function in a thread pool executor.

    This prevents blocking the event loop when calling
    synchronous I/O operations from async code.

    Args:
        func: The synchronous function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function call

    Example:
        # Instead of blocking:
        result = sync_function(arg1, arg2)

        # Use executor:
        result = await run_sync_in_executor(sync_function, arg1, arg2)
    """
    loop = asyncio.get_running_loop()

    # functools.partial handles kwargs
    if kwargs:
        import functools
        func = functools.partial(func, **kwargs)

    return await loop.run_in_executor(_io_executor, func, *args)
```

**使用範例：包裝現有同步函式**

```python
from lib.git_utils import get_current_branch, get_worktree_list, run_git_command
from lib.config_loader import load_config
from lib.hook_validator import validate_hook

# Async wrappers for existing sync functions
async def async_get_current_branch() -> Optional[str]:
    """Async wrapper for get_current_branch"""
    return await run_sync_in_executor(get_current_branch)

async def async_get_worktree_list() -> list[dict]:
    """Async wrapper for get_worktree_list"""
    return await run_sync_in_executor(get_worktree_list)

async def async_load_config(config_name: str) -> dict:
    """Async wrapper for load_config"""
    return await run_sync_in_executor(load_config, config_name)

async def async_validate_hook(hook_path: str) -> ValidationResult:
    """Async wrapper for validate_hook"""
    return await run_sync_in_executor(validate_hook, hook_path)
```

#### 步驟 2：asyncio.run - 非同步到同步

當你有非同步程式碼，但需要從同步環境呼叫時，使用 `asyncio.run`。

```python
import asyncio
from typing import TypeVar, Coroutine

T = TypeVar('T')

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async function from synchronous code.

    Creates a new event loop if none exists.
    Safe to call from synchronous entry points.

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine

    Example:
        # From a synchronous script:
        result = run_async(async_function(arg1, arg2))

    Warning:
        Cannot be called when an event loop is already running!
        Use nest_asyncio or redesign your code structure.
    """
    return asyncio.run(coro)

# Synchronous API that uses async implementation internally
def get_all_worktree_branches() -> dict[str, str]:
    """
    Get branches for all worktrees.

    Uses async implementation internally for parallelization,
    but provides a synchronous API for compatibility.
    """
    async def _async_impl():
        worktrees = await async_get_worktree_list()
        tasks = []
        for wt in worktrees:
            path = wt["path"]
            tasks.append(_get_branch_for_path(path))
        results = await asyncio.gather(*tasks)
        return dict(zip([wt["path"] for wt in worktrees], results))

    return run_async(_async_impl())

async def _get_branch_for_path(path: str) -> str:
    """Get current branch for a specific path"""
    success, output = await run_sync_in_executor(
        run_git_command,
        ["branch", "--show-current"],
        cwd=path
    )
    return output if success else "unknown"
```

#### 步驟 3：處理已存在的事件迴圈

當你在已有事件迴圈的環境中（如 Jupyter Notebook、某些 Web 框架），直接呼叫 `asyncio.run` 會失敗：

```python
# This will raise RuntimeError in Jupyter or when loop is running
asyncio.run(some_coroutine())
# RuntimeError: asyncio.run() cannot be called from a running event loop
```

**解決方案 A：使用 nest_asyncio（快速修復）**

```python
# pip install nest-asyncio
import nest_asyncio

def run_async_safe(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async code safely, even from a running event loop.

    Uses nest_asyncio to allow nested event loops.
    This is a pragmatic solution for environments like Jupyter.

    Note:
        nest_asyncio patches the event loop globally.
        Use with caution in production code.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to use asyncio.run
        return asyncio.run(coro)

    # Running loop exists - need to nest
    nest_asyncio.apply()
    return loop.run_until_complete(coro)
```

**解決方案 B：偵測執行環境（推薦）**

```python
import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar('T')

def is_event_loop_running() -> bool:
    """Check if there's a running event loop"""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False

def run_async_adaptive(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async code with automatic environment detection.

    - If no event loop: uses asyncio.run()
    - If loop running: uses run_in_executor to run in a new thread

    This is safer than nest_asyncio for production use.
    """
    if is_event_loop_running():
        # We're in an async context - run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        # Safe to run directly
        return asyncio.run(coro)
```

**解決方案 C：提供雙重 API（最佳實踐）**

```python
class GitUtils:
    """
    Git utilities with both sync and async APIs.

    Usage:
        # Synchronous (traditional)
        utils = GitUtils()
        branch = utils.get_current_branch()

        # Asynchronous
        branch = await utils.async_get_current_branch()
    """

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd

    # ===== Synchronous API (original) =====

    def get_current_branch(self) -> Optional[str]:
        """Get current branch (sync)"""
        success, output = run_git_command(
            ["branch", "--show-current"],
            cwd=self.cwd
        )
        return output if success else None

    def get_worktree_list(self) -> list[dict]:
        """Get worktree list (sync)"""
        # ... original implementation
        pass

    # ===== Asynchronous API =====

    async def async_get_current_branch(self) -> Optional[str]:
        """Get current branch (async)"""
        return await run_sync_in_executor(self.get_current_branch)

    async def async_get_worktree_list(self) -> list[dict]:
        """Get worktree list (async)"""
        return await run_sync_in_executor(self.get_worktree_list)
```

#### 步驟 4：建立統一的 API

整合以上模式，建立一個統一的適配器：

```python
"""
Sync/Async Bridge Adapter

Provides unified access to .claude/lib modules from both
synchronous and asynchronous contexts.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, Callable, Any, Optional, Coroutine

T = TypeVar('T')

# Shared executor for I/O operations
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="lib_async")

class AsyncAdapter:
    """
    Adapter for converting sync functions to async.

    Provides both decorator and wrapper patterns for flexibility.

    Example:
        adapter = AsyncAdapter()

        # As decorator
        @adapter.make_async
        def sync_function(x):
            return x * 2

        result = await sync_function(5)

        # As wrapper
        result = await adapter.run(other_sync_function, arg1, arg2)
    """

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None):
        self.executor = executor or _executor

    async def run(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """Run a sync function asynchronously"""
        loop = asyncio.get_running_loop()

        if kwargs:
            func = functools.partial(func, **kwargs)

        return await loop.run_in_executor(self.executor, func, *args)

    def make_async(self, func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
        """
        Decorator to create async version of sync function.

        Example:
            @adapter.make_async
            def slow_io_operation(path: str) -> str:
                with open(path) as f:
                    return f.read()

            # Now can be awaited
            content = await slow_io_operation("file.txt")
        """
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.run(func, *args, **kwargs)
        return wrapper

class SyncAdapter:
    """
    Adapter for calling async functions from sync code.

    Example:
        adapter = SyncAdapter()

        # Run async function synchronously
        result = adapter.run(async_function(arg1, arg2))
    """

    @staticmethod
    def run(coro: Coroutine[Any, Any, T]) -> T:
        """
        Run a coroutine from synchronous code.

        Automatically handles the case when an event loop
        is already running.
        """
        try:
            asyncio.get_running_loop()
            # Loop is running - use thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop - safe to use asyncio.run
            return asyncio.run(coro)

    @staticmethod
    def make_sync(
        async_func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., T]:
        """
        Decorator to create sync version of async function.

        Example:
            @SyncAdapter.make_sync
            async def async_fetch(url: str) -> str:
                async with aiohttp.get(url) as resp:
                    return await resp.text()

            # Now can be called synchronously
            content = async_fetch("https://example.com")
        """
        @functools.wraps(async_func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            coro = async_func(*args, **kwargs)
            return SyncAdapter.run(coro)
        return wrapper
```

### 完整程式碼

```python
#!/usr/bin/env python3
"""
Sync/Async Bridge for .claude/lib

This module provides async wrappers for the synchronous
.claude/lib modules, enabling their use in async contexts
like FastAPI without blocking the event loop.

Usage:
    # In async code (FastAPI, aiohttp, etc.)
    from lib_async import (
        async_get_current_branch,
        async_load_config,
        async_validate_hooks,
    )

    branch = await async_get_current_branch()

    # In sync code that needs parallelization
    from lib_async import parallel_validate_hooks

    results = parallel_validate_hooks(hooks_dir)
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar, Callable, Any, Optional, Coroutine

# Import original sync modules
from lib.git_utils import (
    run_git_command,
    get_current_branch,
    get_project_root,
    get_worktree_list,
    is_protected_branch,
    is_allowed_branch,
)
from lib.config_loader import (
    load_config,
    load_agents_config,
    load_quality_rules,
)
from lib.hook_io import (
    read_hook_input,
    write_hook_output,
)
from lib.hook_validator import (
    validate_hook,
    validate_all_hooks,
    ValidationResult,
)
from lib.markdown_link_checker import (
    check_markdown_links,
    check_directory as check_markdown_directory,
    LinkCheckResult,
)

T = TypeVar('T')

# ===== Shared Resources =====

# Thread pool for I/O-bound sync operations
_io_executor = ThreadPoolExecutor(
    max_workers=10,
    thread_name_prefix="lib_async_io"
)

# ===== Core Utilities =====

async def run_in_executor(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Run a synchronous function in the thread pool executor.

    Args:
        func: Synchronous function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    loop = asyncio.get_running_loop()

    if kwargs:
        func = functools.partial(func, **kwargs)

    return await loop.run_in_executor(_io_executor, func, *args)

def make_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to create async version of a sync function.

    Example:
        @make_async
        def slow_operation(x):
            time.sleep(1)
            return x * 2

        result = await slow_operation(5)
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_in_executor(func, *args, **kwargs)
    return wrapper

# ===== Async Git Utils =====

async def async_run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, str]:
    """Async version of run_git_command"""
    return await run_in_executor(run_git_command, args, cwd=cwd, timeout=timeout)

async def async_get_current_branch() -> Optional[str]:
    """Async version of get_current_branch"""
    return await run_in_executor(get_current_branch)

async def async_get_project_root() -> str:
    """Async version of get_project_root"""
    return await run_in_executor(get_project_root)

async def async_get_worktree_list() -> list[dict]:
    """Async version of get_worktree_list"""
    return await run_in_executor(get_worktree_list)

# ===== Async Config Loader =====

async def async_load_config(config_name: str) -> dict:
    """Async version of load_config"""
    return await run_in_executor(load_config, config_name)

async def async_load_agents_config() -> dict:
    """Async version of load_agents_config"""
    return await run_in_executor(load_agents_config)

async def async_load_quality_rules() -> dict:
    """Async version of load_quality_rules"""
    return await run_in_executor(load_quality_rules)

# ===== Async Hook Validator =====

async def async_validate_hook(hook_path: str) -> ValidationResult:
    """Async version of validate_hook"""
    return await run_in_executor(validate_hook, hook_path)

async def async_validate_all_hooks(
    hooks_dir: Optional[str] = None
) -> list[ValidationResult]:
    """
    Validate all hooks in parallel.

    Unlike the sync version that validates sequentially,
    this version validates all hooks concurrently.
    """
    if hooks_dir is None:
        hooks_dir = str(Path(await async_get_project_root()) / ".claude" / "hooks")

    hooks_path = Path(hooks_dir)
    if not hooks_path.is_dir():
        return []

    # Collect all hook files
    hook_files = [
        str(f) for f in sorted(hooks_path.glob("*.py"))
        if not f.name.startswith("_")
    ]

    # Validate all in parallel
    tasks = [async_validate_hook(hook) for hook in hook_files]
    return await asyncio.gather(*tasks)

# ===== Async Markdown Link Checker =====

async def async_check_markdown_links(file_path: str) -> LinkCheckResult:
    """Async version of check_markdown_links"""
    return await run_in_executor(check_markdown_links, file_path)

async def async_check_markdown_directory(
    dir_path: str,
    recursive: bool = True
) -> list[LinkCheckResult]:
    """
    Check all markdown files in directory in parallel.
    """
    # Get file list synchronously (fast operation)
    dir_path_obj = Path(dir_path)
    if not dir_path_obj.is_dir():
        return []

    if recursive:
        md_files = list(dir_path_obj.rglob("*.md"))
    else:
        md_files = list(dir_path_obj.glob("*.md"))

    # Check all files in parallel
    tasks = [async_check_markdown_links(str(f)) for f in md_files]
    return await asyncio.gather(*tasks)

# ===== Parallel Operations =====

async def async_check_all_worktrees() -> dict[str, dict]:
    """
    Check status of all worktrees in parallel.

    Returns:
        dict: {path: {"branch": str, "status": str, "is_clean": bool}}
    """
    worktrees = await async_get_worktree_list()

    async def check_one(wt: dict) -> tuple[str, dict]:
        path = wt["path"]

        # Run git status and branch in parallel for each worktree
        status_task = async_run_git_command(["status", "-s"], cwd=path)
        branch_task = async_run_git_command(["branch", "--show-current"], cwd=path)

        (status_ok, status), (branch_ok, branch) = await asyncio.gather(
            status_task, branch_task
        )

        return path, {
            "branch": branch if branch_ok else wt.get("branch", "unknown"),
            "status": status if status_ok else "error",
            "is_clean": status_ok and not status,
        }

    tasks = [check_one(wt) for wt in worktrees]
    results = await asyncio.gather(*tasks)

    return dict(results)

async def async_project_health_check() -> dict:
    """
    Comprehensive project health check with parallel execution.

    Checks:
    - Git status
    - Configuration validity
    - Hook compliance
    - Documentation links

    Returns:
        dict: Health check results
    """
    # Run all checks in parallel
    git_task = async_get_current_branch()
    worktrees_task = async_check_all_worktrees()
    config_task = async_load_agents_config()
    hooks_task = async_validate_all_hooks()

    branch, worktrees, config, hook_results = await asyncio.gather(
        git_task, worktrees_task, config_task, hooks_task,
        return_exceptions=True  # Don't fail if one check fails
    )

    return {
        "git": {
            "branch": branch if not isinstance(branch, Exception) else str(branch),
            "worktrees": worktrees if not isinstance(worktrees, Exception) else {},
        },
        "config": {
            "loaded": not isinstance(config, Exception),
            "agents_count": len(config.get("known_agents", [])) if not isinstance(config, Exception) else 0,
        },
        "hooks": {
            "total": len(hook_results) if not isinstance(hook_results, Exception) else 0,
            "compliant": sum(1 for r in hook_results if r.is_compliant) if not isinstance(hook_results, Exception) else 0,
        }
    }

# ===== Sync Wrappers for Async Functions =====

def parallel_validate_hooks(hooks_dir: Optional[str] = None) -> list[ValidationResult]:
    """
    Synchronous API that uses async parallelization internally.

    Use this when you want parallelization but are in sync context.
    """
    return asyncio.run(async_validate_all_hooks(hooks_dir))

def parallel_check_worktrees() -> dict[str, dict]:
    """
    Synchronous API for parallel worktree checking.
    """
    return asyncio.run(async_check_all_worktrees())

def project_health_check() -> dict:
    """
    Synchronous API for comprehensive health check.
    """
    return asyncio.run(async_project_health_check())

# ===== Demo =====

async def demo():
    """Demonstrate the sync/async bridge capabilities"""
    import time

    print("=" * 60)
    print("Sync/Async Bridge Demo")
    print("=" * 60)

    # 1. Basic async wrapper usage
    print("\n1. Basic async wrapper:")
    branch = await async_get_current_branch()
    print(f"   Current branch: {branch}")

    # 2. Parallel execution comparison
    print("\n2. Parallel vs Sequential comparison:")

    # Sequential (simulated)
    start = time.perf_counter()
    worktrees = await async_get_worktree_list()
    seq_time = 0
    for wt in worktrees:
        _ = await async_run_git_command(["status", "-s"], cwd=wt["path"])
        seq_time += time.perf_counter() - start
        start = time.perf_counter()
    print(f"   Sequential check: {seq_time:.3f}s")

    # Parallel
    start = time.perf_counter()
    results = await async_check_all_worktrees()
    par_time = time.perf_counter() - start
    print(f"   Parallel check: {par_time:.3f}s")
    print(f"   Speedup: {seq_time/par_time:.1f}x")

    # 3. Project health check
    print("\n3. Project health check (parallel):")
    start = time.perf_counter()
    health = await async_project_health_check()
    elapsed = time.perf_counter() - start

    print(f"   Branch: {health['git']['branch']}")
    print(f"   Worktrees: {len(health['git']['worktrees'])}")
    print(f"   Hooks compliant: {health['hooks']['compliant']}/{health['hooks']['total']}")
    print(f"   Time: {elapsed:.3f}s")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(demo())
```

### 使用範例

#### 在 FastAPI 中使用同步函式

```python
from fastapi import FastAPI, HTTPException
from lib_async import (
    async_get_current_branch,
    async_get_worktree_list,
    async_check_all_worktrees,
    async_validate_all_hooks,
    async_project_health_check,
)

app = FastAPI()

@app.get("/git/branch")
async def get_branch():
    """
    Get current git branch.

    Uses async wrapper to prevent blocking the event loop.
    """
    branch = await async_get_current_branch()
    if branch is None:
        raise HTTPException(status_code=500, detail="Not a git repository")
    return {"branch": branch}

@app.get("/git/worktrees")
async def get_worktrees():
    """
    Get all worktrees with their status.

    Checks all worktrees in parallel for fast response.
    """
    worktrees = await async_check_all_worktrees()
    return {"worktrees": worktrees}

@app.get("/health")
async def health_check():
    """
    Comprehensive project health check.

    Runs multiple checks in parallel:
    - Git status
    - Configuration
    - Hook compliance
    """
    health = await async_project_health_check()
    return health

@app.get("/hooks/validate")
async def validate_hooks():
    """
    Validate all hooks in parallel.

    Much faster than sequential validation for many hooks.
    """
    results = await async_validate_all_hooks()

    return {
        "total": len(results),
        "compliant": sum(1 for r in results if r.is_compliant),
        "issues": [
            {
                "hook": r.hook_path,
                "issues": [
                    {"level": i.level, "message": i.message}
                    for i in r.issues
                ]
            }
            for r in results
            if not r.is_compliant
        ]
    }
```

#### 在同步腳本中使用非同步函式

```python
#!/usr/bin/env python3
"""
Synchronous script that leverages async parallelization internally.
"""

from lib_async import (
    parallel_validate_hooks,
    parallel_check_worktrees,
    project_health_check,
)

def main():
    print("Project Health Report")
    print("=" * 50)

    # These functions use asyncio internally for parallelization
    # but provide a synchronous API

    # 1. Check all worktrees in parallel
    print("\n1. Worktree Status:")
    worktrees = parallel_check_worktrees()
    for path, info in worktrees.items():
        status = "clean" if info["is_clean"] else "dirty"
        print(f"   [{info['branch']}] {path}: {status}")

    # 2. Validate all hooks in parallel
    print("\n2. Hook Validation:")
    results = parallel_validate_hooks()
    compliant = sum(1 for r in results if r.is_compliant)
    print(f"   Compliant: {compliant}/{len(results)}")

    for result in results:
        if not result.is_compliant:
            print(f"   - {result.hook_path}:")
            for issue in result.issues:
                print(f"     [{issue.level}] {issue.message}")

    # 3. Comprehensive health check
    print("\n3. Overall Health:")
    health = project_health_check()
    print(f"   Git branch: {health['git']['branch']}")
    print(f"   Config loaded: {health['config']['loaded']}")
    print(f"   Hooks OK: {health['hooks']['compliant']}/{health['hooks']['total']}")

if __name__ == "__main__":
    main()
```

#### Python 3.9+ 使用 asyncio.to_thread

Python 3.9 引入了 `asyncio.to_thread`，提供更簡潔的語法：

```python
import asyncio
from lib.git_utils import get_current_branch, run_git_command
from lib.config_loader import load_config

# Python 3.9+ simplified syntax
async def async_get_current_branch_39() -> Optional[str]:
    """Using asyncio.to_thread (Python 3.9+)"""
    return await asyncio.to_thread(get_current_branch)

async def async_load_config_39(config_name: str) -> dict:
    """Using asyncio.to_thread (Python 3.9+)"""
    return await asyncio.to_thread(load_config, config_name)

async def async_run_git_command_39(
    args: list[str],
    cwd: Optional[str] = None
) -> tuple[bool, str]:
    """Using asyncio.to_thread with keyword arguments"""
    # to_thread supports kwargs directly in Python 3.9+
    return await asyncio.to_thread(run_git_command, args, cwd)

# Comparison: run_in_executor vs to_thread
async def comparison_demo():
    """
    asyncio.to_thread vs run_in_executor

    to_thread advantages:
    - Simpler syntax
    - Better default executor management
    - Direct kwargs support

    run_in_executor advantages:
    - Works on Python 3.7+
    - Can use custom executors
    - More control over thread pool
    """
    # run_in_executor (Python 3.7+)
    loop = asyncio.get_running_loop()
    result1 = await loop.run_in_executor(None, get_current_branch)

    # to_thread (Python 3.9+)
    result2 = await asyncio.to_thread(get_current_branch)

    assert result1 == result2
```

## 設計權衡

| 面向 | run_in_executor | asyncio.run | asyncio.to_thread |
|------|-----------------|-------------|-------------------|
| **方向** | 同步 -> 非同步 | 非同步 -> 同步 | 同步 -> 非同步 |
| **執行緒** | 使用執行緒池 | 建立新事件迴圈 | 使用預設執行緒池 |
| **適用場景** | 非同步環境呼叫同步 I/O | 同步入口點執行非同步 | 非同步環境呼叫同步 I/O |
| **限制** | 需要事件迴圈存在 | 不能巢狀呼叫 | 需要 Python 3.9+ |
| **效能** | 高（可重用執行緒） | 中（建立新迴圈開銷） | 高（優化的執行緒池） |
| **複雜度** | 中 | 低 | 低 |

### ThreadPoolExecutor vs ProcessPoolExecutor

| 面向 | ThreadPoolExecutor | ProcessPoolExecutor |
|------|-------------------|---------------------|
| **適用場景** | I/O 密集操作 | CPU 密集操作 |
| **記憶體** | 共享記憶體 | 獨立記憶體空間 |
| **GIL** | 受 GIL 限制 | 繞過 GIL |
| **啟動成本** | 低 | 高（進程建立） |
| **資料傳遞** | 直接傳遞 | 需要序列化 |

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# I/O-bound: use ThreadPoolExecutor
io_executor = ThreadPoolExecutor(max_workers=10)

# CPU-bound: use ProcessPoolExecutor
cpu_executor = ProcessPoolExecutor(max_workers=4)

async def io_bound_task():
    """File I/O, network calls, subprocess"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(io_executor, sync_io_function)

async def cpu_bound_task():
    """Heavy computation"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(cpu_executor, sync_cpu_function)
```

## 什麼時候該用這個技術？

### 適合使用

- **漸進式遷移到 asyncio**：有大量同步程式碼，需要逐步遷移
- **在 FastAPI 中使用同步第三方庫**：如 `requests`、`boto3`、資料庫驅動
- **提供同步/非同步雙 API**：讓使用者選擇適合的模式
- **並行化現有同步操作**：如批次檔案處理、多 API 呼叫
- **整合傳統程式碼**：舊系統的同步函式需要在新非同步系統中使用

### 不建議使用

- **全新專案**：直接用原生 asyncio 設計
- **CPU 密集操作**：應用 `multiprocessing` 或 `ProcessPoolExecutor`
- **簡單的單一操作**：不需要並行的情況
- **效能極度敏感**：執行緒池有微小開銷
- **已有原生非同步替代方案**：如用 `aiohttp` 替代 `requests`

## 練習

### 基礎練習

1. **用 run_in_executor 包裝 requests.get**

```python
import requests
import asyncio

# TODO: Implement this function
async def async_fetch(url: str) -> str:
    """
    Fetch URL content asynchronously using requests library.

    Hint: Use run_in_executor to wrap requests.get
    """
    pass

# Test your implementation
async def test():
    content = await async_fetch("https://httpbin.org/get")
    print(content[:200])

asyncio.run(test())
```

<details>
<summary>參考解答</summary>

```python
import requests
import asyncio

async def async_fetch(url: str) -> str:
    """Fetch URL content asynchronously using requests"""
    loop = asyncio.get_running_loop()

    def fetch():
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text

    return await loop.run_in_executor(None, fetch)

# Or using to_thread (Python 3.9+)
async def async_fetch_39(url: str) -> str:
    def fetch():
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text

    return await asyncio.to_thread(fetch)
```
</details>

### 進階練習

2. **建立支援同步/非同步雙模式的 API 客戶端**

```python
# TODO: Implement a dual-mode API client
class WeatherClient:
    """
    Weather API client supporting both sync and async modes.

    Usage:
        client = WeatherClient(api_key="xxx")

        # Sync mode
        weather = client.get_weather("Tokyo")

        # Async mode
        weather = await client.async_get_weather("Tokyo")
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.weatherapi.com/v1"

    def get_weather(self, city: str) -> dict:
        """Synchronous weather fetch"""
        # TODO: Implement
        pass

    async def async_get_weather(self, city: str) -> dict:
        """Asynchronous weather fetch"""
        # TODO: Implement
        pass

    async def async_get_multiple(self, cities: list[str]) -> dict[str, dict]:
        """Fetch weather for multiple cities in parallel"""
        # TODO: Implement
        pass
```

<details>
<summary>參考解答</summary>

```python
import requests
import asyncio
from typing import Optional

class WeatherClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.weatherapi.com/v1"

    def get_weather(self, city: str) -> dict:
        """Synchronous weather fetch"""
        url = f"{self.base_url}/current.json"
        response = requests.get(
            url,
            params={"key": self.api_key, "q": city},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    async def async_get_weather(self, city: str) -> dict:
        """Asynchronous weather fetch using run_in_executor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_weather, city)

    async def async_get_multiple(self, cities: list[str]) -> dict[str, dict]:
        """Fetch weather for multiple cities in parallel"""
        tasks = [self.async_get_weather(city) for city in cities]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            city: result if not isinstance(result, Exception) else {"error": str(result)}
            for city, result in zip(cities, results)
        }
```
</details>

### 挑戰題

3. **實作自動偵測執行環境的適配器**

```python
# TODO: Implement an adaptive function caller
class AdaptiveCaller:
    """
    Automatically detects the execution context and calls
    functions appropriately.

    - In async context: awaits coroutines, wraps sync functions
    - In sync context: runs async functions, calls sync directly

    Usage:
        caller = AdaptiveCaller()

        # Works in both sync and async contexts!
        result = caller.call(some_function, arg1, arg2)
    """

    def call(self, func, *args, **kwargs):
        """
        Call a function adaptively based on context.

        - If func is async and we're in sync: run with asyncio.run
        - If func is sync and we're in async: use run_in_executor
        - Otherwise: call directly
        """
        # TODO: Implement
        pass
```

<details>
<summary>參考解答</summary>

```python
import asyncio
import inspect
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor

class AdaptiveCaller:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=10)

    def _is_async_context(self) -> bool:
        """Check if we're in an async context"""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function adaptively based on context"""
        is_async_func = asyncio.iscoroutinefunction(func)
        in_async_context = self._is_async_context()

        if is_async_func:
            if in_async_context:
                # Return coroutine to be awaited
                return func(*args, **kwargs)
            else:
                # Run async function in new event loop
                return asyncio.run(func(*args, **kwargs))
        else:
            if in_async_context:
                # Wrap sync function for async context
                return self._wrap_sync(func, *args, **kwargs)
            else:
                # Call sync function directly
                return func(*args, **kwargs)

    async def _wrap_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Wrap sync function for async execution"""
        import functools
        loop = asyncio.get_running_loop()

        if kwargs:
            func = functools.partial(func, **kwargs)
            return await loop.run_in_executor(self._executor, func, *args)

        return await loop.run_in_executor(self._executor, func, *args)

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Explicitly async version of call"""
        is_async_func = asyncio.iscoroutinefunction(func)

        if is_async_func:
            return await func(*args, **kwargs)
        else:
            return await self._wrap_sync(func, *args, **kwargs)

# Usage example
caller = AdaptiveCaller()

def sync_func(x):
    return x * 2

async def async_func(x):
    await asyncio.sleep(0.1)
    return x * 3

# In sync context
result1 = caller.call(sync_func, 5)      # Direct call
result2 = caller.call(async_func, 5)     # Uses asyncio.run

# In async context
async def demo():
    result3 = await caller.call_async(sync_func, 5)   # Uses executor
    result4 = await caller.call_async(async_func, 5)  # Direct await
```
</details>

## 延伸閱讀

- [run_in_executor 官方文件](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor)
- [asyncio.run 官方文件](https://docs.python.org/3/library/asyncio-runner.html#asyncio.run)
- [asyncio.to_thread 官方文件](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
- [concurrent.futures 官方文件](https://docs.python.org/3/library/concurrent.futures.html)

---

*上一章：[並行 I/O 操作](../parallel-io/)*
*返回：[模組一：非同步程式設計](../../)*
