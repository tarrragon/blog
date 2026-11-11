---
title: "Prompt Injection"
date: 2026-05-12
description: "把惡意指令藏進 LLM 會讀到的內容、誘導 LLM 跑出非開發者預期行為的攻擊類別、OWASP LLM01 列入頭號威脅"
weight: 1
tags: ["llm", "knowledge-cards", "security", "owasp"]
---

Prompt injection 的核心概念是「攻擊者把惡意指令藏進 LLM 會讀到的內容（檔案、網頁、issue、tool 回傳）、誘導 LLM 忽略原本的 [system prompt](/llm/knowledge-cards/system-prompt/)、改執行攻擊者意圖的動作」。OWASP [LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 把它列為 LLM01、是 LLM application 安全的頭號威脅。

## 跟其他概念的關係

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
5. **agent 自我循環中累積**：sub-agent 回傳、長 [agent loop](/llm/knowledge-cards/agent-loop/) 中前段 injection 影響後段

> **事實查核註**：prompt injection 的攻擊形態跟研究進展快速演進、本卡描述參考 [OWASP LLM Top 10 LLM01](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 跟 Greshake et al. 的「Indirect Prompt Injection」論文、引用前以對應的最新版本為準。

實際造成影響的是 LLM 輸出後的下游動作，而不是 injection 本身：

```text
injection → LLM 輸出 → 下游動作（這裡才是真正攻擊面）
                       ├── 使用者照建議貼到 shell 跑
                       ├── tool use 自動執行
                       ├── 寫進 commit / 文件
                       └── 觸發下一個 agent
```

## 判斷條件與後果

Production LLM application 的 context 會持續讀進外部內容（檔案、網頁、tool 回傳），只靠擋住 injection 的防禦，漏掉一次就讓攻擊者的指令走到下游動作。injection 本身不改變任何狀態，改變狀態的是 LLM 輸出之後的那個動作，所以防禦的效果取決於下游動作的範圍是否受到限制、做錯了能否復原。三個防禦層各自缺席時，系統處在的狀態：

1. **沒有降低觸發率的措施時**（不標記哪些內容來自 untrusted 來源、模型的對齊較弱），模型較常照著外部內容裡的指令做，能力上限與後果控制兩層要攔的次數變多。強化對齊是 vendor 端的工作，應用端做得到的是標記 untrusted 內容。
2. **沒有限制能力上限時**（沒有 [tool use](/llm/knowledge-cards/tool-use/) 白名單、副作用不可逆、agent loop 沒有步數限制），一次成功的 injection 能呼叫任何 tool、做出無法復原的修改，並在 loop 裡連續執行多步，損害的範圍沒有上限。
3. **沒有後果控制時**（沒有人為 review checkpoint、沒有自動偵測異常，見 [LLM Service 偵測訊號覆蓋](/backend/07-security-data-protection/llm-as-service-detection-coverage/)），越過觸發率與能力上限兩層的動作直接生效，事後也沒有訊號指出哪一步是被誘導的。

詳見 [6.3 IDE 場景的 prompt injection](/llm/06-security/prompt-injection-in-ide/) 跟 [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)。
