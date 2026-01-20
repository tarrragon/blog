---
title: "1.1 Python 哲學與設計理念"
description: "理解 Python 的核心設計原則"
weight: 1
---

# Python 哲學與設計理念

在學習任何程式語言之前，了解其設計理念能幫助你寫出更符合語言風格的程式碼。Python 有一套廣為人知的設計原則，被稱為「Python 之禪」。

## Python 之禪

在 Python 直譯器中輸入 `import this`，你會看到 Python 的設計原則：

```python
>>> import this
The Zen of Python, by Tim Peters

Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
...
```

## 實踐中的 Python 哲學

### 顯式優於隱式（Explicit is better than implicit）

在 Hook 系統中，我們明確導入需要的函式，而不是使用 `import *`：

```python
# 好的做法：明確導入
from lib.hook_io import read_hook_input, write_hook_output
from lib.git_utils import get_current_branch

# 不好的做法：隱式導入所有
from lib.hook_io import *  # 不知道導入了什麼
```

### 可讀性很重要（Readability counts）

函式和變數命名要清楚表達用途：

```python
# 好的命名：一看就懂
def get_current_branch() -> Optional[str]:
    """獲取當前分支名稱"""
    success, output = run_git_command(["branch", "--show-current"])
    return output if success and output else None

# 不好的命名：需要猜測
def gcb():
    s, o = rgc(["branch", "--show-current"])
    return o if s and o else None
```

### 簡單優於複雜（Simple is better than complex）

Hook 系統使用簡單的 `(bool, str)` 返回值模式：

```python
def run_git_command(args: list[str]) -> tuple[bool, str]:
    """
    執行 git 命令並返回結果

    Returns:
        tuple[bool, str]: (是否成功, 輸出內容或錯誤訊息)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)
```

這個設計比拋出異常更直觀，呼叫者可以用簡單的 if 來處理：

```python
success, output = run_git_command(["status"])
if success:
    print(output)
else:
    print(f"Error: {output}")
```

### 扁平優於巢狀（Flat is better than nested）

避免過深的巢狀結構：

```python
# 不好：過深的巢狀
def check_file(path):
    if path:
        if path.exists():
            if path.suffix == '.py':
                if path.stat().st_size > 0:
                    return True
    return False

# 好：使用 early return
def check_file(path):
    if not path:
        return False
    if not path.exists():
        return False
    if path.suffix != '.py':
        return False
    if path.stat().st_size <= 0:
        return False
    return True
```

## 「Pythonic」的含義

當我們說程式碼是「Pythonic」時，意思是它遵循 Python 的慣例和風格。以下是一些例子：

### 使用 List Comprehension

```python
# Pythonic
squares = [x**2 for x in range(10)]

# 非 Pythonic
squares = []
for x in range(10):
    squares.append(x**2)
```

### 使用上下文管理器

```python
# Pythonic
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 非 Pythonic
f = open(file_path, "r", encoding="utf-8")
content = f.read()
f.close()  # 容易忘記關閉
```

### 使用 enumerate 而非 range(len())

```python
# Pythonic
for i, item in enumerate(items):
    print(f"{i}: {item}")

# 非 Pythonic
for i in range(len(items)):
    print(f"{i}: {items[i]}")
```

## 實際範例：Hook 系統的設計體現

來自 `.claude/lib/hook_io.py` 的設計展示了這些原則：

```python
def write_hook_output(
    output: dict,
    ensure_ascii: bool = False,
    indent: int = 2
) -> None:
    """
    輸出 Hook 結果到 stdout

    Args:
        output: 要輸出的字典
        ensure_ascii: 是否確保 ASCII 編碼（預設 False 以支援中文）
        indent: JSON 縮排空格數
    """
    print(json.dumps(output, ensure_ascii=ensure_ascii, indent=indent))
```

這個函式體現了：
- **顯式參數**：每個參數都有預設值和明確的型別提示
- **文件字串**：清楚說明函式用途和參數意義
- **單一職責**：函式只做一件事 - 輸出 JSON

## 思考題

1. 為什麼 `ensure_ascii=False` 是預設值？
2. Hook 系統為什麼選擇返回 `tuple[bool, str]` 而不是拋出異常？
3. 閱讀 `.claude/lib/git_utils.py`，找出三個體現 Python 哲學的設計選擇。

## 延伸閱讀

- [PEP 20 - The Zen of Python](https://peps.python.org/pep-0020/)
- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)

---

*下一章：[模組與套件組織](../modules/)*
