---
title: "命名的藝術：讓程式碼說故事"
date: 2026-01-20
description: "透過命名降低認知負擔，讓程式碼像故事一樣易讀"
weight: 2
---

# 命名的藝術：讓程式碼說故事

## 程式碼是一個故事

好的程式碼讀起來應該像一個故事，有主角（變數）、有動作（函式）、有情節（流程）。

### "someone bring something to do what"

想像你在描述一個場景：

> 「使用者提交表單，系統驗證資料，然後儲存到資料庫」

這就是一個故事。好的程式碼應該能像這樣被閱讀：

```python
# 可以像故事一樣閱讀的程式碼
user_submitted_form = receive_form_submission(request)
validated_data = validate_form_data(user_submitted_form)
save_to_database(validated_data)
```

而不是：

```python
# 需要解謎的程式碼
d = get(r)
v = check(d)
save(v)
```

### "something transfer to some what"

另一種敘事模式是描述資料的轉換：

> 「原始輸入轉換成清理過的格式，再轉換成最終輸出」

```python
# 轉換敘事
raw_input = read_user_input()
cleaned_input = sanitize(raw_input)
formatted_output = format_for_display(cleaned_input)
```

### 讀者應該能像讀故事一樣理解程式碼

如果讀者需要：
- 往回翻看變數定義
- 查閱文件理解函式功能
- 猜測縮寫的含義

那就不是好的故事。好的故事讓讀者自然地跟著情節走。

## 變數命名的藝術

### 壞名稱的特徵

```python
# 壞：過於簡短，無法理解
d = get_data()
t = time.time()
r = []
i = 0

# 壞：過於通用，無法區分
data = get_user_data()
data2 = get_order_data()
temp = process(data)
result = combine(temp, data2)

# 壞：誤導性的名稱
user_list = get_user()  # 實際上回傳單一用戶，不是列表！
```

### 好名稱的特徵

```python
# 好：說明「這是什麼」
user_profile = get_user_profile(user_id)
current_timestamp = time.time()
validated_items = []
item_index = 0

# 好：能區分不同用途
user_data = get_user_data()
order_data = get_order_data()
merged_report = merge_user_and_orders(user_data, order_data)

# 好：名稱和實際內容一致
active_user = get_active_user()  # 單數名稱，回傳單一用戶
active_users = get_active_users()  # 複數名稱，回傳列表
```

### 命名原則：說明「這是什麼」，不是「怎麼來的」

```python
# 不好：名稱說明來源
config_from_yaml = load_config()
user_after_validation = validate(user)

# 好：名稱說明內容
app_config = load_config()
valid_user = validate(user)
```

### 布林變數的命名

布林變數應該讀起來像一個問句的答案：

```python
# 不好：不清楚是什麼意思
user_status = True
file_check = False

# 好：讀起來像問句的答案
is_user_active = True      # "Is user active?" - Yes
has_valid_license = False  # "Has valid license?" - No
can_edit_document = True   # "Can edit document?" - Yes
should_retry = False       # "Should retry?" - No
```

### 集合類型的命名

```python
# 不好：不清楚是單一還是多個
user = get_all_users()  # 回傳列表，但名稱是單數
user_list = get_user()  # 回傳單一用戶，但名稱暗示列表

# 好：名稱反映結構
users = get_all_users()           # 複數 = 列表
user = get_user(user_id)          # 單數 = 單一物件
user_ids = get_all_user_ids()     # 複數 + 型別提示
user_id_to_name = build_user_map()  # 說明映射關係
```

## 函式命名的藝術

### 壞名稱的特徵

```python
# 壞：動詞太模糊
def process(data):
    pass

def handle(request):
    pass

def do_something(item):
    pass

def manage_users():
    pass

# 壞：不清楚會做什麼
def user_operation(user, action):
    pass

def data_stuff(d):
    pass
```

### 好名稱的特徵

```python
# 好：清楚說明動作和目標
def validate_user_input(user_input: str) -> ValidationResult:
    pass

def extract_branch_name(git_output: str) -> str:
    pass

def format_error_message(error: Exception) -> str:
    pass

def calculate_total_price(items: list[OrderItem]) -> Decimal:
    pass
```

### 命名原則：說明「做什麼」，不是「怎麼做」

```python
# 不好：名稱洩漏實作細節
def loop_through_and_sum(numbers):
    pass

def use_regex_to_find_emails(text):
    pass

# 好：名稱說明意圖
def calculate_sum(numbers):
    pass

def extract_email_addresses(text):
    pass
```

### 常見動詞模式

| 動詞 | 使用場景 | 範例 |
|------|---------|------|
| `get` | 取得現有的值 | `get_user_name()` |
| `set` | 設定值 | `set_user_name()` |
| `create` | 建立新物件 | `create_user()` |
| `build` | 組裝複雜物件 | `build_report()` |
| `calculate` | 計算數值 | `calculate_total()` |
| `validate` | 驗證資料 | `validate_input()` |
| `parse` | 解析文字 | `parse_config()` |
| `format` | 格式化輸出 | `format_date()` |
| `convert` | 轉換型別 | `convert_to_json()` |
| `extract` | 從資料中提取 | `extract_ids()` |
| `filter` | 過濾資料 | `filter_active_users()` |
| `find` | 尋找符合條件的 | `find_user_by_email()` |
| `is/has/can` | 布林判斷 | `is_valid()`, `has_permission()` |

### 對稱命名

相關的函式應該有對稱的命名：

```python
# 好：對稱的命名
def open_connection():
    pass

def close_connection():
    pass

# 好：對稱的命名
def start_processing():
    pass

def stop_processing():
    pass

# 不好：不對稱
def open_connection():
    pass

def disconnect():  # 應該是 close_connection
    pass
```

## 命名與認知負擔的關係

### 好的命名 = 讀者不需要記住前面發生什麼

比較這兩段程式碼：

```python
# 高認知負擔版本
d = fetch()
d = clean(d)
d = transform(d)
r = aggregate(d)
```

讀到最後一行時，你需要記住：
- `d` 一開始是什麼
- `d` 經過了哪些處理
- 現在的 `d` 是什麼狀態

```python
# 低認知負擔版本
raw_data = fetch_user_data()
cleaned_data = remove_invalid_entries(raw_data)
normalized_data = normalize_formats(cleaned_data)
report = generate_summary_report(normalized_data)
```

讀到最後一行時，你只需要知道：
- `normalized_data` 是正規化後的資料
- `generate_summary_report` 會產生報告

你不需要記住前面的處理過程，因為名稱已經告訴你每個變數「是什麼」。

### 認知負擔的量化分析

考慮這個問題：**讀者需要追溯多少步才能理解這個變數？**

```python
# 需要追溯 4 步
x = get_data()      # 第 1 步
x = process(x)      # 第 2 步
x = filter(x)       # 第 3 步
result = format(x)  # 第 4 步：x 到底是什麼？

# 不需要追溯
raw_data = get_data()
processed_data = process(raw_data)
filtered_data = filter(processed_data)
formatted_output = format(filtered_data)  # 直接看名稱就知道是過濾後的資料
```

### 實際案例：Hook 系統

```python
# 重構前（高認知負擔）
def check(p):
    c = open(p).read()
    if c.startswith("#!"):
        l = c.split("\n")
        if len(l) > 1:
            return l[1].startswith("# -*- coding")
    return False

# 重構後（低認知負擔）
def has_valid_python_header(file_path: Path) -> bool:
    """檢查 Python 檔案是否有有效的檔頭"""
    file_content = file_path.read_text()

    has_shebang = file_content.startswith("#!")
    if not has_shebang:
        return False

    lines = file_content.split("\n")
    has_encoding_declaration = (
        len(lines) > 1 and
        lines[1].startswith("# -*- coding")
    )

    return has_encoding_declaration
```

## 命名的自我檢查清單

撰寫程式碼時，對每個名稱問自己：

### 變數命名
- [ ] 名稱是否說明「這是什麼」？
- [ ] 讀者是否能在不看定義的情況下理解？
- [ ] 布林變數是否以 is/has/can/should 開頭？
- [ ] 集合是否使用複數形式？
- [ ] 名稱是否和實際內容一致？

### 函式命名
- [ ] 名稱是否以動詞開頭？
- [ ] 名稱是否說明「做什麼」而非「怎麼做」？
- [ ] 相關函式是否有對稱的命名？
- [ ] 讀者是否能從名稱推測回傳值？
- [ ] 名稱是否符合常見的動詞模式？

### 整體檢查
- [ ] 讀者是否能像讀故事一樣閱讀程式碼？
- [ ] 讀者是否需要往回追溯才能理解？
- [ ] 名稱是否有歧義或誤導性？

## 小結

命名是降低認知負擔最直接的方法。好的命名讓程式碼自己說話，不需要註解、不需要追溯、不需要猜測。

記住這個原則：

> 如果你需要寫註解來解釋一個變數或函式，那可能是名稱不夠好。

讓程式碼說故事，讓讀者輕鬆理解。這就是命名的藝術。

---

## 延伸閱讀

- [認知負擔：程式碼設計的核心目的](../cognitive-load/) - 理解命名為何重要
- [開放封閉原則與認知負擔](../open-closed-principle/) - 命名在架構設計中的角色

---

## 參考資料

- Martin, R. C. (2008). "Clean Code" - Chapter 2: Meaningful Names
- Boswell, D. & Foucher, T. (2011). "The Art of Readable Code"
