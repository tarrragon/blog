---
title: "monkeypatch（測試期間的替換）"
date: 2026-10-19
description: "用 monkeypatch 或 unittest.mock.patch 替換了函式卻沒有生效、或把模組拆成套件之後原本的替換失效時：替換要對準程式執行時查找的那個名字"
weight: 2
tags: ["python", "knowledge-card", "pytest", "testing", "mock"]
---

monkeypatch 是 pytest 內建的 [fixture](/python/knowledge-cards/pytest-fixture/)：在一個測試執行期間把某個物件上的屬性、某個環境變數或某個字典項目換成別的值，測試結束後自動還原。替換是否生效，取決於換掉的是否就是程式執行時實際去查的那個名字——這條規則同樣適用於 `unittest.mock.patch`，用法見 [Mock 與測試隔離](/python/05-error-testing/mock/)。

## 概念位置

monkeypatch 屬於 [pytest fixture](/python/knowledge-cards/pytest-fixture/) 的一種，責任是暫時改變被測程式的依賴，讓測試不受執行環境影響（時間、網路、哪些程序正在執行）。它改的是名字與物件之間的綁定：`monkeypatch.setattr(模組, "名字", 新值)` 把那個模組命名空間裡的「名字」改綁到新值。綁定在測試結束時還原，所以下一個測試看到的是原本的物件。

## 可觀察訊號與例子

Python 的函式在執行時才去查它用到的名字，查的位置由匯入的寫法決定：

```python
# app/clock.py
def now():
    return "real"

# app/report.py
from app.clock import now     # 在 report 的命名空間建立一個名字 now
from app import clock         # 在 report 的命名空間建立一個名字 clock

def stamp_from_import():
    return now()               # 執行時查 report.now

def stamp_via_module():
    return clock.now()         # 執行時查 report.clock，再查 clock.now
```

```python
from app import clock, report

def test_patch_definition_site(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: "fake")
    assert report.stamp_via_module() == "fake"   # 查的是 clock.now，換到了
    assert report.stamp_from_import() == "real"  # 查的是 report.now，沒換到

def test_patch_lookup_site(monkeypatch):
    monkeypatch.setattr(report, "now", lambda: "fake")
    assert report.stamp_from_import() == "fake"  # 換的正是被查找的名字
```

`from app.clock import now` 在匯入當下把 `report.now` 綁到原本的函式，之後替換 `clock.now` 不會改變 `report.now` 的綁定，所以 `stamp_from_import` 仍然呼叫原本的函式。

`monkeypatch.setattr` 預設 `raising=True`：要替換的名字不存在時直接拋出 `AttributeError`。目標也可以寫成字串，例如 `monkeypatch.setattr("app.report.now", ...)`。

**拆模組時最容易違反這條規則。** 一個模組改成同名套件之後，函式搬進子模組，它查找依賴的位置也跟著搬進那個子模組；原本對準舊模組的替換，在舊模組仍匯入那個名字時（例如為了相容而重新匯出）執行成功、不報錯，只是不再影響被測的函式，測試因此依執行環境而時好時壞；舊模組已經沒有那個名字時，`raising=True` 讓它直接報錯。拆分時的處理方式在[拆分 Python 模組](/python/07-refactoring/python-module-split/)的〈用 pytest 寫特徵測試鎖住拆分前的行為〉。

## 設計責任

寫替換之前先找出被測函式查找依賴的那一行：它寫的是 `now()` 就替換被測函式所在模組的 `now`，寫的是 `clock.now()` 就替換 `clock` 模組的 `now`。程式碼搬家之後，替換目標跟著被測函式走，不跟著依賴的定義走。替換生效與否沒有任何錯誤訊息可以提示，所以替換之後加一條斷言確認被測函式拿到的是替換的值，比事後追查時好時壞的測試便宜。
