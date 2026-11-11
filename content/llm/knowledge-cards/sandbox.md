---
title: "Sandbox"
date: 2026-05-12
description: "把程式跑在受限制環境的隔離技術、限制檔案 / 網路 / 系統呼叫權限、是 tool use 跟 MCP server 副作用控制的基礎"
weight: 1
tags: ["llm", "knowledge-cards", "security", "isolation"]
---

Sandbox 的核心概念是「把程式跑在權限受限的隔離環境、限制檔案存取、網路連線、系統呼叫的範圍」。在 LLM 場景下、sandbox 用來控制 [tool use](/llm/knowledge-cards/tool-use/) 跟 MCP server 的副作用範圍：即使 LLM 被 [prompt injection](/llm/knowledge-cards/prompt-injection/) 誘導跑惡意 tool、sandbox 能限制最壞情況的影響面。

## 跟其他概念的關係

常見的 sandbox 技術光譜（依隔離強度跟工程成本）：

| 技術                         | 隔離強度            | 工程成本 | LLM 場景的典型用途                  |
| ---------------------------- | ------------------- | -------- | ----------------------------------- |
| 不同 OS user                 | 中（檔案權限）      | 低       | 個人 dev 跑 MCP server              |
| Docker container             | 中高                | 中       | 跑第三方 MCP server、隔離 LLM agent |
| VM / Firecracker / gVisor    | 高                  | 中高     | production 多租戶 LLM agent         |
| chroot / namespace           | 中                  | 中       | 限定 filesystem 視角                |
| seccomp / AppArmor / SELinux | 高（syscall 層）    | 高       | 細粒度限制 syscall                  |
| Web Worker / V8 isolate      | 中（JavaScript 層） | 中       | LLM 跑 user-provided JavaScript     |

Sandbox 在 LLM 場景的常見配置：

1. **個人 dev**：用獨立 OS user 跑 [MCP server](/llm/knowledge-cards/mcp/)、限制檔案存取到 workspace；或用 Docker。
2. **production agent**：每個 user / session 一個 ephemeral container、跑完就 destroy。
3. **code execution tool**：把 LLM 生成的 code 丟進 sandbox 跑（如 OpenAI Code Interpreter、Anthropic Claude Code Tool）。

## 判斷條件與後果

MCP server 是可執行的程式碼，權限上限是執行它的那個 OS user 的權限。第三方 MCP server 直接用開發者自己的帳號跑時，被 injection 誘導的 tool 呼叫讀寫得到這個帳號碰得到的所有檔案，所以 sandbox 是跑第三方 MCP server 的基本配置。production 的 code execution tool 若在長期存活的環境裡跑，前一個 user 留下的檔案與 state 會被下一個 user 的程式讀到；ephemeral sandbox 跑完就銷毀，沒有殘留可讀。

Sandbox 與 [tool use](/llm/knowledge-cards/tool-use/) 白名單攔下的對象不同：白名單限制 LLM 能呼叫哪些 tool，攔下已知範圍以外的呼叫；sandbox 限制被允許的 tool 執行時碰得到什麼，攔下白名單內的 tool 做出的未預期副作用。只有白名單時，被允許的 tool 受誘導之後做的事沒有邊界；只有 sandbox 時，LLM 能呼叫的 tool 種類沒有限制，所以兩層都要有。詳見 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)。
