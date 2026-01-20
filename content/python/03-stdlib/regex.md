---
title: "3.4 re - 正規表達式"
date: 2026-01-20
description: "文字模式匹配與擷取"
weight: 4
---

# re - 正規表達式

正規表達式（Regular Expression，簡稱 regex 或 re）是一種強大的文字模式匹配工具。在 Hook 系統中，主要用於解析 Markdown 連結和驗證輸入格式。

## 基本用法

### re.search() - 搜尋匹配

```python
import re

text = "Hello, Python 3.11!"

# 搜尋數字
match = re.search(r'\d+\.\d+', text)
if match:
    print(match.group())  # "3.11"
```

### re.match() - 從開頭匹配

```python
import re

text = "Python is great"

# 只從字串開頭匹配
match = re.match(r'Python', text)  # 成功
match = re.match(r'great', text)   # None（不是從開頭開始）
```

### re.findall() - 找出所有匹配

```python
import re

text = "Call 123-456-7890 or 098-765-4321"

# 找出所有電話號碼
phones = re.findall(r'\d{3}-\d{3}-\d{4}', text)
# ['123-456-7890', '098-765-4321']
```

### re.sub() - 替換

```python
import re

text = "Hello   World"

# 將多個空格替換為單個
result = re.sub(r'\s+', ' ', text)
# "Hello World"
```

## 正規表達式語法

### 基本字元

| 模式 | 說明 | 範例 |
|------|------|------|
| `.` | 任意字元（除換行） | `a.c` 匹配 "abc", "a1c" |
| `\d` | 數字 [0-9] | `\d+` 匹配 "123" |
| `\w` | 單字字元 [a-zA-Z0-9_] | `\w+` 匹配 "hello" |
| `\s` | 空白字元 | `\s+` 匹配空格、tab |
| `^` | 字串開頭 | `^Hello` |
| `$` | 字串結尾 | `World$` |

### 數量詞

| 模式 | 說明 | 範例 |
|------|------|------|
| `*` | 0 或多次 | `a*` 匹配 "", "a", "aaa" |
| `+` | 1 或多次 | `a+` 匹配 "a", "aaa" |
| `?` | 0 或 1 次 | `a?` 匹配 "", "a" |
| `{n}` | 恰好 n 次 | `a{3}` 匹配 "aaa" |
| `{n,m}` | n 到 m 次 | `a{2,4}` 匹配 "aa", "aaa", "aaaa" |

### 群組與擷取

```python
import re

text = "[Link Text](https://example.com)"

# 使用群組擷取
match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', text)
if match:
    link_text = match.group(1)  # "Link Text"
    link_url = match.group(2)   # "https://example.com"
```

## 實際範例：Markdown 連結檢查

來自 `.claude/lib/markdown_link_checker.py`：

```python
import re

class MarkdownLinkChecker:
    # Markdown 連結正則表達式
    # 匹配 [text](target) 格式，排除圖片 ![alt](src)
    INLINE_LINK_PATTERN = re.compile(
        r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'
    )

    # 引用式連結定義 [ref]: target
    REFERENCE_DEF_PATTERN = re.compile(
        r'^\s*\[([^\]]+)\]:\s*(.+)$',
        re.MULTILINE
    )

    # 引用式連結使用 [text][ref]
    REFERENCE_USE_PATTERN = re.compile(
        r'\[([^\]]+)\]\[([^\]]+)\]'
    )
```

### 模式解析

`r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'` 解析：

| 部分 | 說明 |
|------|------|
| `(?<!!)` | 負向前瞻，確保前面不是 `!`（排除圖片） |
| `\[` | 匹配字面 `[` |
| `([^\]]+)` | 群組 1：擷取連結文字（一個或多個非 `]` 字元） |
| `\]` | 匹配字面 `]` |
| `\(` | 匹配字面 `(` |
| `([^)]+)` | 群組 2：擷取連結目標（一個或多個非 `)` 字元） |
| `\)` | 匹配字面 `)` |

### 使用範例

```python
def parse_markdown_links(self, content: str) -> list[dict]:
    """解析 Markdown 內容中的所有連結"""
    links = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # 行內連結 [text](target)
        for match in self.INLINE_LINK_PATTERN.finditer(line):
            links.append({
                "text": match.group(1),
                "target": match.group(2),
                "line": line_num
            })

    return links
```

## 編譯正規表達式

對於重複使用的模式，預先編譯可提升效能：

```python
import re

# 編譯模式
pattern = re.compile(r'\d+')

# 重複使用
pattern.search(text1)
pattern.findall(text2)
pattern.sub('X', text3)
```

## 實際應用：Hook 驗證

來自 `.claude/lib/hook_validator.py`：

```python
class HookValidator:
    # 共用模組導入模式
    HOOK_IO_PATTERNS = [
        r"from\s+hook_io\s+import",
        r"from\s+lib\.hook_io\s+import",
    ]

    # 命名規範模式
    VALID_NAME_PATTERNS = [
        r"^[a-z0-9]([a-z0-9\-_]*[a-z0-9])?\.py$",
    ]

    def _has_import(self, content: str, patterns: list[str]) -> bool:
        """檢查是否有符合任一模式的導入"""
        return any(
            re.search(pattern, content)
            for pattern in patterns
        )

    def check_naming_convention(self, hook_path: Path) -> list:
        """檢查命名規範"""
        filename = hook_path.name

        valid_name = any(
            re.match(pattern, filename)
            for pattern in self.VALID_NAME_PATTERNS
        )
        # ...
```

## 常用旗標

### re.IGNORECASE（忽略大小寫）

```python
import re

re.search(r'hello', 'Hello World', re.IGNORECASE)  # 匹配
```

### re.MULTILINE（多行模式）

```python
import re

text = """line 1
line 2
line 3"""

# 每行開頭的 "line"
matches = re.findall(r'^line', text, re.MULTILINE)
# ['line', 'line', 'line']
```

### re.DOTALL（點號匹配換行）

```python
import re

text = "start\nmiddle\nend"

# 無 DOTALL：. 不匹配換行
re.search(r'start.*end', text)  # None

# 有 DOTALL：. 匹配換行
re.search(r'start.*end', text, re.DOTALL)  # 匹配
```

## 外部連結判斷

```python
class MarkdownLinkChecker:
    EXTERNAL_PATTERNS = [
        r'^https?://',
        r'^mailto:',
        r'^tel:',
        r'^ftp://',
    ]

    def _is_external_link(self, target: str) -> bool:
        """檢查是否為外部連結"""
        return any(
            re.match(pattern, target)
            for pattern in self.EXTERNAL_PATTERNS
        )
```

## 最佳實踐

### 1. 使用原始字串

```python
# 好：使用 r'' 避免跳脫問題
pattern = r'\d+\.\d+'

# 不好：需要雙重跳脫
pattern = '\\d+\\.\\d+'
```

### 2. 預編譯重複使用的模式

```python
# 好：編譯後重複使用
pattern = re.compile(r'\d+')
for text in texts:
    pattern.findall(text)

# 不好：每次都重新編譯
for text in texts:
    re.findall(r'\d+', text)
```

### 3. 使用命名群組

```python
# 有命名群組：更易讀
pattern = re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})')
match = pattern.search("2024-01-20")
if match:
    print(match.group('year'))   # "2024"
    print(match.group('month'))  # "01"
```

## 思考題

1. `re.search()` 和 `re.match()` 有什麼區別？
2. 為什麼 Markdown 連結模式使用 `(?<!!)` 負向前瞻？
3. `re.compile()` 的好處是什麼？

## 實作練習

1. 寫一個正規表達式，驗證電子郵件格式
2. 從 Python 原始碼中擷取所有函式定義（`def function_name(`）
3. 實作一個函式，將 Markdown 標題（`# Title`）轉換為 HTML（`<h1>Title</h1>`）

---

*上一章：[subprocess - 執行外部命令](../subprocess/)*
*下一章：[logging - 日誌系統](../logging/)*
