---
title: "TOML"
date: 2026-10-26
description: "讀到 .toml 設定檔、要判斷一個值會被解析成什麼型別、要在 JSON、YAML、TOML 之間選設定檔格式，或解析器版本對不上而報錯時"
weight: 72
tags: ["infra", "knowledge-cards", "toml", "config"]
---

TOML（Tom's Obvious, Minimal Language）是一種給人讀寫的設定檔格式：每一行是 `鍵 = 值`，值的型別由寫法本身決定（字串要加引號、數字與布林值不加），用方括號的表頭把鍵分組，可以寫 `#` 開頭的註解，沒有用縮排表示結構。規格由 toml.io 維護，1.0.0 在 2021 年 1 月發佈，1.1.0 在 2025 年 12 月發佈；Python 的 `pyproject.toml`、Rust 的 `Cargo.toml` 都用這個格式，跟 [HCL](/infra/knowledge-cards/hcl/) 與 [.env](/infra/knowledge-cards/dotenv/) 同樣是描述設定的檔案：比起 HCL，TOML 只描述資料、沒有變數與函式；比起 .env，TOML 有型別、分組與巢狀結構。

## 概念位置

TOML 在設定檔格式裡的位置介於 JSON 與 YAML 之間：跟 JSON 一樣每個值的型別都由寫法明確決定，跟 YAML 一樣可以寫註解、適合人手動編輯。它只描述資料，需要變數、迴圈與條件來描述基礎設施時用的是 [HCL](/infra/knowledge-cards/hcl/) 這類設定語言。它在本站被用來寫主機的維護清單，選它的理由與實測見 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)；Python 打包設定裡的 TOML 用法見 [6.1 pyproject.toml 完整指南](/python-advanced/07-packaging/pyproject-toml/)。

## 可觀察訊號

需要讀懂 TOML 的情境包括：打開一個副檔名是 `.toml` 的設定檔、要判斷某個值會被程式讀成字串還是數字、在 JSON、YAML、TOML 之間選設定檔格式，以及解析器回報 `TOMLDecodeError` 這類錯誤、而同一份檔案在另一台機器上解析得過。

## 設計責任

TOML 的基本結構：

```toml
# 註解
name = "web-demo"          # 字串一定要加引號
port = 443                 # 整數
enabled = true             # 布林值只有 true 與 false
checked_at = 2026-10-26T06:21:00Z   # 有時區的日期時間，解析成帶時區的時間物件

[host]                     # 表格（table）：底下的鍵屬於 host
provider = "oracle-cloud"

[[entrypoint]]             # 表格陣列（array of tables）：每出現一次就新增一筆
port = 443
exposure = "cdn-only"

[[entrypoint]]
port = 22
exposure = "admin-only"
```

- **`[名稱]`**：表格（table），指一組鍵值，等於程式裡的一個物件，跟試算表的格子無關；底下的鍵到下一個表頭為止都屬於它。
- **`[[名稱]]`**：表格陣列，每出現一次就在陣列裡加一筆，適合同一種項目要列很多筆的清單（入口、檢查項目、步驟）。
- **型別由寫法決定**：`"no"` 是字串，不加引號的 `no` 不屬於任何型別，解析器報錯；YAML 1.1 的解析器（例如 PyYAML）把不加引號的 `no` 讀成 `false`（英文資料常稱為 Norway problem）、`010` 讀成 8。寫法剛好屬於另一個型別時，TOML 一樣照那個型別讀：不加引號的 `1.10` 是浮點數 1.1。所以版本號這類看起來像數字的字串要加引號。
- **日期與時間是原生型別**：有時區的日期時間、沒有時區的日期時間、日期、時間各是一種型別，不必用字串存再自己解析。
- **巢狀的表格陣列**：`[[entrypoint.verify]]` 屬於它上面最近的那一筆 `[[entrypoint]]`，讓每一筆項目各有自己的一組子項目。
- **寫在同一行的表格（inline table）**：`verify = { command = "...", expect_stdout = "ok" }`，適合只有幾個欄位的子項目；TOML 1.0 要寫在一行內、結尾不能有逗號。
- **兩種字串**：雙引號的基本字串處理反斜線跳脫（regex 的 `\.` 寫成 `\\.`），單引號的字面字串不處理任何跳脫（寫成 `'\.'`）。
- **數字的分隔**：整數可以用底線分隔位數，`1_073_741_824` 等於 `1073741824`。

跟其他格式的差別：

| 格式 | 註解 | 型別怎麼決定                                 | 結構怎麼表示   | 適合的場景                                   |
| ---- | ---- | -------------------------------------------- | -------------- | -------------------------------------------- |
| JSON | 不能 | 寫法決定，規則嚴格                           | 大括號與中括號 | 程式之間交換資料                             |
| YAML | 能   | 不加引號的值由解析器推測（版本之間規則不同） | 縮排           | 巢狀很深的設定（Kubernetes、CI 的 workflow） |
| TOML | 能   | 寫法決定，不加引號又不是合法值時報錯         | 表頭與表格陣列 | 人手動維護、層數不深的設定與清單             |

**版本對解析器的影響**：1.1.0 新增的語法（寫在同一行的表格 inline table 可以跨行並在結尾加逗號、`\xHH` 與 `\e` 跳脫、時間可以省略秒）只有支援 1.1 的解析器讀得懂。Python 的標準函式庫 `tomllib` 在 3.11 加入時支援 1.0，3.15 起支援 1.1，3.10 以下沒有 `tomllib`、要另裝 `tomli`。同一份用了 1.1 語法的檔案，在 Python 3.15 解析得過，在 3.12 會報錯；版本對不上時的兩種結果與寫檔時的對策，見 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈TOML 1.0 與 1.1 的差異與解析器的版本〉。`tomllib` 只能讀不能寫，要由程式寫出 TOML 時需要第三方套件。

## 鄰卡

- [HCL](/infra/knowledge-cards/hcl/)
- [.env](/infra/knowledge-cards/dotenv/)
- [php.ini / .user.ini](/infra/knowledge-cards/php-ini/)
