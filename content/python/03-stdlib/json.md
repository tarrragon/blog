---
title: "3.2 json - 序列化"
date: 2026-01-20
description: "資料的讀寫與轉換"
weight: 2
---

# json - 序列化

JSON（JavaScript Object Notation）是現代應用程式中最常用的資料交換格式。Python 的 `json` 模組提供了簡單的 API 來處理 JSON 資料。

## 基本操作

### 序列化（Python 物件 → JSON 字串）

```python
import json

# 字典轉 JSON 字串
data = {"name": "Python", "version": 3.11}
json_str = json.dumps(data)
# '{"name": "Python", "version": 3.11}'

# 格式化輸出
json_str = json.dumps(data, indent=2)
# {
#   "name": "Python",
#   "version": 3.11
# }
```

### 反序列化（JSON 字串 → Python 物件）

```python
import json

json_str = '{"name": "Python", "version": 3.11}'
data = json.loads(json_str)
# {'name': 'Python', 'version': 3.11}
```

### 檔案讀寫

```python
import json

# 寫入檔案
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

# 讀取檔案
with open("config.json", "r", encoding="utf-8") as f:
    data = json.load(f)
```

## 實際範例：Hook 系統

### Hook 輸入讀取

來自 `.claude/lib/hook_io.py`：

```python
import json
import sys

def read_hook_input() -> dict:
    """
    從 stdin 讀取 Hook 輸入

    Returns:
        dict: 解析後的 JSON 資料，解析失敗時返回空字典
    """
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
    except Exception:
        return {}
```

### Hook 輸出寫入

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
        ensure_ascii: 是否確保 ASCII 編碼
        indent: JSON 縮排空格數
    """
    print(json.dumps(output, ensure_ascii=ensure_ascii, indent=indent))
```

## 重要參數

### ensure_ascii

控制是否將非 ASCII 字元轉換為跳脫序列：

```python
import json

data = {"message": "你好"}

# ensure_ascii=True（預設）
json.dumps(data)
# '{"message": "\\u4f60\\u597d"}'

# ensure_ascii=False（保留原字元）
json.dumps(data, ensure_ascii=False)
# '{"message": "你好"}'
```

在 Hook 系統中，我們使用 `ensure_ascii=False` 來保留中文字元。

### indent

控制輸出的縮排：

```python
data = {"name": "Python", "features": ["simple", "readable"]}

# 無縮排
json.dumps(data)
# '{"name": "Python", "features": ["simple", "readable"]}'

# 有縮排
json.dumps(data, indent=2)
# {
#   "name": "Python",
#   "features": [
#     "simple",
#     "readable"
#   ]
# }
```

### sort_keys

按鍵名排序輸出：

```python
data = {"z": 1, "a": 2, "m": 3}

json.dumps(data, sort_keys=True)
# '{"a": 2, "m": 3, "z": 1}'
```

### default

處理無法序列化的物件：

```python
from datetime import datetime
import json

def json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

data = {"timestamp": datetime.now()}
json.dumps(data, default=json_serializer)
# '{"timestamp": "2024-01-20T15:30:00"}'
```

## 型別對應

| Python 型別 | JSON 型別 |
|------------|-----------|
| dict | object |
| list, tuple | array |
| str | string |
| int, float | number |
| True | true |
| False | false |
| None | null |

## 常見錯誤處理

### JSONDecodeError

```python
import json

def safe_parse_json(json_str: str) -> dict:
    """安全解析 JSON，失敗時返回空字典"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {e}")
        return {}
```

### 無法序列化的物件

```python
import json
from dataclasses import dataclass, asdict

@dataclass
class Config:
    name: str
    timeout: int

config = Config("test", 30)

# 錯誤：dataclass 無法直接序列化
# json.dumps(config)  # TypeError

# 正確：轉換為字典
json.dumps(asdict(config))
# '{"name": "test", "timeout": 30}'
```

## 實際應用：配置檔案載入

來自 `.claude/lib/config_loader.py`：

```python
def _load_json_file(file_path: Path) -> dict:
    """載入 JSON 檔案"""
    import json
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

## 與 YAML 的比較

Hook 系統同時支援 JSON 和 YAML：

```python
# 嘗試導入 PyYAML，如果失敗則使用 JSON 作為備案
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    import json

def load_config(config_name: str) -> dict:
    if yaml_path.exists() and HAS_YAML:
        return _load_yaml_file(yaml_path)
    elif json_path.exists():
        return _load_json_file(json_path)
```

## 最佳實踐

### 1. 總是指定編碼

```python
# 好
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f)

# 不好（可能在不同系統有不同行為）
with open("data.json", "w") as f:
    json.dump(data, f)
```

### 2. 處理解析錯誤

```python
def read_config(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
```

### 3. 使用 ensure_ascii=False 處理中文

```python
# 輸出中文友好的 JSON
json.dumps(data, ensure_ascii=False, indent=2)
```

## 思考題

1. `json.dump()` 和 `json.dumps()` 有什麼區別？
2. 為什麼 Hook 系統的 `read_hook_input()` 捕獲 `JSONDecodeError` 後返回空字典而不是拋出異常？
3. 如何將包含 `datetime` 物件的字典序列化為 JSON？

## 實作練習

1. 寫一個函式，合併多個 JSON 檔案
2. 實作一個支援註解的 JSON 讀取器（移除 `//` 開頭的行）
3. 寫一個函式，比較兩個 JSON 檔案的差異

---

*上一章：[pathlib - 路徑操作](../pathlib/)*
*下一章：[subprocess - 執行外部命令](../subprocess/)*
