---
title: "開放封閉原則與認知負擔"
date: 2026-01-20
description: "從認知負擔的視角重新理解 SOLID 原則"
weight: 3
---

# 開放封閉原則與認知負擔

## OCP 的傳統解釋

開放封閉原則（Open-Closed Principle, OCP）是 SOLID 原則之一，傳統定義是：

> 軟體實體（類別、模組、函式）應該對擴展開放，對修改封閉。

這意味著：
- **對擴展開放**：可以增加新功能
- **對修改封閉**：不需要修改現有程式碼

### 傳統焦點：避免修改帶來的風險

傳統觀點認為，OCP 的目的是：
- 避免修改穩定的程式碼引入錯誤
- 減少回歸測試的範圍
- 保護現有功能不受影響

這些都是正確的，但還有一個更深層的目的。

## OCP 的認知負擔視角（用戶觀點）

### 真正目的：讓閱讀者不需要理解整個系統才能使用

從認知負擔的角度來看，OCP 的核心價值是：

> 擴展系統時，開發者只需要理解介面，不需要理解實作。

這大幅降低了認知負擔。

### 範例：違反 OCP 的設計

```python
class ReportGenerator:
    def generate(self, report_type: str, data: dict) -> str:
        if report_type == "pdf":
            # 100 行 PDF 生成邏輯
            return self._generate_pdf(data)
        elif report_type == "excel":
            # 80 行 Excel 生成邏輯
            return self._generate_excel(data)
        elif report_type == "html":
            # 60 行 HTML 生成邏輯
            return self._generate_html(data)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
```

問題：
- 新增格式需要修改這個類別
- 理解新增功能需要閱讀整個類別
- 每種格式的邏輯混在一起

**認知負擔**：要新增 CSV 格式，開發者需要理解整個 `ReportGenerator` 類別的結構，找到正確的位置插入程式碼，並確保不影響其他格式。

### 範例：遵循 OCP 的設計

```python
from abc import ABC, abstractmethod

class ReportFormatter(ABC):
    """報告格式化器的抽象介面"""

    @abstractmethod
    def format(self, data: dict) -> str:
        """將資料格式化為報告"""
        pass

class PdfFormatter(ReportFormatter):
    def format(self, data: dict) -> str:
        # PDF 生成邏輯
        pass

class ExcelFormatter(ReportFormatter):
    def format(self, data: dict) -> str:
        # Excel 生成邏輯
        pass

class HtmlFormatter(ReportFormatter):
    def format(self, data: dict) -> str:
        # HTML 生成邏輯
        pass

class ReportGenerator:
    def __init__(self, formatter: ReportFormatter):
        self._formatter = formatter

    def generate(self, data: dict) -> str:
        return self._formatter.format(data)
```

新增 CSV 格式：

```python
class CsvFormatter(ReportFormatter):
    def format(self, data: dict) -> str:
        # CSV 生成邏輯
        pass

# 使用
generator = ReportGenerator(CsvFormatter())
report = generator.generate(data)
```

**認知負擔**：要新增 CSV 格式，開發者只需要：
1. 理解 `ReportFormatter` 介面（一個方法）
2. 實作 `format` 方法

不需要閱讀 `PdfFormatter`、`ExcelFormatter` 或 `ReportGenerator` 的實作。

### 擴展時只需要理解介面，不需要理解實作

這就是 OCP 降低認知負擔的方式：

| 情境 | 違反 OCP | 遵循 OCP |
|------|---------|---------|
| 新增格式 | 需要理解整個類別 | 只需理解介面 |
| 修改一個格式 | 可能影響其他格式 | 完全隔離 |
| 閱讀程式碼 | 需要跟蹤 if-else 分支 | 直接看對應的類別 |

### 這和命名是同一件事：降低認知負擔

回想[命名的藝術](../naming-art/)：好的命名讓讀者不需要追溯定義就能理解。

OCP 做的是同樣的事，只是在更高的層級：好的設計讓讀者不需要理解整個系統就能擴展。

## 單一職責原則的本質

單一職責原則（Single Responsibility Principle, SRP）是另一個 SOLID 原則：

> 一個類別應該只有一個改變的理由。

### 一次只理解一件事

從認知負擔的角度，SRP 的核心是：

> 讓讀者一次只需要理解一件事。

```python
# 違反 SRP：一個類別做太多事
class UserManager:
    def create_user(self, data):
        # 驗證邏輯
        # 資料庫操作
        # 發送歡迎郵件
        # 記錄日誌
        pass

    def delete_user(self, user_id):
        # 權限檢查
        # 資料庫操作
        # 清理關聯資料
        # 發送通知
        # 記錄日誌
        pass
```

問題：讀者想理解「如何發送歡迎郵件」，卻需要閱讀整個 `UserManager` 類別。

```python
# 遵循 SRP：每個類別只做一件事
class UserValidator:
    def validate(self, data: dict) -> ValidationResult:
        pass

class UserRepository:
    def create(self, user: User) -> User:
        pass

    def delete(self, user_id: str) -> bool:
        pass

class EmailService:
    def send_welcome_email(self, user: User) -> None:
        pass

class UserService:
    def __init__(
        self,
        validator: UserValidator,
        repository: UserRepository,
        email_service: EmailService
    ):
        self._validator = validator
        self._repository = repository
        self._email_service = email_service

    def create_user(self, data: dict) -> User:
        validation = self._validator.validate(data)
        if not validation.is_valid:
            raise ValidationError(validation.errors)

        user = self._repository.create(User.from_dict(data))
        self._email_service.send_welcome_email(user)
        return user
```

現在，讀者想理解「如何發送歡迎郵件」，只需要看 `EmailService`。

### 類別/函式的職責清晰 = 閱讀時認知負擔低

| 職責數量 | 認知負擔 | 維護難度 |
|---------|---------|---------|
| 1 | 低 | 容易 |
| 2-3 | 中 | 需要注意 |
| 4+ | 高 | 危險區域 |

### 和命名的關聯：如果難以命名，可能職責不單一

這是一個非常實用的檢測方法：

```python
# 難以命名 = 職責不單一
class UserStuffManager:  # "stuff" 說明不知道它具體做什麼
    pass

class DataProcessorAndValidator:  # "and" 說明做了兩件事
    pass

class HelperUtils:  # "helper/utils" 說明是雜項收集
    pass

# 容易命名 = 職責單一
class UserAuthenticator:  # 清楚：處理用戶認證
    pass

class ConfigurationLoader:  # 清楚：載入配置
    pass

class EmailFormatter:  # 清楚：格式化郵件
    pass
```

**規則**：如果你無法用一個簡短的名詞描述類別的職責，它可能做了太多事。

## 實際案例

### Hook 系統中的設計決策

讓我們看 Hook 系統中如何應用這些原則：

#### 配置載入器（遵循 SRP）

```python
# .claude/lib/config_loader.py
class ConfigLoader:
    """
    單一職責：載入和快取配置檔案

    不負責：
    - 驗證配置內容
    - 使用配置執行操作
    - 修改配置
    """

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._cache: Optional[dict] = None

    def load(self) -> dict:
        """載入配置，使用快取避免重複讀取"""
        if self._cache is None:
            self._cache = self._read_config()
        return self._cache

    def _read_config(self) -> dict:
        with open(self._config_path) as f:
            return yaml.safe_load(f)
```

#### 解析器工廠（遵循 OCP）

```python
# .claude/lib/parsers/base.py
class LanguageParser(ABC):
    """語言解析器的抽象介面"""

    @abstractmethod
    def parse(self, content: str) -> ParseResult:
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        pass

# .claude/lib/parsers/python_parser.py
class PythonParser(LanguageParser):
    def parse(self, content: str) -> ParseResult:
        # Python 解析邏輯
        pass

    def get_supported_extensions(self) -> list[str]:
        return [".py"]

# .claude/lib/parsers/factory.py
class ParserFactory:
    """
    對擴展開放：新增語言只需實作 LanguageParser
    對修改封閉：不需要修改此工廠類別
    """

    _parsers: dict[str, type[LanguageParser]] = {}

    @classmethod
    def register(cls, parser_class: type[LanguageParser]) -> None:
        for ext in parser_class.get_supported_extensions():
            cls._parsers[ext] = parser_class

    @classmethod
    def get_parser(cls, file_extension: str) -> LanguageParser:
        parser_class = cls._parsers.get(file_extension)
        if parser_class is None:
            raise UnsupportedLanguageError(file_extension)
        return parser_class()
```

新增 Dart 語言支援：

```python
# .claude/lib/parsers/dart_parser.py
class DartParser(LanguageParser):
    def parse(self, content: str) -> ParseResult:
        # Dart 解析邏輯
        pass

    def get_supported_extensions(self) -> list[str]:
        return [".dart"]

# 註冊（可在初始化時自動完成）
ParserFactory.register(DartParser)
```

開發者只需要：
1. 理解 `LanguageParser` 介面
2. 實作兩個方法
3. 註冊解析器

不需要閱讀其他解析器的實作。

### 如何用「降低認知負擔」來判斷設計好壞

面對設計決策時，問自己這些問題：

1. **擴展時**：開發者需要理解多少現有程式碼？
   - 好：只需要理解介面
   - 壞：需要理解整個實作

2. **修改時**：改動會影響多少其他部分？
   - 好：改動是局部的
   - 壞：改動會連鎖反應

3. **閱讀時**：讀者一次需要記住多少概念？
   - 好：一次一個概念
   - 壞：需要同時記住多個概念

## 設計原則檢查清單

### 開放封閉原則

- [ ] 新增功能是否不需要修改現有程式碼？
- [ ] 擴展時是否只需要理解介面？
- [ ] 是否有抽象層隔離變化點？

### 單一職責原則

- [ ] 類別是否只有一個改變的理由？
- [ ] 類別名稱是否能清楚描述其職責？
- [ ] 類別是否小到可以快速理解？

### 認知負擔檢查

- [ ] 讀者是否能在 5 分鐘內理解這個類別？
- [ ] 是否需要閱讀其他類別才能理解這個類別？
- [ ] 修改這個類別是否需要擔心影響其他部分？

## 小結

從認知負擔的視角來看，OCP 和 SRP 的核心目的是：

- **OCP**：讓開發者不需要理解整個系統就能擴展
- **SRP**：讓開發者一次只需要理解一件事

這和命名是同一個哲學：**降低閱讀者的認知負擔**。

當你面對設計決策時，不要問「這是否符合 OCP」，而是問：

> 下一個開發者要擴展這個功能時，需要理解多少現有程式碼？

答案越少，設計越好。

---

## 延伸閱讀

- [認知負擔：程式碼設計的核心目的](../cognitive-load/) - 認知負擔的基本概念
- [命名的藝術：讓程式碼說故事](../naming-art/) - 降低認知負擔的另一種方式
- [抽象基類 ABC](../../04-oop/abc/) - Python 中實現 OCP 的工具

## 延伸閱讀（進階系列）

- [進階設計模式](/python-advanced/03-design-patterns/) - OCP 在複雜系統中的應用
- [插件系統設計](/python-advanced/03-design-patterns/plugin-system/) - 用 OCP 原則建構可擴展架構

---

## 參考資料

- Martin, R. C. (2000). "Design Principles and Design Patterns"
- Martin, R. C. (2017). "Clean Architecture"
- Meyer, B. (1988). "Object-Oriented Software Construction"
