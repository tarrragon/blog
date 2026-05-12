---
title: "Prompt Injection"
date: 2026-05-12
description: "把惡意指令藏進 LLM 會讀到的內容、誘導 LLM 跑出非開發者預期行為的攻擊類別、OWASP LLM01 列入頭號威脅"
weight: 1
tags: ["llm", "knowledge-cards", "security", "owasp"]
---

Prompt injection 的核心概念是「攻擊者把惡意指令藏進 LLM 會讀到的內容（檔案、網頁、issue、tool 回傳）、誘導 LLM 忽略原本的 [system prompt](/llm/knowledge-cards/system-prompt/)、改執行攻擊者意圖的動作」。OWASP [LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 把它列為 LLM01、是 LLM application 安全的頭號威脅。

## 概念位置

Prompt injection 的兩種主要形態：

| 形態               | 描述                           | 個人 dev 場景的觸發路徑  |
| ------------------ | ------------------------------ | ------------------------ |
| Direct injection   | 使用者自己 prompt 內含惡意指令 | 較少發生、主要是測試場景 |
| Indirect injection | LLM 讀到的別人內容含惡意指令   | 主要威脅形態             |

Indirect injection 的常見入口：

1. **檔案內容**：codebase 中的 README、依賴的 package README、PDF / Word 文件
2. **Web 內容**：tool 抓的網頁、社群留言、PR 描述
3. **tool 回傳結果**：DB 查詢結果、API response、其他 service 回傳
4. **使用者貼上內容**：從外部複製貼上、帶進惡意 prompt
5. **agent 自我循環中累積**：sub-agent 回傳、長 agent loop 中前段 injection 影響後段

> **事實查核註**：prompt injection 的攻擊形態跟研究進展快速演進、本卡描述參考 [OWASP LLM Top 10 LLM01](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 跟 Greshake et al. 的「Indirect Prompt Injection」論文、引用前以對應的最新版本為準。

實際造成影響的不是 injection 本身、是 LLM 輸出後的下游動作：

```text
injection → LLM 輸出 → 下游動作（這裡才是真正攻擊面）
                       ├── 使用者照建議貼到 shell 跑
                       ├── tool use 自動執行
                       ├── 寫進 commit / 文件
                       └── 觸發下一個 agent
```

## 設計責任

理解 prompt injection 後可以解釋兩個現象：為什麼「擋住 injection」對 production LLM application 是不切實際的目標（外部內容會持續引入）、為什麼防禦重點應該放在「下游動作的可逆性 + review checkpoint」（injection 不可完全擋住、但後果可以收斂）。

防禦設計的層次：

1. **降低觸發率**：明確標記 untrusted 內容、強化模型對齊（vendor 端責任）。
2. **限制能力上限**：[tool use](/llm/knowledge-cards/tool-use/) 白名單、副作用可逆性、agent loop 步數限制。
3. **後果可控**：人為 review checkpoint、自動偵測異常（見 [LLM Service 偵測訊號覆蓋](/backend/07-security-data-protection/llm-as-service-detection-coverage/)）。

詳見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/) 跟 [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)。
