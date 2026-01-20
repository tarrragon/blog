---
title: "5.3 unittest 基礎"
date: 2026-01-20
description: "撰寫第一個單元測試"
weight: 3
---

# unittest 基礎

`unittest` 是 Python 內建的測試框架，提供了測試組織、斷言和測試執行等功能。Hook 系統的測試都使用 `unittest` 撰寫。

## 基本結構

### 最簡單的測試

```python
import unittest

class TestCalculator(unittest.TestCase):

    def test_add(self):
        result = 1 + 1
        self.assertEqual(result, 2)

    def test_subtract(self):
        result = 5 - 3
        self.assertEqual(result, 2)

if __name__ == "__main__":
    unittest.main()
```

執行測試：

```bash
$ python -m unittest test_calculator.py
..
----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK
```

## 測試類別結構

```python
import unittest

class TestMyModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """在所有測試前執行一次"""
        cls.shared_resource = create_expensive_resource()

    @classmethod
    def tearDownClass(cls):
        """在所有測試後執行一次"""
        cls.shared_resource.cleanup()

    def setUp(self):
        """在每個測試前執行"""
        self.test_data = {"key": "value"}

    def tearDown(self):
        """在每個測試後執行"""
        self.test_data = None

    def test_something(self):
        """測試方法必須以 test_ 開頭"""
        self.assertTrue(True)
```

## 常用斷言方法

| 方法 | 檢查 |
|------|------|
| `assertEqual(a, b)` | a == b |
| `assertNotEqual(a, b)` | a != b |
| `assertTrue(x)` | x is True |
| `assertFalse(x)` | x is False |
| `assertIs(a, b)` | a is b |
| `assertIsNone(x)` | x is None |
| `assertIn(a, b)` | a in b |
| `assertIsInstance(a, b)` | isinstance(a, b) |
| `assertRaises(Error)` | 拋出指定異常 |

## 實際範例：測試 Hook IO

來自 `.claude/lib/tests/test_hook_io.py`：

```python
import json
import sys
import unittest
from io import StringIO
from unittest.mock import patch

# 導入被測試的模組
sys.path.insert(0, str(Path(__file__).parent.parent))
from hook_io import (
    read_hook_input,
    write_hook_output,
    create_pretooluse_output,
    create_posttooluse_output,
)


class TestReadHookInput(unittest.TestCase):
    """測試 read_hook_input 函式"""

    def test_valid_json_input(self):
        """測試有效的 JSON 輸入"""
        test_data = {"tool_name": "Write", "file_path": "/test.txt"}
        json_input = json.dumps(test_data)

        with patch("sys.stdin", StringIO(json_input)):
            result = read_hook_input()

        self.assertEqual(result, test_data)

    def test_invalid_json_returns_empty_dict(self):
        """測試無效的 JSON 應返回空字典"""
        with patch("sys.stdin", StringIO("not valid json")):
            result = read_hook_input()

        self.assertEqual(result, {})

    def test_empty_input_returns_empty_dict(self):
        """測試空輸入應返回空字典"""
        with patch("sys.stdin", StringIO("")):
            result = read_hook_input()

        self.assertEqual(result, {})


class TestWriteHookOutput(unittest.TestCase):
    """測試 write_hook_output 函式"""

    def test_output_json_format(self):
        """測試輸出為有效的 JSON 格式"""
        test_data = {"decision": "allow", "reason": "OK"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            write_hook_output(test_data)
            output = mock_stdout.getvalue()

        parsed = json.loads(output)
        self.assertEqual(parsed["decision"], "allow")

    def test_chinese_characters_preserved(self):
        """測試中文字元被保留"""
        test_data = {"message": "你好"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            write_hook_output(test_data, ensure_ascii=False)
            output = mock_stdout.getvalue()

        self.assertIn("你好", output)


class TestCreatePretoolueOutput(unittest.TestCase):
    """測試 create_pretooluse_output 函式"""

    def test_basic_output_structure(self):
        """測試基本輸出結構"""
        result = create_pretooluse_output(
            decision="allow",
            reason="Test reason"
        )

        self.assertIn("hookSpecificOutput", result)
        self.assertEqual(
            result["hookSpecificOutput"]["permissionDecision"],
            "allow"
        )

    def test_with_user_prompt(self):
        """測試包含 userPrompt 的輸出"""
        result = create_pretooluse_output(
            decision="ask",
            reason="Need confirmation",
            user_prompt="Continue?"
        )

        self.assertEqual(
            result["hookSpecificOutput"]["userPrompt"],
            "Continue?"
        )


if __name__ == "__main__":
    unittest.main()
```

## 測試異常

### assertRaises

```python
def test_raises_value_error(self):
    """測試函式是否拋出 ValueError"""
    with self.assertRaises(ValueError):
        int("not a number")

def test_raises_with_message(self):
    """測試異常訊息"""
    with self.assertRaises(ValueError) as context:
        raise ValueError("invalid input")

    self.assertIn("invalid", str(context.exception))
```

## 測試檔案操作

### 使用臨時檔案

```python
import tempfile
import unittest

class TestFileOperations(unittest.TestCase):

    def test_read_file(self):
        """測試檔案讀取"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False
        ) as f:
            f.write("test content")
            temp_path = f.name

        try:
            result = read_file(temp_path)
            self.assertEqual(result, "test content")
        finally:
            os.unlink(temp_path)
```

### 使用臨時目錄

```python
import tempfile
import unittest

class TestDirectoryOperations(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_create_file(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        create_file(file_path, "content")
        self.assertTrue(os.path.exists(file_path))
```

## 執行測試

### 執行單一測試檔案

```bash
python -m unittest tests/test_hook_io.py
```

### 執行單一測試類別

```bash
python -m unittest tests.test_hook_io.TestReadHookInput
```

### 執行單一測試方法

```bash
python -m unittest tests.test_hook_io.TestReadHookInput.test_valid_json_input
```

### 執行所有測試

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 詳細輸出

```bash
python -m unittest -v tests/test_hook_io.py
```

## 測試組織

### 目錄結構

```
.claude/lib/
├── __init__.py
├── git_utils.py
├── hook_io.py
├── hook_logging.py
└── tests/
    ├── __init__.py
    ├── test_git_utils.py
    ├── test_hook_io.py
    └── test_hook_logging.py
```

### 命名慣例

- 測試檔案：`test_<module>.py`
- 測試類別：`Test<ClassName>`
- 測試方法：`test_<behavior>`

```python
# test_git_utils.py
class TestRunGitCommand(unittest.TestCase):
    def test_successful_command_returns_true(self):
        ...
    def test_failed_command_returns_false(self):
        ...
    def test_timeout_returns_error_message(self):
        ...
```

## 最佳實踐

### 1. 一個測試驗證一件事

```python
# 好：每個測試只驗證一個行為
def test_valid_input_returns_true(self):
    result = validate("valid")
    self.assertTrue(result)

def test_invalid_input_returns_false(self):
    result = validate("invalid")
    self.assertFalse(result)

# 不好：一個測試驗證多件事
def test_validate(self):
    self.assertTrue(validate("valid"))
    self.assertFalse(validate("invalid"))
    self.assertEqual(validate(""), None)
```

### 2. 使用描述性的測試名稱

```python
# 好：清楚說明測試內容
def test_empty_input_returns_empty_dict(self):
    ...

# 不好：模糊的名稱
def test_input(self):
    ...
```

### 3. 使用 setUp 避免重複

```python
class TestMarkdownChecker(unittest.TestCase):

    def setUp(self):
        self.checker = MarkdownLinkChecker()
        self.test_content = "# Test\n[link](./file.md)"

    def test_check_valid_link(self):
        # 使用 setUp 中建立的物件
        result = self.checker.check(self.test_content)
        ...
```

## 思考題

1. `setUp` 和 `setUpClass` 有什麼區別？什麼時候用哪個？
2. 為什麼測試方法必須以 `test_` 開頭？
3. 如何測試一個需要讀取 stdin 的函式？

## 實作練習

1. 為 `get_current_branch()` 函式撰寫測試
2. 測試一個會拋出異常的函式
3. 使用 `unittest.skip` 暫時跳過某個測試

---

*上一章：[異常處理策略](../exception/)*
*下一章：[Mock 與測試隔離](../mock/)*
