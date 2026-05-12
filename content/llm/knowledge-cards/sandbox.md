---
title: "Sandbox"
date: 2026-05-12
description: "把程式跑在受限制環境的隔離技術、限制檔案 / 網路 / 系統呼叫權限、是 tool use 跟 MCP server 副作用控制的基礎"
weight: 1
tags: ["llm", "knowledge-cards", "security", "isolation"]
---

Sandbox 的核心概念是「把程式跑在權限受限的隔離環境、限制檔案存取、網路連線、系統呼叫的範圍」。在 LLM 場景下、sandbox 用來控制 [tool use](/llm/knowledge-cards/tool-use/) 跟 MCP server 的副作用範圍：即使 LLM 被 [prompt injection](/llm/knowledge-cards/prompt-injection/) 誘導跑惡意 tool、sandbox 能限制最壞情況的影響面。

## 概念位置

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

1. **個人 dev**：用獨立 OS user 跑 MCP server、限制檔案存取到 workspace；或用 Docker。
2. **production agent**：每個 user / session 一個 ephemeral container、跑完就 destroy。
3. **code execution tool**：把 LLM 生成的 code 丟進 sandbox 跑（如 OpenAI Code Interpreter、Anthropic Claude Code Tool）。

## 設計責任

理解 sandbox 後可以解釋兩個現象：為什麼跑第三方 MCP server 前 sandbox 是基本配置（MCP 是可執行程式碼、權限上限是「跑該 server 的 user 的權限」）、為什麼 production 場景的 code execution tool 必定在 ephemeral sandbox 內跑（避免長期 state 跟跨 user 殘留）。

設計 LLM application 時、sandbox 跟 [tool use](/llm/knowledge-cards/tool-use/) 的白名單是兩個獨立的防護層、建議都做：白名單擋已知範圍、sandbox 擋未預期的副作用。詳見 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)。
