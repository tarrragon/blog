---
title: "配置與程式碼分離"
date: 2026-01-20
description: "學習將硬編碼配置抽離到 YAML 檔案，提升程式碼可維護性"
weight: 72
---

# 配置與程式碼分離

本章基於 Error Pattern ARCH-001，學習如何識別配置與程式碼混合的問題，並掌握正確的分離方法。

## 問題背景

### 症狀

單一檔案超過 800 行，其中約一半是硬編碼的配置資料：

```python
# 800+ 行的 Hook 檔案
PROTECTED_BRANCHES = ["main", "master", "develop"]
ALLOWED_PATTERNS = ["feat/*", "fix/*", "chore/*"]
ERROR_MESSAGES = {
    "branch_not_allowed": "分支名稱不符合規範",
    "missing_ticket": "缺少 Ticket 引用",
    "invalid_commit": "提交訊息格式錯誤",
    # ... 更多配置，數百行
}

WORKFLOW_RULES = {
    "pre_commit": {
        "checks": ["lint", "test", "format"],
        "timeout": 300,
        # ...
    },
    # ...
}

def check_branch():
    # 實際邏輯只有幾十行
    pass
```

### 5 Why 分析

1. Why 1: 單一檔案包含大量配置資料和程式邏輯
2. Why 2: 開發時為求快速，直接在程式碼中定義配置
3. Why 3: 缺乏配置管理策略和標準化做法
4. Why 4: Hook 系統初期設計未考慮配置分離
5. Why 5: **缺乏明確的架構原則指導配置與程式碼分離**

## 分離原則

### 什麼應該放在配置檔

| 資料類型 | 放置位置 | 範例 |
|---------|---------|------|
| 業務規則 | YAML 檔案 | 分支規則、檔案類型限制 |
| 錯誤訊息 | YAML 或 i18n | 多語言訊息 |
| 清單資料 | YAML 檔案 | 允許的分支、忽略的檔案 |
| 程式常數 | Python 檔案 | TIMEOUT = 30 |
| 程式邏輯 | Python 檔案 | 核心處理邏輯 |

### 判斷標準

問自己這些問題：

1. **這個值會隨環境改變嗎？** → 放配置
2. **非工程師可能需要修改嗎？** → 放配置
3. **這是業務規則還是技術實作？** → 業務規則放配置
4. **這個值和程式邏輯緊密耦合嗎？** → 放程式碼

## 實作方式

### 步驟 1：建立 YAML 配置檔

```yaml
# config/branch_rules.yaml
protected_branches:
  - main
  - master
  - develop

allowed_patterns:
  - "feat/*"
  - "fix/*"
  - "chore/*"
  - "docs/*"
  - "refactor/*"

error_messages:
  branch_not_allowed: "分支名稱不符合規範"
  missing_ticket: "缺少 Ticket 引用"
  invalid_commit: "提交訊息格式錯誤"
```

### 步驟 2：建立配置載入器

```python
# lib/config_loader.py
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

# 配置快取（單例模式）
_config_cache: Dict[str, Any] = {}

def get_config_dir() -> Path:
    """取得配置目錄路徑。"""
    return Path(__file__).parent.parent / "config"

def load_config(filename: str) -> Dict[str, Any]:
    """載入 YAML 配置檔案。

    Args:
        filename: 配置檔案名稱（相對於 config 目錄）

    Returns:
        配置內容字典

    Raises:
        FileNotFoundError: 找不到配置檔案
        yaml.YAMLError: YAML 解析錯誤
    """
    # 檢查快取
    if filename in _config_cache:
        return _config_cache[filename]

    config_path = get_config_dir() / filename

    if not config_path.exists():
        raise FileNotFoundError(f"配置檔案不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 存入快取
    _config_cache[filename] = config
    return config

def get_config_value(
    filename: str,
    key: str,
    default: Optional[Any] = None
) -> Any:
    """取得配置中的特定值。

    支援點號分隔的巢狀 key，例如 "workflow.pre_commit.timeout"
    """
    config = load_config(filename)

    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value
```

### 步驟 3：在 Hook 中使用

```python
# hooks/branch_guardian.py
from lib.config_loader import load_config, get_config_value

def check_branch():
    """檢查分支是否符合規範。"""
    config = load_config("branch_rules.yaml")

    current_branch = get_current_branch()

    # 使用配置中的保護分支清單
    if current_branch in config["protected_branches"]:
        message = config["error_messages"]["branch_not_allowed"]
        print(f"錯誤: {message}")
        return False

    return True
```

## 重構範例

### 重構前

```
hooks/
└── user_prompt_submit.py  # 847 行，配置佔 400+ 行
```

```python
# user_prompt_submit.py (重構前)
# 400+ 行的配置定義
WORKFLOW_CHECKS = {
    "tdd_phase_check": {
        "enabled": True,
        "phases": ["phase1", "phase2", "phase3", "phase4"],
        # ...
    },
    # ... 數百行配置
}

ERROR_MESSAGES = {
    "phase_missing": "TDD Phase 不完整",
    # ... 數十行訊息
}

# 200 行的實際邏輯
def main():
    # ...
```

### 重構後

```
hooks/
├── user_prompt_submit.py  # 約 200 行純邏輯
└── config/
    ├── workflow_checks.yaml
    └── error_messages.yaml

lib/
└── config_loader.py       # 統一配置載入
```

```python
# user_prompt_submit.py (重構後)
from lib.config_loader import load_config

def main():
    config = load_config("workflow_checks.yaml")
    messages = load_config("error_messages.yaml")

    # 清晰的邏輯，沒有配置雜訊
    for check_name, check_config in config.items():
        if check_config.get("enabled", True):
            run_check(check_name, check_config)
```

## 進階技巧

### 配置驗證

```python
from dataclasses import dataclass
from typing import List

@dataclass
class BranchRulesConfig:
    """分支規則配置結構。"""
    protected_branches: List[str]
    allowed_patterns: List[str]
    error_messages: dict

def load_branch_rules() -> BranchRulesConfig:
    """載入並驗證分支規則配置。"""
    raw_config = load_config("branch_rules.yaml")

    # 驗證必要欄位
    required_fields = ["protected_branches", "allowed_patterns"]
    for field in required_fields:
        if field not in raw_config:
            raise ValueError(f"配置缺少必要欄位: {field}")

    return BranchRulesConfig(
        protected_branches=raw_config["protected_branches"],
        allowed_patterns=raw_config["allowed_patterns"],
        error_messages=raw_config.get("error_messages", {})
    )
```

### 環境特定配置

```yaml
# config/branch_rules.yaml
default:
  protected_branches:
    - main
    - master

development:
  protected_branches:
    - main

production:
  protected_branches:
    - main
    - master
    - release
```

```python
import os

def load_env_config(filename: str) -> dict:
    """載入環境特定配置。"""
    config = load_config(filename)
    env = os.getenv("ENV", "default")

    # 合併預設配置和環境特定配置
    base_config = config.get("default", {})
    env_config = config.get(env, {})

    return {**base_config, **env_config}
```

## 檢測方法

```bash
# 檢查超長檔案
find .claude/hooks -name "*.py" -exec wc -l {} \; | awk '$1 > 500'

# 檢查配置行數佔比（大寫常數定義）
for f in .claude/hooks/*.py; do
    total=$(wc -l < "$f")
    config=$(grep -c "^\s*[A-Z_]*\s*=" "$f" || echo 0)
    echo "$f: $config config lines / $total total"
done
```

## 常見錯誤

### 錯誤 1：配置散落各處

```python
# 錯誤：同一個配置在多個檔案定義
# file1.py
PROTECTED_BRANCHES = ["main", "master"]

# file2.py
PROTECTED_BRANCHES = ["main", "master", "develop"]  # 不一致！
```

**解決**：集中管理所有配置。

### 錯誤 2：過度配置化

```python
# 錯誤：把程式邏輯也放進配置
# config.yaml
process_steps:
  - name: "validate"
    function: "validate_input"
  - name: "transform"
    function: "transform_data"
```

**解決**：程式邏輯保留在程式碼中，配置只放資料。

### 錯誤 3：缺乏預設值

```python
# 錯誤：沒有處理配置缺失
timeout = config["timeout"]  # KeyError!

# 正確：提供預設值
timeout = config.get("timeout", 30)
```

## 實作練習

### 練習 1：識別可配置化的內容

檢視以下程式碼，標記出應該移到配置檔的部分：

```python
def validate_commit_message(message):
    PREFIXES = ["feat", "fix", "docs", "chore", "refactor"]
    MAX_LENGTH = 72
    FORBIDDEN_WORDS = ["WIP", "TODO", "FIXME"]

    if len(message) > MAX_LENGTH:
        return False, "訊息過長"

    if not any(message.startswith(p) for p in PREFIXES):
        return False, "缺少前綴"

    for word in FORBIDDEN_WORDS:
        if word in message:
            return False, f"包含禁止字詞: {word}"

    return True, "驗證通過"
```

<details>
<summary>參考答案</summary>

應該配置化的內容：
- `PREFIXES` - 可能隨專案規範調整
- `MAX_LENGTH` - 可能隨團隊習慣調整
- `FORBIDDEN_WORDS` - 可能隨專案需求調整
- 錯誤訊息 - 可能需要多語言支援

```yaml
# commit_rules.yaml
prefixes:
  - feat
  - fix
  - docs
  - chore
  - refactor

max_length: 72

forbidden_words:
  - WIP
  - TODO
  - FIXME

messages:
  too_long: "訊息過長"
  missing_prefix: "缺少前綴"
  forbidden_word: "包含禁止字詞: {word}"
```

</details>

### 練習 2：實作配置載入

為練習 1 的配置撰寫載入和使用程式碼。

<details>
<summary>參考答案</summary>

```python
from lib.config_loader import load_config

def validate_commit_message(message: str) -> tuple[bool, str]:
    config = load_config("commit_rules.yaml")

    if len(message) > config["max_length"]:
        return False, config["messages"]["too_long"]

    if not any(message.startswith(p) for p in config["prefixes"]):
        return False, config["messages"]["missing_prefix"]

    for word in config["forbidden_words"]:
        if word in message:
            msg = config["messages"]["forbidden_word"].format(word=word)
            return False, msg

    return True, "驗證通過"
```

</details>

## 小結

- 配置與程式碼混合是常見的架構問題
- 使用 YAML 檔案集中管理配置
- 建立統一的配置載入機制
- 配置應該只包含資料，不包含邏輯
- 適當提供預設值處理配置缺失

## 下一步

- [DRY 原則與共用程式庫](../dry-principle/) - 學習消除重複程式碼
- [重構案例研究](../case-study/) - 看完整的重構流程

---

*文件版本：v0.30.0*
*建立日期：2026-01-20*
