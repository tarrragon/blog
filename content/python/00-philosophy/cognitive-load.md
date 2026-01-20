---
title: "認知負擔：程式碼設計的核心目的"
date: 2026-01-20
description: "所有設計原則的統一視角：降低閱讀者的認知負擔"
weight: 1
---

# 認知負擔：程式碼設計的核心目的

## 什麼是認知負擔？

認知負擔（Cognitive Load）是心理學中的概念，指的是人腦在處理資訊時所承受的負擔量。

### 工作記憶的限制

心理學家 George Miller 在 1956 年提出著名的「7 加減 2」法則：人類的工作記憶一次只能處理約 **5 到 9 個項目**。

這意味著當你閱讀程式碼時：

- 如果需要同時記住超過 7 個變數的狀態，你會開始混淆
- 如果需要追蹤超過 7 層的呼叫關係，你會迷失方向
- 如果一個函式做超過 7 件事，你會難以理解它的目的

### 程式碼閱讀中的認知負擔

閱讀程式碼時，以下情況會增加認知負擔：

```python
# 高認知負擔的程式碼
def process(d):
    r = []
    for i in d:
        if i[0] > 0 and i[1] != "" and len(i) >= 3:
            t = i[0] * 2 + len(i[1])
            if t > 10:
                r.append((i[2], t))
    return sorted(r, key=lambda x: x[1], reverse=True)
```

閱讀這段程式碼時，你需要：

1. 記住 `d` 是什麼（輸入資料）
2. 追蹤 `r` 的狀態（結果列表）
3. 理解 `i` 的結構（至少有 3 個元素的序列）
4. 計算 `t` 的值（某種加權計算）
5. 記住過濾條件（三個條件）
6. 理解最終排序邏輯

這就是典型的高認知負擔程式碼。

## 核心論點：所有原則的統一目的

### Clean Code 不是「優美」，而是「易讀」

很多人誤解 Clean Code 是追求程式碼的「優美」或「藝術性」。但事實上：

```
Clean Code 的真正目標是：讓程式碼能被人類輕鬆理解
```

優美的程式碼如果難以理解，就不是好的程式碼。樸素但清晰的程式碼，遠勝於巧妙但費解的程式碼。

### 無法讀懂的程式碼沒人會讀

這是一個殘酷的現實：

- 如果程式碼太難讀，維護者會選擇重寫而非修改
- 如果程式碼太難讀，除錯會變成猜測遊戲
- 如果程式碼太難讀，知識無法傳承

### DRY、SOLID、命名規範 = 降低認知負擔的不同策略

讓我們重新審視這些經典原則：

| 原則 | 傳統解釋 | 認知負擔視角 |
|------|---------|-------------|
| DRY | 不要重複自己 | 讀者只需要理解一次，減少記憶負擔 |
| 單一職責 | 一個類別只做一件事 | 讀者一次只需要理解一個概念 |
| 開放封閉 | 對擴展開放，對修改封閉 | 讀者不需要理解整個系統就能擴展 |
| 依賴反轉 | 依賴抽象而非具體 | 讀者可以忽略實作細節 |
| 命名規範 | 使用有意義的名稱 | 讀者不需要追溯定義就能理解 |

**它們的共同目標都是：降低閱讀者的認知負擔。**

## 認知負擔的來源

### 1. 需要記住前面發生什麼事

```python
# 高認知負擔：需要記住 data 經歷了什麼轉換
data = get_raw_data()
data = filter_invalid(data)
data = normalize(data)
data = enrich(data)
result = aggregate(data)

# 低認知負擔：每步都有清晰的命名
raw_data = get_raw_data()
valid_data = filter_invalid(raw_data)
normalized_data = normalize(valid_data)
enriched_data = enrich(normalized_data)
result = aggregate(enriched_data)
```

### 2. 需要追蹤變數經歷的轉換

```python
# 高認知負擔：temp 到底是什麼？
temp = user_input.strip()
temp = temp.lower()
temp = temp.replace(" ", "_")
temp = re.sub(r'[^a-z_]', '', temp)

# 低認知負擔：每個變數都說明自己是什麼
trimmed_input = user_input.strip()
lowercase_input = trimmed_input.lower()
underscored_input = lowercase_input.replace(" ", "_")
clean_identifier = re.sub(r'[^a-z_]', '', underscored_input)
```

### 3. 需要理解隱藏的狀態變化

```python
# 高認知負擔：process() 會修改什麼？
class DataProcessor:
    def process(self):
        self._validate()      # 可能修改 self.errors?
        self._transform()     # 可能修改 self.data?
        self._save()          # 可能修改 self.saved?

# 低認知負擔：回傳值明確說明結果
class DataProcessor:
    def process(self) -> ProcessResult:
        errors = self._validate(self.data)
        if errors:
            return ProcessResult(success=False, errors=errors)

        transformed = self._transform(self.data)
        save_result = self._save(transformed)
        return ProcessResult(success=True, saved_path=save_result)
```

### 4. 需要跳轉到其他地方才能理解當前程式碼

```python
# 高認知負擔：需要跳到 MAGIC_VALUE 的定義
if score > MAGIC_VALUE:
    return "pass"

# 低認知負擔：直接說明意圖
PASSING_SCORE_THRESHOLD = 60
if score > PASSING_SCORE_THRESHOLD:
    return "pass"
```

## 降低認知負擔的原則

### 原則一：在當下就能理解

好的程式碼不需要讀者記住之前發生的事情：

```python
# 不好：需要記住 user 是什麼
def process(user):
    if user[0] and user[1] > 18:
        return user[2]

# 好：當下就能理解
def get_adult_user_name(user: User) -> Optional[str]:
    if user.is_active and user.age > 18:
        return user.name
    return None
```

### 原則二：程式碼即文件（自文件化）

程式碼本身應該說明它在做什麼：

```python
# 不好：需要註解才能理解
# 檢查用戶是否有權限
if u.r >= 3 and u.s == 'a':
    pass

# 好：程式碼本身就是說明
if user.role_level >= ADMIN_LEVEL and user.status == UserStatus.ACTIVE:
    pass
```

### 原則三：最小意外原則

程式碼的行為應該符合讀者的預期：

```python
# 不好：get 通常不應該修改狀態
def get_user_count(self):
    self._refresh_cache()  # 意外的副作用！
    return len(self._users)

# 好：get 只做讀取
def get_user_count(self) -> int:
    return len(self._users)

def refresh_and_get_user_count(self) -> int:
    self._refresh_cache()
    return len(self._users)
```

## 實際案例：Hook 系統重構

讓我們看一個實際的重構案例。

### 重構前（高認知負擔）

```python
def check_hook(path):
    with open(path) as f:
        c = f.read()

    # 檢查 shebang
    if not c.startswith("#!"):
        return False, "no shebang"

    # 解析配置
    import yaml
    cfg = yaml.safe_load(open(".claude/config.yaml"))

    # 驗證
    for h in cfg.get("hooks", []):
        if h.get("path") == str(path):
            if not os.path.exists(path):
                return False, "not found"
            if not os.access(path, os.X_OK):
                return False, "not executable"
            return True, "ok"

    return False, "not registered"
```

讀者需要：
- 記住 `c` 是檔案內容
- 理解為什麼要檢查 shebang
- 追蹤 `cfg` 的結構
- 理解 `h` 和 `path` 的關係

### 重構後（低認知負擔）

```python
from lib.config_loader import load_hook_config
from lib.hook_validator import validate_hook_file

def check_hook(hook_path: Path) -> tuple[bool, str]:
    """
    檢查指定的 Hook 檔案是否有效。

    Returns:
        (是否有效, 訊息)
    """
    # 載入配置
    config = load_hook_config()

    # 檢查是否已註冊
    if not config.is_registered(hook_path):
        return False, "Hook 未在配置中註冊"

    # 驗證檔案
    validation_result = validate_hook_file(hook_path)

    return validation_result.is_valid, validation_result.message
```

改善之處：
- 函式名稱說明目的
- 型別提示說明輸入輸出
- 每個步驟都有清晰的意圖
- 複雜邏輯封裝在專門的函式中

## 自我檢查清單

閱讀或撰寫程式碼時，問自己這些問題：

- [ ] 讀者需要記住幾個變數的狀態？（應該少於 5 個）
- [ ] 讀者需要追蹤多少層呼叫？（應該少於 3 層）
- [ ] 讀者能在當下理解這段程式碼嗎？（不需要往回看）
- [ ] 變數名稱是否說明它是什麼？（不是它怎麼來的）
- [ ] 函式名稱是否說明它做什麼？（不是它怎麼做的）

## 小結

**認知負擔是程式碼品質的終極度量標準。**

所有的設計原則、最佳實踐、重構技巧，都可以用一個問題來檢驗：

> 這樣做是否降低了閱讀者的認知負擔？

當你面對設計決策時，不要問「這樣是否符合 DRY」或「這樣是否符合 SOLID」，而是問：

> 這樣寫的話，下一個讀這段程式碼的人（可能是三個月後的你自己），需要記住多少東西才能理解它？

這就是程式碼設計的核心目的。

---

## 延伸閱讀

- [命名的藝術：讓程式碼說故事](../naming-art/) - 如何用命名降低認知負擔
- [開放封閉原則與認知負擔](../open-closed-principle/) - SOLID 原則的認知負擔詮釋

---

## 參考資料

- Miller, G. A. (1956). "The Magical Number Seven, Plus or Minus Two"
- Martin, R. C. (2008). "Clean Code: A Handbook of Agile Software Craftsmanship"
