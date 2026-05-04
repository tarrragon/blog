---
title: "WRAP Integration Patterns"
date: 2026-05-04
description: "WRAP reference：把 WRAP 整合進任務系統、CLI、Hook、規則庫與案例庫的可攜模式總覽。"
tags: ["skills", "wrap-decision", "決策框架", "工程方法論"]
---

本目錄的責任是提供 WRAP 在任務系統、CLI、Hook、規則庫與案例庫中的可攜整合模式。內容只描述通用整合語意，不依賴特定專案路徑或工具名稱。

---

## 依賴方向

```text
WRAP core skill  ->  integration patterns  ->  project-specific implementation
通用原理             可攜模板                  各專案自行落地
```

整合層可以引用 WRAP core skill，專案實作可以引用整合層。WRAP core skill 保持獨立，避免反向依賴任何專案實作。

---

## 檔案清單

| 檔案                                                                                                 | 內容                                                 |
| ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [triggers-alignment](/skills/wrap-decision/integration-patterns-triggers-alignment/)                 | 觸發條件在文字規則、機器設定與自動提醒之間的同步模式 |
| [simplified-three-questions](/skills/wrap-decision/integration-patterns-simplified-three-questions/) | 任務啟動時的 W/A/P 三問模板                          |
| [pseudo-widen-guard](/skills/wrap-decision/integration-patterns-pseudo-widen-guard/)                 | 偽 Widen 防護與假設層級多元性檢查                    |
| [source-verification](/skills/wrap-decision/integration-patterns-source-verification/)               | 清單類答案的逐項來源核對流程                         |
| [personalized-advice](/skills/wrap-decision/integration-patterns-personalized-advice/)               | 個人化建議場景的 Step 0 落地方式                     |
| [rules-map](/skills/wrap-decision/integration-patterns-rules-map/)                                   | 規則庫與 WRAP 的分工模板                             |
| [case-studies](/skills/wrap-decision/integration-patterns-case-studies/)                             | 案例庫的收錄欄位與抽象化方式                         |

---

## 使用方式

1. 先讀 [skill](/skills/wrap-decision/skill/)，確認是否觸發 WRAP。
2. 需要把 WRAP 接到工具或流程時，讀本目錄的對應模板。
3. 在專案內建立自己的實作文件，填入實際路徑、指令、狀態欄位與 owner。
4. 保持核心 skill 與專案實作分離。

---

## 可攜限制

本目錄保留為可攜模板，因此遵守以下限制：

- 只使用 skill 內部相對連結與中性範例。
- 只使用通用任務名稱，避免專案內部任務編號、批次代號、錯誤代碼或歷史編號。
- 保持 CLI、Hook framework 與任務管理工具的供應商中立。
- 範例使用中性名稱，例如 task、rule store、automation hook、case library。

---

**Last Updated**: 2026-04-30
**Version**: 2.0.0 — 改為 portable integration patterns。
