---
title: "YAML"
date: 2026-10-26
description: "讀到 .yaml 或 .yml 設定檔、一個沒加引號的值被程式讀成布林值或別的數字、同一份檔案換一個解析器結果不同，或要在 JSON、YAML、TOML 之間選設定檔格式時"
weight: 73
tags: ["infra", "knowledge-cards", "yaml", "config"]
aliases: ["/infra/knowledge-cards/yaml/"]
---

YAML（YAML Ain't Markup Language）是一種用縮排表示結構的資料格式：`鍵: 值` 組成對應表，`- ` 開頭的行組成清單，子項目往右縮排一層，可以寫 `#` 開頭的註解，不加引號的值由解析器依寫法推測型別。Kubernetes 的 manifest、GitHub Actions 的 workflow、Ansible 的 playbook 與 inventory、Docker Compose 的設定檔都用這個格式（Ansible 的變數檔一樣受下面的隱式型別影響，見 [Configuration Management（組態管理）](/devops/infra/knowledge-cards/configuration-management/)）。同樣是給人手動編輯的設定檔格式，[TOML](/devops/infra/knowledge-cards/toml/) 用表頭分組、型別完全由寫法決定；[HCL](/devops/infra/knowledge-cards/hcl/) 另外有變數與函式，YAML 與 TOML 一樣只描述資料。

## 概念位置

YAML 在設定檔格式裡的位置是巢狀深、層數多的設定：縮排一層就是一層結構，寫到第五、六層仍然不必重複上層的名字，這是 Kubernetes 與 CI 工具選它的理由，[Helm](/devops/infra/knowledge-cards/helm/) 的 chart 參數檔 `values.yaml` 也是這個格式。付出的代價在型別：不加引號的值是什麼型別，由解析器實作的 YAML 版本決定，而一份檔案自己沒有辦法指定讀它的解析器。它跟 TOML、JSON 逐項比對的需求表與實測，見 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/devops/operations/09-host-lifecycle/host-manifest-in-toml/)〈主機維護清單對檔案格式的需求：JSON、YAML、TOML 的比對〉。

## 可觀察訊號

需要讀懂 YAML 的情境包括：打開一個副檔名是 `.yaml` 或 `.yml` 的檔案、程式讀到的值跟檔案上寫的字不一樣（寫 `no` 讀成 `false`、寫 `010` 讀成 8）、同一份檔案在兩個工具裡讀出不同的結果，以及解析器回報 `ScannerError` 或 `found character '\t' that cannot start any token` 這類縮排錯誤。

## 設計責任

YAML 的基本結構：

```yaml
# 註解
name: web-demo            # 對應表的一個鍵；不加引號的 web-demo 讀成字串
port: 443                 # 讀成整數
entrypoints:              # 值是一份清單
  - port: 443             # 清單的每一項以 "- " 開頭，項目本身可以是對應表
    exposure: cdn-only
  - port: 22
    exposure: admin-only
note: |                   # | 保留換行的多行字串
  第一行
  第二行
```

- **縮排就是結構**：同一層的鍵左側對齊，子項目多縮排一層；縮排只能用空格，Tab 字元會讓解析器回報 `ScannerError`。
- **不加引號的值由解析器推測型別**：這是 YAML 最常讓設定出錯的位置，見下面的版本差異。字串加上引號（`"no"`、`'010'`）就不會被推測。
- **重複的鍵不報錯**：PyYAML 6.0.3 解析 `a: 1` 接著 `a: 2`，得到 `{'a': 2}`，前一個值被安靜地蓋掉；手動維護的長檔案裡重複一個鍵，前面那一筆設定就不生效。
- **錨點與別名**：`&名稱` 標記一個節點、`*名稱` 引用它，用來在同一份檔案裡重用一段設定；讀的人要回頭找錨點才知道別名展開成什麼。
- **一個檔案可以有多份文件**：`---` 分隔多份文件，Kubernetes 常用這個寫法把多個資源放在同一個檔案裡。

**版本決定型別的推測規則**：YAML 1.1（2005 年）與 1.2（2009 年）對不加引號的值規則不同。同樣這五行：

```yaml
country: no
mode: 010
port_map: 22:22
version: 1.10
on: true
```

交給兩個 Python 解析器，結果是：

| 這一行             | PyYAML 6.0.3（實作 YAML 1.1） | ruamel.yaml 0.19.1（實作 YAML 1.2） |
| ------------------ | ----------------------------- | ----------------------------------- |
| `country: no`      | 布林值 `False`                | 字串 `'no'`                         |
| `mode: 010`        | 八進位的 `8`                  | 十進位的 `10`                       |
| `port_map: 22:22`  | 六十進位的 `1342`             | 字串 `'22:22'`                      |
| `version: 1.10`    | 浮點數 `1.1`                  | 浮點數 `1.1`                        |
| `on: true`（鍵名） | 鍵變成布林值 `True`           | 鍵是字串 `'on'`                     |

兩個解析器都沒有報錯。`no` 被讀成 `false` 這一種，英文資料常稱為 Norway problem（挪威的國家代碼 `NO` 變成布林值）。YAML 1.2 把布林值限定成 `true` 與 `false` 及其大小寫變體，所以 1.1 的幾個陷阱消失；`1.10` 在兩個版本都是合法的浮點數，所以版本號不論哪一版都要加引號。一份 YAML 檔被讀成哪一版，由讀它的程式選的解析器決定：PyYAML 至今實作 1.1；Go 的 `gopkg.in/yaml.v3` 依它的 README 以 1.2 為主，而解碼到布林型別的欄位時仍接受 1.1 的 `yes`、`no`、`on`、`off`（這一點照文件，沒有實跑），所以寫檔的人無法只看檔案判斷結果，跨工具共用的值一律加引號。這張表在 `python:3.12-slim` 容器裡以兩個套件的 `safe_load` 實跑。

## 鄰卡

- [TOML](/devops/infra/knowledge-cards/toml/)
- [HCL](/devops/infra/knowledge-cards/hcl/)
- [Helm](/devops/infra/knowledge-cards/helm/)
