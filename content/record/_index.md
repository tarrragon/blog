---
title: "開發記錄"
slug: "record"
---

這個資料夾收錄**方法論記錄** — 寫法是中性 frame 的「某個工作模式 / 流程 / 原則是什麼、怎麼用」、不一定有具體 case 觸發。

內容大致分五類：

**自察與認知方法論** — 工作前 / 工作中的自我檢視框架。例：

- [5W1H 自察方法論](5w1h-self-awareness-methodology/)
- [AI 任務迴避偵測方法論](ai-task-avoidance-detection-methodology/)
- [大規模重構方法論](大規模重構方法論/)

**設計判斷與選型** — 技術決策框架，避免過度設計與設計瑕疵的判斷標準（如 YAGNI 的真實適用條件、成本不對稱性下的選擇邏輯）。例：

- [YAGNI 的真實適用條件](yagni-boundary-three-axes/)

**敏捷 / 工程流程** — 敏捷實作、重構流程、文件分層。例：

- [敏捷編程方法論](agile-programing-methodology/)
- [敏捷重構方法論](agile-refactor-methodology/)
- [5 層文件系統](5-layer-doc-system/)

**寫作 / 溝通標準** — 驗收條件、寫作規範。例：

- [驗收條件方法論](acceptance-criteria-methodology/)
- [經驗分享文章的寫作準則](writing-guidelines/)

**文件與 API 設計** — function 文件分層、測試命名作為 spec、commit message vs source code doc 的職責邊界、型別取代 doc 等表達設計議題。例：

- [函式文件分層設計](function-doc-layered-design/)
- [型別取代 doc 的收益曲線](types-replacing-docs/)
- [測試命名作為文件](test-naming-as-documentation/)
- [Commit message vs source code doc](commit-message-vs-source-doc/)

---

## 跟其他資料夾的邊界

| 議題                                     | 該放                               |
| ---------------------------------------- | ---------------------------------- |
| 從具體 case 抽出可重用的工程原則         | `report/`（case-driven、編號連續） |
| 工作中遇到的具體事件 / 工具坑            | `work-log/`                        |
| blog 本身的設計 / 規範                   | `posts/`                           |
| 中性 frame 的方法論說明（不綁特定 case） | **本資料夾**                       |

**跟 `report/` 的區別**：record 是「方法論本身怎麼用」（教學 / 中性說明）、report 是「從某個 case 抽出來的原則」（事後檢討 / case-driven）。同一個議題若先有方法論再有 case、方法論寫 record、case 抽出的原則寫 report；若是先踩坑再抽原則、直接寫 report。

---

底下自動列出本資料夾的所有文章、依日期排序。
