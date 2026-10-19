---
title: "pytest fixture（測試夾具）"
date: 2026-10-19
description: "讀到測試函式的參數沒有任何呼叫端傳入、或要讓多個測試共用準備與清理步驟時：pytest 用參數名稱找出 fixture、在測試前後執行準備與清理"
weight: 1
tags: ["python", "knowledge-card", "pytest", "testing"]
---

pytest fixture 是 pytest 在測試執行前替它準備好的資源：一個加上 `@pytest.fixture` 的函式，測試函式只要把它的名字寫成參數，pytest 就會先執行它、把回傳值傳進測試。fixture 用 `yield` 交出資源時，`yield` 之後的程式碼會在測試結束後執行，負責清理。pytest 內建的 fixture 裡最常用來替換依賴的是 [monkeypatch](/python/knowledge-cards/monkeypatch/)。

## 概念位置

fixture 承擔的是測試的準備與清理，與測試本身的斷言分開。unittest 用 `setUp` 與 `tearDown` 方法做同一件事，綁在測試類別上；pytest 的 fixture 是獨立的函式，由參數名稱宣告依賴，所以同一個 fixture 可以被不同檔案的測試共用（放在 `conftest.py`），也可以依賴別的 fixture。pytest 內建一組 fixture：`tmp_path` 給一個每次測試都不同的暫存目錄，`capsys` 擷取寫到標準輸出與標準錯誤的內容，[monkeypatch](/python/knowledge-cards/monkeypatch/) 在測試期間替換屬性、環境變數與字典項目，測試結束後還原。

## 可觀察訊號與例子

```python
import pytest

@pytest.fixture
def config_file(tmp_path):
    # tmp_path 是 pytest 內建的 fixture，這個 fixture 依賴它
    path = tmp_path / "config.toml"
    path.write_text("mode = 'test'\n")
    yield path
    # yield 之後的程式碼在使用它的測試結束後執行
    print("清理", path)

def test_reads_mode(config_file):
    # 參數名 config_file 對到上面的 fixture，沒有任何呼叫端傳入它
    assert "test" in config_file.read_text()
```

讀別人的測試時，參數名稱沒有任何呼叫端傳入，就是 fixture；它的定義在同一個檔案、同一目錄或上層目錄的 `conftest.py`，或是 pytest 內建的。`pytest --fixtures` 會列出目前可用的全部 fixture 與它們定義的位置。

`@pytest.fixture(autouse=True)` 讓同一個檔案（或同一個 `conftest.py` 涵蓋範圍）的每個測試都自動使用這個 fixture，不必寫成參數。它適合每個測試都要的固定設定，例如把一個取決於執行環境的函式替換成固定的結果；代價是讀單一測試時看不到它，要回頭找 fixture 的定義。

## 設計責任

fixture 的設計責任是讓每個測試拿到的資源與其他測試隔離：預設的 `scope="function"` 讓每個測試各自執行一次準備與清理，一個測試對資源的修改不會流到下一個測試。把 scope 放寬成 `module` 或 `session` 可以省下昂貴的準備（例如啟動一個資料庫），條件是測試不修改那份資源；會修改的話，測試結果會隨執行順序改變。
