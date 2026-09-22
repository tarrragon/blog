# 追溯矩陣整合點（Layer 2）

> **角色**：本檔是 `tdd` 的 Layer 2 整合點，記錄本框架的追溯矩陣住在哪、形狀由誰定義、誰消費它。
>
> **何時讀**：要把測試對象目錄的內容接上追溯矩陣、或有人提議把兩者合併時。
>
> **可攜性**：本目錄（`references/project-integration/`）不隨 skill 同步傳遞，由各專案自備。Layer 1 的語意在 `references/test-object-catalogue.md`〈與追溯矩陣的界線〉，那一節不依賴本檔。

## 本框架的對應

| 項目 | 本框架的實現 |
| ---- | ------------ |
| 追溯矩陣的住址 | `docs/traceability.yaml` |
| 形狀的定義處 | doc skill 的 `TRACEABILITY_SCHEMA`，在 `.claude/skills/doc/doc_system/core/tracking_schema.py` |
| 消費它的工具 | `test-map` CLI（映射軸）與人工查閱 |
| 單位 | 該 schema 各軸各自定義：使用案例映射、domain bundle、資料契約、runtime 場景 |

## 為什麼這一段是 Layer 2

Layer 1 講的是兩類產物的區別（設計期推導 vs 事後審計），那個區別在任何專案都成立。本檔的四列全是本框架的安裝細節：換一個專案，檔名、schema 名稱與 CLI 名稱都不同，而區別本身不變。

`TRACEABILITY_SCHEMA` 的頂層鍵是封閉集合且有 conformance 測試把關，所以把測試對象目錄的欄位塞進去會撞上強制層——這條後果與本框架的實作綁定，判斷標準本身寫在 Layer 1。
