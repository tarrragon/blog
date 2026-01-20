---
title: "3.1 pathlib - 路徑操作"
date: 2026-01-20
description: "物件導向的路徑處理"
weight: 1
---

# pathlib - 路徑操作

`pathlib` 是 Python 3.4+ 引入的現代路徑處理模組，提供物件導向的 API 來處理檔案系統路徑。在 Hook 系統中，幾乎每個檔案都使用 `pathlib`。

## 為什麼使用 pathlib？

### 傳統 os.path 方式

```python
import os

# 組合路徑
config_path = os.path.join(project_root, ".claude", "config.json")

# 取得父目錄
parent = os.path.dirname(file_path)

# 取得檔名
filename = os.path.basename(file_path)

# 檢查存在
if os.path.exists(config_path):
    ...
```

### 現代 pathlib 方式

```python
from pathlib import Path

# 組合路徑
config_path = project_root / ".claude" / "config.json"

# 取得父目錄
parent = file_path.parent

# 取得檔名
filename = file_path.name

# 檢查存在
if config_path.exists():
    ...
```

## 基本操作

### 建立 Path 物件

```python
from pathlib import Path

# 從字串建立
p = Path("/home/user/project")

# 當前目錄
cwd = Path.cwd()

# 使用者目錄
home = Path.home()

# 從 __file__ 建立
current_file = Path(__file__)
```

### 路徑組合

使用 `/` 運算子組合路徑（非常直觀）：

```python
from pathlib import Path

project = Path("/home/user/project")
config = project / ".claude" / "config.json"

# 等同於
config = project.joinpath(".claude", "config.json")
```

### 取得路徑部分

```python
p = Path("/home/user/project/file.txt")

p.name        # "file.txt"
p.stem        # "file"（不含副檔名）
p.suffix      # ".txt"
p.parent      # Path("/home/user/project")
p.parents[0]  # Path("/home/user/project")
p.parents[1]  # Path("/home/user")
p.parts       # ('/', 'home', 'user', 'project', 'file.txt')
```

## 實際範例：Hook 系統

### 日誌目錄建立

來自 `.claude/lib/hook_logging.py`：

```python
from pathlib import Path

def setup_hook_logging(hook_name: str) -> logging.Logger:
    # 建立日誌目錄
    project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    log_dir = Path(project_root) / ".claude" / "hook-logs" / hook_name

    # mkdir 的 parents=True 會建立所有不存在的父目錄
    # exist_ok=True 表示如果目錄已存在不會報錯
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日誌檔案路徑
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"{hook_name}-{timestamp}.log"

    # ...
```

### 設定檔案搜尋

來自 `.claude/lib/config_loader.py`：

```python
def load_config(config_name: str) -> dict:
    config_dir = get_config_dir()

    # 優先嘗試不同副檔名
    yaml_path = config_dir / f"{config_name}.yaml"
    yml_path = config_dir / f"{config_name}.yml"
    json_path = config_dir / f"{config_name}.json"

    if yaml_path.exists():
        return _load_yaml_file(yaml_path)
    elif yml_path.exists():
        return _load_yaml_file(yml_path)
    elif json_path.exists():
        return _load_json_file(json_path)

    raise FileNotFoundError(f"Configuration not found: {config_name}")
```

## 檔案操作

### 讀取檔案

```python
from pathlib import Path

p = Path("config.json")

# 讀取文字
content = p.read_text(encoding="utf-8")

# 讀取位元組
data = p.read_bytes()
```

### 寫入檔案

```python
from pathlib import Path

p = Path("output.txt")

# 寫入文字
p.write_text("Hello, World!", encoding="utf-8")

# 寫入位元組
p.write_bytes(b"binary data")
```

### 檢查檔案類型

```python
p = Path("/some/path")

p.exists()      # 是否存在
p.is_file()     # 是否為檔案
p.is_dir()      # 是否為目錄
p.is_symlink()  # 是否為符號連結
```

## 目錄操作

### 建立目錄

```python
from pathlib import Path

p = Path("new_dir/sub_dir")

# 建立目錄（包含父目錄）
p.mkdir(parents=True, exist_ok=True)
```

### 列出目錄內容

```python
from pathlib import Path

p = Path(".")

# 列出所有項目
for item in p.iterdir():
    print(item)

# 使用 glob 模式
for py_file in p.glob("*.py"):
    print(py_file)

# 遞迴搜尋
for md_file in p.rglob("*.md"):
    print(md_file)
```

### 實際範例：驗證所有 Hook

來自 `.claude/lib/hook_validator.py`：

```python
def validate_all_hooks(self, hooks_dir: Optional[str] = None):
    if hooks_dir is None:
        hooks_dir = str(self.project_root / ".claude" / "hooks")

    hooks_dir = self._resolve_path(hooks_dir)

    # 找出所有 .py 檔案
    results = []
    for hook_file in sorted(hooks_dir.glob("*.py")):
        if hook_file.name.startswith("_"):
            continue  # 跳過 __init__.py 等
        results.append(self.validate_hook(str(hook_file)))

    return results
```

## 路徑解析

### 相對路徑與絕對路徑

```python
from pathlib import Path

p = Path("./relative/path")

# 轉換為絕對路徑
absolute = p.resolve()

# 相對於某個目錄
relative = p.relative_to(Path.cwd())
```

### 實際範例：解析路徑

```python
def _resolve_path(self, path: str) -> Path:
    """解析路徑為絕對路徑"""
    p = Path(path)
    if p.is_absolute():
        return p
    return self.project_root / p
```

## 常用模式

### 計算腳本所在目錄

```python
# 在 .claude/hooks/my_hook.py 中
from pathlib import Path

# 取得 lib 目錄
lib_path = Path(__file__).parent.parent / "lib"
# __file__ = .claude/hooks/my_hook.py
# parent = .claude/hooks/
# parent.parent = .claude/
# / "lib" = .claude/lib/
```

### 確保檔案副檔名

```python
def ensure_extension(path: Path, ext: str) -> Path:
    """確保檔案有指定的副檔名"""
    if path.suffix != ext:
        return path.with_suffix(ext)
    return path

# 使用
p = Path("config")
p = ensure_extension(p, ".json")  # Path("config.json")
```

### 安全的檔案讀取

```python
def safe_read_file(path: Path) -> Optional[str]:
    """安全讀取檔案，不存在時返回 None"""
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None
```

## 思考題

1. `Path("/a/b") / "c"` 和 `Path("/a/b").joinpath("c")` 有什麼區別？
2. 為什麼 `mkdir(parents=True, exist_ok=True)` 是常見的組合？
3. `glob("**/*.py")` 和 `rglob("*.py")` 有什麼區別？

## 實作練習

1. 寫一個函式，找出目錄中所有超過 1MB 的檔案
2. 寫一個函式，將所有 `.txt` 檔案重命名為 `.md`
3. 實作一個函式，計算目錄中所有 Python 檔案的總行數

---

*下一章：[json - 序列化](../json/)*
