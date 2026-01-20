---
title: "模組四：物件導向設計"
description: "Python 的物件導向設計與設計模式"
weight: 4
---

# 模組四：物件導向設計

Python 支援多種程式設計範式，物件導向是其中最重要的一種。本模組介紹 Hook 系統中使用的 OOP 技巧和設計模式。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [4.1](class-design/) | 類別設計原則 | 設計清晰的類別介面 |
| [4.2](abc/) | 抽象基類 ABC | 定義介面契約 |
| [4.3](factory/) | 工廠模式 | 動態建立物件 |
| [4.4](singleton-cache/) | 單例與快取模式 | 控制物件生命週期 |

## 實際範例來源

| 模式 | 範例來源 |
|------|---------|
| 類別設計 | `MarkdownLinkChecker` |
| 抽象基類 | `parsers/base.py` |
| 工廠模式 | `ParserFactory` |
| 快取模式 | `config_loader.py` |

## 設計原則預覽

```python
# 單一職責：每個類別只做一件事
class MarkdownLinkChecker:
    """只負責檢查 Markdown 連結"""
    pass

# 開放封閉：對擴展開放，對修改封閉
class BaseParser(ABC):
    """定義介面，子類別實作細節"""
    @abstractmethod
    def parse(self) -> dict:
        pass
```

## 學習路徑

建議按順序學習：

```
類別設計 → 抽象基類 → 工廠模式 → 單例/快取
```

## 學習時間

預計 60-90 分鐘
