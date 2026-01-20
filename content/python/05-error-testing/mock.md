---
title: "5.4 Mock 與測試隔離"
description: "隔離外部依賴"
weight: 4
---

# Mock 與測試隔離

當測試的程式碼依賴外部資源（檔案系統、網路、stdin/stdout）時，我們需要使用 Mock 來隔離這些依賴，確保測試的可靠性和速度。

## 為什麼需要 Mock？

### 問題場景

```python
def read_hook_input() -> dict:
    """從 stdin 讀取 JSON 輸入"""
    return json.load(sys.stdin)

# 測試時如何提供 stdin？
```

### 使用 Mock 解決

```python
from unittest.mock import patch
from io import StringIO

def test_read_hook_input():
    json_input = '{"key": "value"}'

    # 用 StringIO 替換 sys.stdin
    with patch("sys.stdin", StringIO(json_input)):
        result = read_hook_input()

    assert result == {"key": "value"}
```

## unittest.mock 基礎

### patch 裝飾器

```python
from unittest.mock import patch

class TestMyFunction(unittest.TestCase):

    @patch("module.function_to_mock")
    def test_something(self, mock_func):
        mock_func.return_value = "mocked result"
        result = my_function()
        self.assertEqual(result, "expected")
```

### patch 上下文管理器

```python
def test_something(self):
    with patch("module.function") as mock_func:
        mock_func.return_value = "mocked"
        result = my_function()
        self.assertEqual(result, "expected")
```

## 實際範例：測試 Hook IO

來自 `.claude/lib/tests/test_hook_io.py`：

```python
import json
import unittest
from io import StringIO
from unittest.mock import patch

from hook_io import read_hook_input, write_hook_output


class TestReadHookInput(unittest.TestCase):
    """測試 read_hook_input 函式"""

    def test_valid_json_input(self):
        """測試有效的 JSON 輸入"""
        test_data = {"tool_name": "Write", "file_path": "/test.txt"}
        json_input = json.dumps(test_data)

        # Mock sys.stdin
        with patch("sys.stdin", StringIO(json_input)):
            result = read_hook_input()

        self.assertEqual(result, test_data)

    def test_invalid_json_returns_empty_dict(self):
        """測試無效的 JSON"""
        with patch("sys.stdin", StringIO("not valid json")):
            result = read_hook_input()

        self.assertEqual(result, {})


class TestWriteHookOutput(unittest.TestCase):
    """測試 write_hook_output 函式"""

    def test_output_json_format(self):
        """測試輸出為有效的 JSON"""
        test_data = {"decision": "allow"}

        # Mock sys.stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            write_hook_output(test_data)
            output = mock_stdout.getvalue()

        # 驗證輸出是有效的 JSON
        parsed = json.loads(output)
        self.assertEqual(parsed["decision"], "allow")

    def test_chinese_preserved(self):
        """測試中文字元被保留"""
        test_data = {"message": "你好"}

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            write_hook_output(test_data, ensure_ascii=False)
            output = mock_stdout.getvalue()

        self.assertIn("你好", output)
```

## Mock 物件的設定

### return_value

```python
from unittest.mock import Mock

mock_func = Mock()
mock_func.return_value = 42

result = mock_func()  # 42
```

### side_effect - 動態返回值

```python
from unittest.mock import Mock

mock_func = Mock()

# 依序返回不同值
mock_func.side_effect = [1, 2, 3]
mock_func()  # 1
mock_func()  # 2
mock_func()  # 3

# 根據輸入返回不同值
def side_effect_func(x):
    return x * 2

mock_func.side_effect = side_effect_func
mock_func(5)  # 10
```

### side_effect - 拋出異常

```python
from unittest.mock import Mock

mock_func = Mock()
mock_func.side_effect = ValueError("Error!")

mock_func()  # 拋出 ValueError
```

## 驗證 Mock 被呼叫

```python
from unittest.mock import Mock, call

mock_func = Mock()

# 呼叫 mock
mock_func(1, 2, key="value")
mock_func(3, 4)

# 驗證呼叫
mock_func.assert_called()              # 被呼叫過
mock_func.assert_called_once()         # 只被呼叫一次（這會失敗）
mock_func.assert_called_with(3, 4)     # 最後一次呼叫的參數

# 檢查所有呼叫
mock_func.assert_has_calls([
    call(1, 2, key="value"),
    call(3, 4)
])

# 呼叫次數
self.assertEqual(mock_func.call_count, 2)
```

## 實際範例：測試 Git 工具

```python
import unittest
from unittest.mock import patch, Mock

from git_utils import run_git_command, get_current_branch


class TestRunGitCommand(unittest.TestCase):

    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        """測試成功的 git 命令"""
        # 設定 mock 返回值
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success, output = run_git_command(["branch", "--show-current"])

        self.assertTrue(success)
        self.assertEqual(output, "main")

        # 驗證 subprocess.run 被正確呼叫
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0], ["git", "branch", "--show-current"])

    @patch("subprocess.run")
    def test_failed_command(self, mock_run):
        """測試失敗的 git 命令"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result

        success, output = run_git_command(["status"])

        self.assertFalse(success)
        self.assertIn("not a git repository", output)

    @patch("subprocess.run")
    def test_timeout(self, mock_run):
        """測試命令超時"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 10)

        success, output = run_git_command(["status"], timeout=10)

        self.assertFalse(success)
        self.assertIn("timed out", output)
```

## MagicMock

`MagicMock` 自動支援魔術方法：

```python
from unittest.mock import MagicMock

mock = MagicMock()

# 自動支援各種操作
mock[0]          # 不會報錯
mock.anything()  # 返回另一個 MagicMock
len(mock)        # 返回預設值
str(mock)        # 返回字串
```

## 測試檔案操作

### 使用 mock_open

```python
from unittest.mock import patch, mock_open

def test_read_config():
    config_content = '{"key": "value"}'

    with patch("builtins.open", mock_open(read_data=config_content)):
        result = load_config("config.json")

    self.assertEqual(result["key"], "value")
```

### 測試 Path 物件

```python
from unittest.mock import patch, Mock

def test_check_file_exists():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True

        result = check_file_exists("/some/path")

        self.assertTrue(result)
```

## patch 的位置

**重要**：patch 的目標是模組匯入的位置，而非定義的位置。

```python
# module_a.py
from os import getcwd

def my_function():
    return getcwd()

# test_module_a.py
# 正確：patch 匯入的位置
@patch("module_a.getcwd")
def test_my_function(mock_getcwd):
    ...

# 錯誤：patch 定義的位置
@patch("os.getcwd")  # 不會生效！
def test_my_function(mock_getcwd):
    ...
```

## 最佳實踐

### 1. 只 Mock 外部依賴

```python
# 好：Mock 外部系統
@patch("subprocess.run")
def test_git_command(self, mock_run):
    ...

# 不好：Mock 內部邏輯
@patch("my_module.internal_helper")
def test_my_function(self, mock_helper):
    ...  # 過度 mock 會讓測試變脆弱
```

### 2. 使用 autospec

```python
from unittest.mock import patch

# autospec 確保 mock 的簽名與原函式相同
@patch("module.function", autospec=True)
def test_something(self, mock_func):
    # 如果呼叫簽名錯誤會報錯
    mock_func("wrong", "args")  # 可能報錯
```

### 3. 清理 Mock

```python
def setUp(self):
    self.patcher = patch("module.function")
    self.mock_func = self.patcher.start()

def tearDown(self):
    self.patcher.stop()  # 確保清理
```

## 思考題

1. patch 的目標為什麼是匯入位置而非定義位置？
2. `Mock` 和 `MagicMock` 有什麼區別？
3. 什麼時候應該使用 `autospec=True`？

## 實作練習

1. 為 `get_current_branch()` 撰寫使用 Mock 的測試
2. 測試一個讀取檔案的函式，使用 `mock_open`
3. 測試一個會拋出異常的外部呼叫，使用 `side_effect`

---

*上一章：[unittest 基礎](../unittest/)*
*下一模組：[物件導向設計](../../04-oop/)*
