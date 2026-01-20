---
title: "5.2 返回值設計"
description: "(bool, str) 模式的應用"
weight: 2
---

# 返回值設計

Hook 系統採用 `(bool, str)` 返回值模式，這是一種替代異常處理的設計策略。本章深入探討這個模式的設計理念和最佳實踐。

## (bool, str) 模式

### 基本形式

```python
def validate_something() -> tuple[bool, str]:
    """
    Returns:
        tuple[bool, str]:
            - (True, "成功訊息") - 操作成功
            - (False, "錯誤訊息") - 操作失敗
    """
    if some_condition:
        return True, "驗證通過"
    return False, "驗證失敗：原因說明"
```

### 使用方式

```python
success, message = validate_something()
if success:
    print(f"成功: {message}")
else:
    print(f"失敗: {message}")
    # 決定如何處理錯誤
```

## 實際範例：Git 命令

來自 `.claude/lib/git_utils.py`：

```python
def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, str]:
    """
    執行 git 命令並返回結果

    Args:
        args: git 命令參數列表
        cwd: 執行目錄
        timeout: 超時時間（秒）

    Returns:
        tuple[bool, str]: (是否成功, 輸出或錯誤訊息)
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
```

### 使用這個函式

```python
def get_current_branch() -> Optional[str]:
    """獲取當前分支名稱"""
    success, output = run_git_command(["branch", "--show-current"])
    return output if success and output else None

def get_project_root() -> str:
    """獲取專案根目錄"""
    success, output = run_git_command(["rev-parse", "--show-toplevel"])
    return output if success else os.getcwd()
```

## 為什麼選擇這個模式？

### 優點

1. **明確的錯誤處理**
   ```python
   # 呼叫者必須處理兩種情況
   success, message = validate()
   if not success:
       # 必須處理錯誤
       pass
   ```

2. **錯誤訊息保留**
   ```python
   # 錯誤訊息可以傳遞給使用者
   success, error = run_command()
   if not success:
       logger.error(error)
       return create_error_response(error)
   ```

3. **不中斷執行流程**
   ```python
   # 可以收集所有錯誤
   errors = []
   for file in files:
       success, message = process(file)
       if not success:
           errors.append(message)
   ```

### 與異常的比較

| 特性 | (bool, str) | 異常 |
|------|------------|------|
| 強制處理 | 是（需要解包） | 否（可能被忽略） |
| 控制流程 | 不中斷 | 中斷 |
| 效能 | 較好 | 較差（stack trace） |
| 適合場景 | 預期的錯誤 | 非預期的錯誤 |

## 設計變體

### (bool, T) - 通用型別

```python
from typing import TypeVar, Tuple

T = TypeVar("T")

def parse_json(text: str) -> Tuple[bool, dict]:
    try:
        return True, json.loads(text)
    except json.JSONDecodeError as e:
        return False, {"error": str(e)}
```

### (T | None) - 成功返回值，失敗返回 None

```python
def find_config(name: str) -> Optional[dict]:
    """找不到時返回 None"""
    path = get_config_path(name)
    if not path.exists():
        return None
    return load_config(path)
```

### Result 類別（進階）

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class Result(Generic[T]):
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(success=True, value=value)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        return cls(success=False, error=error)

# 使用
def divide(a: int, b: int) -> Result[float]:
    if b == 0:
        return Result.fail("Division by zero")
    return Result.ok(a / b)

result = divide(10, 2)
if result.success:
    print(result.value)  # 5.0
else:
    print(result.error)
```

## 實際應用模式

### 鏈式操作

```python
def process_pipeline(data: str) -> Tuple[bool, str]:
    # 第一步
    success, result = step_one(data)
    if not success:
        return False, f"Step 1 failed: {result}"

    # 第二步
    success, result = step_two(result)
    if not success:
        return False, f"Step 2 failed: {result}"

    # 第三步
    success, result = step_three(result)
    if not success:
        return False, f"Step 3 failed: {result}"

    return True, result
```

### 收集多個錯誤

```python
def validate_all(items: list[str]) -> Tuple[bool, list[str]]:
    errors = []
    for item in items:
        success, message = validate_item(item)
        if not success:
            errors.append(message)

    if errors:
        return False, errors
    return True, []
```

### 帶上下文的錯誤

```python
def run_with_context(
    command: str
) -> Tuple[bool, str]:
    """執行命令並提供上下文"""
    try:
        result = execute(command)
        return True, result
    except Exception as e:
        context = f"Command: {command}\nError: {e}"
        return False, context
```

## Hook 系統的應用

### Hook 輸入讀取

```python
def read_hook_input() -> dict:
    """
    從 stdin 讀取輸入
    失敗時返回空字典（而非拋出異常）
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
```

### 分支驗證

```python
def validate_branch(branch: str) -> Tuple[bool, str]:
    """驗證分支是否可以編輯"""
    if is_protected_branch(branch):
        return False, f"Cannot edit protected branch: {branch}"
    if not is_allowed_branch(branch):
        return False, f"Branch not in allowed list: {branch}"
    return True, f"Branch {branch} is valid"
```

## 最佳實踐

### 1. 訊息要有意義

```python
# 好：提供具體資訊
return False, f"Config file not found: {path}"

# 不好：模糊的訊息
return False, "Error"
```

### 2. 保持一致性

```python
# 好：整個模組使用相同模式
def func_a() -> Tuple[bool, str]: ...
def func_b() -> Tuple[bool, str]: ...
def func_c() -> Tuple[bool, str]: ...

# 不好：混合使用
def func_a() -> Tuple[bool, str]: ...
def func_b() -> Optional[str]: ...  # 不一致
def func_c(): ...  # 可能拋出異常
```

### 3. 文檔說明返回值

```python
def validate(data: str) -> Tuple[bool, str]:
    """
    驗證資料格式

    Returns:
        tuple[bool, str]:
            - (True, "Validation passed") - 驗證成功
            - (False, error_message) - 驗證失敗，包含原因
    """
    ...
```

## 思考題

1. 什麼情況下應該使用 `(bool, str)` 而不是異常？
2. 如何處理需要返回多種錯誤類型的情況？
3. `(bool, str)` 模式如何與型別檢查工具配合？

## 實作練習

1. 重構一個使用異常的函式，改為 `(bool, str)` 模式
2. 實作一個 `Result` 類別，支援 `map` 和 `flat_map` 操作
3. 寫一個函式，執行多個驗證並收集所有錯誤

---

*上一章：[異常處理策略](../exception/)*
*下一章：[unittest 基礎](../unittest/)*
