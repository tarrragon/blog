---
title: "3.5.6 軟體設計的取捨藝術"
date: 2026-03-04
description: "從業界經驗學習取捨決策框架：DRY vs 重複、效能 vs 可讀性、Build vs Buy、技術債務管理"
weight: 6
---


前五章介紹了泛型、異常設計、上下文管理、插件系統等進階設計模式。但在真實專案中，最困難的往往不是「如何實作」，而是「該不該這樣做」。本章從英文技術社群的經驗中提煉出實用的取捨決策框架，幫助你在面對兩難時做出更好的判斷。

## 先備知識

- 本模組 3.5.1-3.5.5 所有章節
- 入門系列 [模組四：物件導向設計](../../python/04-oop/)

---

## 為什麼取捨不可避免？

Stack Overflow 的技術部落格曾發表一篇文章 [Plan for Tradeoffs](https://stackoverflow.blog/2022/01/17/plan-for-tradeoffs-you-cant-optimize-all-software-quality-attributes/)，核心論點是：**你無法同時最佳化所有軟體品質屬性**。

該文列出了 17 項核心品質屬性，包含可用性、效能、安全性、可維護性、可移植性等。它們之間存在天然的衝突：

- **安全性 vs 易用性**：多因素驗證提高了安全性，但增加了使用步驟
- **可重用性 vs 效率**：泛用型元件的效能不如針對特定場景最佳化的程式碼
- **效能 vs 可移植性**：平台特定的最佳化降低了跨平台能力

這不是工程師能力不足的問題，而是軟體開發的數學本質。每個設計決策都在一個多維空間中選擇一個點，不可能讓每個維度都處於最佳值。

### Python 的哲學立場

Python 的設計者 Tim Peters 在 [PEP 20 -- The Zen of Python](https://peps.python.org/pep-0020/) 中早已預見了這個問題，其中幾條格言直接反映了取捨思維：

```text
Simple is better than complex.
Complex is better than complicated.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
```

「Although practicality beats purity」（務實勝於純粹）是整個 Python 設計哲學的關鍵。它承認完美方案不存在，鼓勵工程師在原則和現實之間找到平衡。

---

## 六個核心取捨維度

從業界經驗中，我們可以歸納出六個最常見的取捨維度。

### 維度一：重複 vs 錯誤抽象

這是軟體設計中最經典的取捨之一，近年來因為 [Sandi Metz 的 "The Wrong Abstraction"](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction) 和 [Kent C. Dodds 的 AHA Programming](https://kentcdodds.com/blog/aha-programming) 而被重新審視。

**傳統觀點 -- DRY（Don't Repeat Yourself）**

> "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."

DRY 原則要求消除所有重複。這在很多情況下是正確的，但當它成為教條時，工程師會為了消除表面上的重複而建立過度複雜的抽象。

**反思觀點 -- AHA（Avoid Hasty Abstractions）**

Kent C. Dodds 提出了 AHA 程式設計的概念：**不要急於抽象，等到模式自然浮現**。核心洞察是：

- 重複的程式碼容易在之後重構
- 但錯誤的抽象拆除起來痛苦得多

Sandi Metz 的名言精準地總結了這個觀點：

> "Duplication is far cheaper than the wrong abstraction."
>
> （重複的成本遠低於錯誤抽象的成本。）

**錯誤抽象的演化過程**

Metz 描述了一個在真實專案中反覆出現的模式：

1. 工程師發現兩段重複程式碼，提取出抽象
2. 新需求出現，幾乎但不完全符合現有抽象
3. 後繼者加入參數和條件分支來適應新需求
4. 更多變體出現，更多條件被加入
5. 抽象變得難以理解，但沒人敢重寫（沉沒成本謬誤）
6. 所有人都害怕這段程式碼

**Python 實際案例**

```python
# 階段 1：發現重複，提取函式
def process_user_data(data: dict) -> dict:
    """最初只處理使用者資料"""
    validated = validate_fields(data)
    normalized = normalize_strings(validated)
    return save_to_db(normalized)


# 階段 2：「訂單資料也差不多嘛」，加入參數
def process_data(data: dict, data_type: str = "user") -> dict:
    validated = validate_fields(data)
    normalized = normalize_strings(validated)
    if data_type == "order":
        normalized = calculate_totals(normalized)
    return save_to_db(normalized)


# 階段 3：更多類型，更多分支
def process_data(
    data: dict,
    data_type: str = "user",
    skip_validation: bool = False,
    custom_normalizer: Callable | None = None,
    dry_run: bool = False,
) -> dict:
    if not skip_validation:
        validated = validate_fields(data, strict=(data_type == "payment"))
    else:
        validated = data

    if custom_normalizer:
        normalized = custom_normalizer(validated)
    else:
        normalized = normalize_strings(validated)

    if data_type == "order":
        normalized = calculate_totals(normalized)
    elif data_type == "payment":
        normalized = encrypt_sensitive(normalized)
    elif data_type == "inventory":
        normalized = check_stock_levels(normalized)

    if dry_run:
        return normalized
    return save_to_db(normalized, table=TABLE_MAP[data_type])
```

到了階段 3，這個函式已經違反了單一職責原則，而且任何修改都可能影響所有資料類型的處理。

**更好的做法：讓每個資料類型擁有自己的處理流程**

```python
from abc import ABC, abstractmethod


class DataProcessor(ABC):
    """定義處理流程的骨架，但不強制共用邏輯"""

    @abstractmethod
    def validate(self, data: dict) -> dict: ...

    @abstractmethod
    def normalize(self, data: dict) -> dict: ...

    @abstractmethod
    def save(self, data: dict) -> dict: ...

    def process(self, data: dict) -> dict:
        validated = self.validate(data)
        normalized = self.normalize(validated)
        return self.save(normalized)


class UserDataProcessor(DataProcessor):
    def validate(self, data: dict) -> dict:
        return validate_fields(data)

    def normalize(self, data: dict) -> dict:
        return normalize_strings(data)

    def save(self, data: dict) -> dict:
        return save_to_db(data, table="users")


class PaymentDataProcessor(DataProcessor):
    def validate(self, data: dict) -> dict:
        return validate_fields(data, strict=True)

    def normalize(self, data: dict) -> dict:
        normalized = normalize_strings(data)
        return encrypt_sensitive(normalized)

    def save(self, data: dict) -> dict:
        return save_to_db(data, table="payments")
```

注意：`UserDataProcessor` 和 `PaymentDataProcessor` 的 `validate` 方法有些重複（都呼叫 `validate_fields`），但這是**可接受的重複**。每個處理器獨立演化，不會因為支付系統的新需求而影響用戶資料的處理。

**決策指引**

| 情境                                     | 建議                                     |
| ---------------------------------------- | ---------------------------------------- |
| 兩段程式碼目前看起來一樣                 | 先保持重複，觀察是否真的有共同的演化方向 |
| 三處以上相同且穩定不變                   | 提取抽象，但保持介面簡單                 |
| 現有抽象開始出現 `if type == ...`        | 考慮拆回獨立實作                         |
| 修改一處總是需要同時修改抽象的其他使用者 | 抽象方向錯了，回到重複再重新評估         |

### 維度二：效能 vs 可讀性

Python 社群有一句話經常被引用：

> "Premature optimization is the root of all evil." -- Donald Knuth

但完整的引用其實是：

> "We should forget about small efficiencies, say about 97% of the time: premature optimization is the root of all evil. **Yet we should not pass up our opportunities in that critical 3%.**"

這段話包含了兩個同樣重要的訊息：**97% 的時候不要優化**，但**那關鍵的 3% 不能錯過**。

**Python 的定位**

Python 的設計選擇（動態型別、簡潔語法、豐富的標準庫）大幅降低了開發時間。Dev.to 上的一篇分析指出，效能不僅用 CPU 週期衡量，也用 [time-to-solution](https://dev.to/grenishrai/why-developers-still-choose-python-even-if-its-slow-2hlc) 衡量。程式碼可能在 0.5 秒內執行完畢，但如果需要三天來撰寫和除錯，你損失的生產力可能超過執行速度帶來的收益。

**Python 中效能與可讀性的典型衝突**

```python
# 可讀版本：清楚表達意圖
def find_active_premium_users(users: list[User]) -> list[User]:
    """找出活躍的付費用戶"""
    active_users = [u for u in users if u.is_active]
    premium_users = [u for u in active_users if u.plan == "premium"]
    recent_users = [u for u in premium_users if u.last_login > cutoff_date]
    return recent_users


# 效能版本：單次遍歷，但意圖較不明顯
def find_active_premium_users(users: list[User]) -> list[User]:
    """找出活躍的付費用戶"""
    return [
        u for u in users
        if u.is_active
        and u.plan == "premium"
        and u.last_login > cutoff_date
    ]


# 極致效能版本：犧牲可讀性
def find_active_premium_users(users: list[User]) -> list[User]:
    _is = True.__eq__  # 避免屬性查找
    _pr = "premium".__eq__
    _dt = cutoff_date
    return [u for u in users if _is(u.is_active) and _pr(u.plan) and u.last_login > _dt]
```

在這個例子中，第一個版本建立了三個中間列表，但最清楚；第二個版本是合理的平衡；第三個版本的微優化在 99% 的場景中毫無意義，卻犧牲了所有可讀性。

**決策框架：何時該優化？**

```python
# 決策流程（虛擬碼）
def should_optimize(code_section) -> str:
    # 步驟 1：有實際效能問題嗎？
    if not is_performance_bottleneck(code_section):
        return "維持可讀版本"

    # 步驟 2：瓶頸在這裡嗎？
    profiling_result = profile(code_section)
    if profiling_result.time_percentage < 5:
        return "瓶頸不在這裡，維持可讀版本"

    # 步驟 3：有不犧牲可讀性的優化方案嗎？
    if can_use_better_algorithm():
        return "換演算法（通常不影響可讀性）"

    if can_use_better_data_structure():
        return "換資料結構（通常不影響可讀性）"

    # 步驟 4：真的需要犧牲可讀性
    return "優化，但加上詳細註解說明為什麼"
```

**資料結構選擇的隱性取捨**

```python
# 場景：頻繁的成員檢查

# list -- O(n) 查找，但保留順序、允許重複
users_list: list[str] = ["alice", "bob", "charlie"]
if "alice" in users_list:  # 線性掃描
    pass

# set -- O(1) 查找，但不保留順序、不允許重複
users_set: set[str] = {"alice", "bob", "charlie"}
if "alice" in users_set:  # 雜湊查找
    pass

# 取捨考量：
# - 集合 < 100 個元素：差異可忽略，選擇語義更清楚的
# - 集合 > 10000 個元素且頻繁查找：set 是明確的選擇
# - 需要保留順序 + 快速查找：dict.fromkeys() 或 OrderedDict
```

### 維度三：Build vs Buy

這是影響範圍最大的取捨之一。Antoine Sauvinet 在 [Build vs Buy in 2026](https://oinant.com/en/posts/2026-01-05-build-vs-buy-2026/) 中指出，67% 的軟體專案失敗源於錯誤的 build vs buy 決策（引用 Forrester 研究）。

**核心判斷原則：這是你的競爭優勢嗎？**

> 如果你正在建造的東西能在市場上區隔你和競爭者，那值得自建。否則，不要重新發明輪子。

這個原則被稱為 NIH 症候群（Not Invented Here Syndrome）的解藥。一篇分析 [Hacker News 上的 build vs buy 失敗經驗](https://news.ycombinator.com/item?id=34163624) 後發現，最常見的錯誤是：

- 低估了維護自建方案的長期成本
- 高估了「我們的需求很特殊」的程度
- 忽略了開源社群數百位貢獻者的累積優勢

**Python 生態系統的案例**

```python
# 反面案例：自建 HTTP 請求函式庫
# 「我們只需要 GET 和 POST，寫一個很簡單」
import socket

def simple_get(url: str) -> str:
    # 解析 URL、建立 socket、處理 SSL、
    # 處理重導向、處理分塊傳輸、處理超時...
    # 三個月後，你重新實作了 requests 的 30%
    # 但缺少了 cookie 管理、連接池、代理支援...
    pass

# 正確做法：用 requests 或 httpx
import httpx

response = httpx.get("https://api.example.com/data")
```

```python
# 合理的自建案例：核心業務邏輯的定價引擎
# 這是你的競爭優勢，沒有通用方案能完全符合
class PricingEngine:
    """公司專有的定價策略，包含多年的業務經驗"""

    def calculate(self, product: Product, customer: Customer) -> Price:
        base = self._base_price(product)
        adjusted = self._apply_customer_tier(base, customer)
        seasonal = self._seasonal_adjustment(adjusted)
        return self._apply_regulatory_constraints(seasonal)
```

**決策矩陣**

| 因素       | 傾向自建                    | 傾向採用                |
| ---------- | --------------------------- | ----------------------- |
| 核心競爭力 | 是你的差異化所在            | 是基礎設施              |
| 團隊能力   | 有相關領域專家              | 需要從零學習            |
| 維護預算   | 有長期維護資源              | 只需要「能用就好」      |
| 特殊需求   | 市面方案無法滿足 > 70% 需求 | 市面方案滿足 > 80% 需求 |
| 時間壓力   | 可以投入 3+ 個月            | 需要在數週內交付        |

### 維度四：快速失敗 vs 預先驗證

**Fail Fast 原則**

DZone 上的文章 [The Fail-Fast Principle in Software Development](https://dzone.com/articles/fail-fast-principle-in-software-development) 指出：fail-fast 系統在遇到非預期狀態時立即停止，而不是嘗試繼續執行可能產生不正確結果的操作。

Enterprise Craftsmanship 的部落格進一步說明：因為 fail-fast 程式碼在第一時間就失敗了，回報的錯誤或例外通常非常接近實際的根因，大幅減少了除錯時間。

**Python 中的 Fail Fast**

```python
# Fail Fast 風格：立即驗證，立即失敗
def transfer_money(from_account: str, to_account: str, amount: Decimal) -> None:
    if amount <= 0:
        raise ValueError(f"轉帳金額必須為正數，收到: {amount}")
    if from_account == to_account:
        raise ValueError("不能轉帳給自己")
    # ... 執行轉帳
```

```python
# 預先驗證風格：收集所有錯誤後一次回報
def transfer_money(from_account: str, to_account: str, amount: Decimal) -> None:
    errors: list[str] = []
    if amount <= 0:
        errors.append(f"轉帳金額必須為正數，收到: {amount}")
    if from_account == to_account:
        errors.append("不能轉帳給自己")
    if not account_exists(from_account):
        errors.append(f"來源帳戶不存在: {from_account}")
    if not account_exists(to_account):
        errors.append(f"目標帳戶不存在: {to_account}")

    if errors:
        raise ValidationError(errors)
    # ... 執行轉帳
```

**何時用哪種？**

| 場景         | 建議策略         | 理由                        |
| ------------ | ---------------- | --------------------------- |
| 程式內部邏輯 | Fail Fast        | 不應該出現的狀態要立即暴露  |
| API 請求驗證 | 預先驗證         | 使用者需要一次看到所有錯誤  |
| 資料管線     | Fail Fast + 重試 | 單筆失敗不應阻塞整個管線    |
| 表單提交     | 預先驗證         | UX 考量：使用者不想重複提交 |
| 系統啟動     | Fail Fast        | 配置錯誤要在啟動時就發現    |

**Python 的 assert 是 Fail Fast 的工具（但有限制）**

```python
def process_batch(items: list[Item]) -> list[Result]:
    # assert 適合標記「這裡不應該發生」的情況
    assert items, "process_batch 不應該收到空列表"

    # 但注意：python -O 會移除所有 assert
    # 所以不要用 assert 做業務驗證
    # 以下是錯誤用法：
    assert user.is_authenticated, "使用者未登入"  # 不要這樣做
```

### 維度五：嚴格型別 vs 靈活鴨子型別

Python 同時支援靜態型別提示和動態鴨子型別，這在其他語言中比較少見。

```python
from typing import Protocol


# 方案 A：嚴格的型別定義
class Serializable(Protocol):
    def to_dict(self) -> dict: ...
    def from_dict(cls, data: dict) -> "Serializable": ...


def save_strict(obj: Serializable) -> None:
    data = obj.to_dict()
    # ... 儲存


# 方案 B：鴨子型別，依賴約定
def save_flexible(obj: object) -> None:
    if not hasattr(obj, "to_dict"):
        raise TypeError(f"{type(obj).__name__} 缺少 to_dict 方法")
    data = obj.to_dict()  # type: ignore
    # ... 儲存


# 方案 C：Protocol 的平衡點（推薦）
# Protocol 提供靜態檢查，但不要求繼承
class Persistable(Protocol):
    def to_dict(self) -> dict: ...


def save_balanced(obj: Persistable) -> None:
    data = obj.to_dict()
    # ... 儲存


# 任何有 to_dict 方法的類別都自動滿足 Persistable
# 不需要顯式繼承，保留了鴨子型別的靈活性
class User:
    def to_dict(self) -> dict:
        return {"name": self.name}


save_balanced(User())  # mypy 檢查通過，無需繼承
```

**決策指引**

| 專案特性       | 建議                       |
| -------------- | -------------------------- |
| 團隊 > 5 人    | 傾向嚴格型別，降低溝通成本 |
| 快速原型       | 鴨子型別，快速迭代         |
| 長期維護的框架 | Protocol（平衡點）         |
| 資料管線/ETL   | 嚴格型別，錯誤代價高       |
| 個人腳本       | 鴨子型別，效率優先         |

### 維度六：技術債務的策略性管理

Oskar Dudycz 在 Architecture Weekly 上發表了一篇引人深思的文章 [Tech Debt Doesn't Exist, But Trade-offs Do](https://www.architecture-weekly.com/p/tech-debt-doesnt-exist-but-trade)。他認為「技術債務」這個標籤讓我們可以承認問題的存在而不去解決它。他主張用「取捨」取代「債務」的思維：

> 說「我們有技術債」是一種藉口。真正的問題是：「我們當時做了什麼取捨，現在的代價是什麼？」

**策略性技術債務 vs 魯莽的技術債務**

```python
# 策略性技術債務：有意識地選擇，有計畫地償還
# 場景：MVP 需要在兩週內上線驗證市場

# 目前的實作：直接用 JSON 檔案儲存
# 取捨決策：放棄資料庫，節省 3 天開發時間
# 償還計畫：驗證成功後第二個 sprint 遷移到 PostgreSQL
import json
from pathlib import Path

# TRADE-OFF: 使用 JSON 檔案而非資料庫
# 原因: MVP 階段，使用者 < 100 人，讀寫頻率低
# 風險: 無並行安全、無交易支援、效能隨資料量線性下降
# 償還條件: 使用者 > 50 或資料 > 10MB 時遷移
DATA_FILE = Path("data/users.json")

def save_user(user: dict) -> None:
    data = json.loads(DATA_FILE.read_text()) if DATA_FILE.exists() else []
    data.append(user)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

```python
# 魯莽的技術債務：沒有意識到代價
# 場景：「先讓它動起來再說」
def handle_request(req):
    try:
        # 100 行沒有型別提示、沒有錯誤處理、沒有測試的程式碼
        data = req["data"]  # 可能是 None
        result = process(data)  # process 可能拋出任何異常
        db.save(result)  # 沒有交易管理
        return {"ok": True}
    except:  # 裸 except：吞掉所有錯誤
        return {"ok": False}
```

**關鍵區別**：策略性債務是有意識的取捨，附帶償還計畫和觸發條件。魯莽的債務是無意識的品質下降。

---

## 決策框架：面對取捨的系統性方法

綜合上述六個維度的經驗，以下是一個通用的取捨決策框架。

### 三步決策法

**步驟一：辨識取捨的存在**

很多時候，工程師沒有意識到自己正在做取捨。以下信號表明你正面對一個取捨決策：

- 「兩種做法各有優缺點」
- 「如果我們選 A，就會失去 B」
- 團隊成員對同一個問題有不同偏好
- 解決方案中出現了 "it depends"

**步驟二：量化代價**

不要用直覺判斷，盡量量化每個選項的代價：

```python
# 取捨評估模板
class TradeoffEvaluation:
    """用結構化方式記錄取捨決策"""

    def __init__(self, decision: str):
        self.decision = decision
        self.options: list[dict] = []

    def add_option(
        self,
        name: str,
        benefits: list[str],
        costs: list[str],
        risks: list[str],
        reversibility: str,  # "easy" | "moderate" | "difficult"
    ) -> None:
        self.options.append({
            "name": name,
            "benefits": benefits,
            "costs": costs,
            "risks": risks,
            "reversibility": reversibility,
        })

    def evaluate(self) -> str:
        """產出決策摘要"""
        lines = [f"## 決策: {self.decision}\n"]
        for opt in self.options:
            lines.append(f"### 方案: {opt['name']}")
            lines.append(f"- 可逆性: {opt['reversibility']}")
            lines.append(f"- 優點: {', '.join(opt['benefits'])}")
            lines.append(f"- 代價: {', '.join(opt['costs'])}")
            lines.append(f"- 風險: {', '.join(opt['risks'])}")
            lines.append("")
        return "\n".join(lines)
```

**步驟三：偏好可逆的決策**

Amazon 的 Jeff Bezos 將決策分為兩類：

- **Type 1 決策**（單向門）：不可逆，需要深思熟慮。例如選擇程式語言、資料庫架構。
- **Type 2 決策**（雙向門）：可逆，應該快速做出。例如 API 命名、函式拆分方式。

```python
# Type 2 決策：函式簽名可以之後改
# 先用簡單版本，有需要再擴展
def send_notification(user_id: str, message: str) -> bool:
    """現在只支援 email，之後可以擴展"""
    return send_email(user_id, message)

# 之後需要時再擴展，改動成本很低
def send_notification(
    user_id: str,
    message: str,
    channel: str = "email",
) -> bool:
    """支援多種通知管道"""
    sender = CHANNEL_MAP[channel]
    return sender(user_id, message)
```

```python
# Type 1 決策：資料庫 schema 設計
# 上線後很難改，需要仔細評估

# 決策記錄（Architecture Decision Record）
# ADR-007: 使用者地址儲存方式
#
# 狀態: 已採納
# 日期: 2026-03-01
#
# 背景:
#   使用者可能有多個地址（家、公司、寄送地址）
#
# 考慮的方案:
#   A. JSON 欄位：靈活但難以查詢和索引
#   B. 獨立 address 表：標準化但查詢需要 JOIN
#   C. 嵌入式欄位（home_addr, work_addr）：簡單但不可擴展
#
# 決策: 方案 B（獨立表）
# 理由: 地址需要獨立查詢（物流系統需求），
#        且未來可能增加地址類型
```

### 可逆性評估表

| 決策類型      | 可逆性           | 建議決策速度 |
| ------------- | ---------------- | ------------ |
| 變數/函式命名 | 高（全域替換）   | 秒級         |
| 模組拆分方式  | 中（需要重構）   | 分鐘級       |
| API 介面設計  | 低（外部依賴）   | 小時級       |
| 資料庫 schema | 很低（資料遷移） | 天級         |
| 程式語言選擇  | 極低（全部重寫） | 週級         |

---

## 經典案例研究

### 案例一：Food-Tech 新創的技術債務危機

一家 Food-Tech 新創公司在六個月內推出了 MVP，快速獲得了數千名用戶和可觀的投資。但開發團隊為了搶市場，犧牲了文件、測試和可擴展的架構。

一次特別糟糕的產品發布導致了嚴重的停機和大量客戶投訴。CTO 終於意識到，短期搶快的收益已經被長期的不穩定和效率低下所抵消。

**教訓**：這是一個策略性債務失控的例子。初始的取捨（速度優先）是合理的，但缺少了「償還計畫」和「觸發條件」。如果團隊在 MVP 驗證成功後立即投入技術債務償還，結果會完全不同。

來源：[Medium - Technical Debt vs. Innovation](https://medium.com/@helal.hamed/technical-debt-vs-innovation-how-to-manage-trade-offs-in-startups-and-scale-ups-d00abd8add4a)

### 案例二：可觀測性的成本爆炸

[Honeycomb 的工程部落格](https://www.honeycomb.io/blog/cost-crisis-observability-tooling)描述了可觀測性工具面臨的成本危機：微服務架構產生的日誌、指標和追蹤資料量呈指數成長，但大部分資料從未被查看。

典型的取捨是取樣率：10% 的取樣可以大幅降低成本，但可能錯過關鍵的請求。

**業界的解決方案**：

```python
# 概念示意：基於重要性的取樣策略
import random

# 不是所有請求都值得完整記錄
SAMPLING_RULES = {
    "health_check": 0.001,    # 0.1% -- 幾乎不需要
    "static_asset": 0.01,     # 1% -- 很少出問題
    "api_read": 0.1,          # 10% -- 標準取樣
    "api_write": 0.5,         # 50% -- 寫入操作更重要
    "payment": 1.0,           # 100% -- 永遠完整記錄
    "error": 1.0,             # 100% -- 錯誤永遠記錄
}


def should_sample(request_type: str) -> bool:
    rate = SAMPLING_RULES.get(request_type, 0.1)
    return random.random() < rate
```

來源：[Honeycomb - The Cost Crisis in Observability Tooling](https://www.honeycomb.io/blog/cost-crisis-observability-tooling)

### 案例三：B2B 企業的 4 億美元技術債

McKinsey 報導了一家大型 B2B 企業的案例：他們識別出了數十個現代化計畫，可以帶來 20 億美元的利潤提升，但其中 70% 的計畫依賴的技術需要 4 億美元的投入來償還多年累積的技術債務。

**教訓**：技術債務的成本不是線性的。每一次「之後再處理」都會增加下一次修改的難度。當債務累積到一定程度，甚至連修改的機會成本都變成天文數字。

來源：[McKinsey - Breaking Technical Debt's Vicious Cycle](https://mckinsey.com/capabilities/mckinsey-digital/our-insights/breaking-technical-debts-vicious-cycle-to-modernize-your-business)

---

## Python 特有的取捨考量

### "There should be one obvious way to do it" vs 現實

The Zen of Python 說：

```text
There should be one-- and preferably only one --obvious way to do it.
```

但在實際的 Python 開發中，你經常面對多種方案的選擇：

```python
# 格式化字串：三種方式
name = "World"

# % 格式化（最老，但 logging 模組仍在用）
message = "Hello, %s" % name

# str.format()（Python 2.6+，某些場景更靈活）
message = "Hello, {}".format(name)

# f-string（Python 3.6+，通常是最佳選擇）
message = f"Hello, {name}"
```

```python
# 合併字典：多種方式
dict_a = {"a": 1}
dict_b = {"b": 2}

# 方式 1：update（原地修改）
merged = dict_a.copy()
merged.update(dict_b)

# 方式 2：解包（Python 3.5+，建立新字典）
merged = {**dict_a, **dict_b}

# 方式 3：聯集運算子（Python 3.9+，最 Pythonic）
merged = dict_a | dict_b
```

**如何選擇？** 優先考慮：

1. **團隊共識** -- 統一比「最佳」更重要
2. **Python 版本相容性** -- 如果要支援 3.8，就不能用 `|`
3. **語境適合度** -- logging 中用 `%` 是慣例，不需要改成 f-string

### 型別提示的漸進策略

```python
# 階段 1：不加型別提示（快速原型）
def process(data):
    return [item["name"] for item in data if item.get("active")]


# 階段 2：關鍵介面加型別提示（公開 API）
def process(data: list[dict[str, Any]]) -> list[str]:
    return [item["name"] for item in data if item.get("active")]


# 階段 3：完整型別定義（長期維護）
from dataclasses import dataclass


@dataclass
class Item:
    name: str
    active: bool = True


def process(data: list[Item]) -> list[str]:
    return [item.name for item in data if item.active]
```

每個階段都是合理的，關鍵在於根據專案的生命週期選擇正確的階段。個人腳本停在階段 1 完全合理；團隊共同維護的服務應該至少在階段 2；核心業務邏輯應該達到階段 3。

### EAFP vs LBYL

Python 社群有兩種錯誤處理哲學：

```python
# LBYL (Look Before You Leap) -- 先檢查再行動
def get_value_lbyl(data: dict, key: str) -> str | None:
    if key in data:
        value = data[key]
        if isinstance(value, str):
            return value
    return None


# EAFP (Easier to Ask Forgiveness than Permission) -- 先嘗試再處理異常
def get_value_eafp(data: dict, key: str) -> str | None:
    try:
        value = data[key]
        if not isinstance(value, str):
            return None
        return value
    except KeyError:
        return None
```

| 因素             | LBYL                       | EAFP               |
| ---------------- | -------------------------- | ------------------ |
| Race condition   | 檢查和使用之間狀態可能改變 | 原子操作，無此問題 |
| 效能（正常路徑） | 額外的檢查開銷             | 無額外開銷         |
| 效能（異常路徑） | 無額外開銷                 | 例外處理有成本     |
| 可讀性           | 意圖明確                   | 需要理解例外流程   |
| Python 慣例      | 較少使用                   | 更 Pythonic        |

**實用建議**：如果異常是真正的「例外情況」（發生率 < 5%），EAFP 通常更好。如果「異常」其實是常見情況（例如字典中 30% 的 key 不存在），LBYL 的效能更好。

---

## 取捨決策清單

面對需要做取捨的設計決策時，依序確認以下項目：

### 決策前

- [ ] 我是否辨識出了取捨的存在？（不是只有一個「正確答案」）
- [ ] 我列出了至少兩個可行方案嗎？
- [ ] 每個方案的優點、代價和風險都有記錄嗎？
- [ ] 這個決策的可逆性如何？（Type 1 還是 Type 2？）
- [ ] 有沒有可以參考的業界經驗或先例？

### 評估中

- [ ] 我是否量化了代價，而不只是用直覺判斷？
- [ ] 我有沒有考慮到**長期**維護成本？
- [ ] 團隊其他成員的意見是什麼？
- [ ] 最壞的情況是什麼？我們能承受嗎？
- [ ] 有沒有第三個方案是我忽略的？

### 決策後

- [ ] 決策理由有記錄嗎？（ADR 或程式碼註解）
- [ ] 取捨的代價有告知相關人員嗎？
- [ ] 如果是策略性技術債務，償還計畫和觸發條件是什麼？
- [ ] 什麼條件下需要重新評估這個決策？

---

## 本章重點整理

**核心觀念**

1. 取捨是軟體工程的本質，不是能力不足的表現
2. 「務實勝於純粹」-- Python 的設計哲學本身就是取捨的產物
3. 錯誤的抽象比重複更昂貴（Sandi Metz）
4. 不要急於抽象，等模式自然浮現（AHA Programming）
5. 優先做可逆的決策，謹慎對待不可逆的決策

**實用原則**

1. 效能優化前先量測，97% 的時候可讀性優先
2. 只有核心競爭力才值得自建
3. 策略性技術債務需要「償還計畫」和「觸發條件」
4. 型別提示的嚴格程度應匹配專案的生命週期
5. 決策理由比決策本身更值得記錄

---

## 延伸閱讀

### 必讀文章

- [The Wrong Abstraction -- Sandi Metz](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction) -- 為什麼錯誤的抽象比重複更昂貴
- [AHA Programming -- Kent C. Dodds](https://kentcdodds.com/blog/aha-programming) -- 不要急於抽象的實踐指南
- [Plan for Tradeoffs -- Stack Overflow Blog](https://stackoverflow.blog/2022/01/17/plan-for-tradeoffs-you-cant-optimize-all-software-quality-attributes/) -- 軟體品質屬性的取捨框架
- [Tech Debt Doesn't Exist, But Trade-offs Do -- Oskar Dudycz](https://www.architecture-weekly.com/p/tech-debt-doesnt-exist-but-trade) -- 重新理解技術債務

### 深入探討

- [Build vs Buy in 2026 -- Antoine Sauvinet](https://oinant.com/en/posts/2026-01-05-build-vs-buy-2026/) -- AI 時代的 build vs buy 決策
- [The Cost Crisis in Observability Tooling -- Honeycomb](https://www.honeycomb.io/blog/cost-crisis-observability-tooling) -- 可觀測性的成本取捨
- [The Fail-Fast Principle -- DZone](https://dzone.com/articles/fail-fast-principle-in-software-development) -- 快速失敗原則的全面介紹
- [Fail Fast Principle -- Enterprise Craftsmanship](https://enterprisecraftsmanship.com/posts/fail-fast-principle/) -- 快速失敗的實務應用

### Python 相關

- [PEP 20 -- The Zen of Python](https://peps.python.org/pep-0020/) -- Python 設計哲學
- [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/) -- Python 風格指南
- [Why Developers Still Choose Python, Even If It's "Slow"](https://dev.to/grenishrai/why-developers-still-choose-python-even-if-its-slow-2hlc) -- Python 速度取捨的分析
- [The Hitchhiker's Guide to Python: Code Style](https://docs.python-guide.org/writing/style/) -- Pythonic 風格指南

---

*上一章：[3.5.5 設計模式整合案例](../integration/)*
*回到模組首頁：[模組 3.5：進階設計模式](../)*
