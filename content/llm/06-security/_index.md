---
title: "模組六：本地 LLM 的安全與權限"
date: 2026-05-12
description: "個人 dev 在自己機器上跑本地 LLM 的安全議題：模型供應鏈、推論伺服器綁定、tool use 副作用、prompt injection 在 IDE、跨雲端 / 本地資料邊界"
tags: ["llm", "security", "local-llm", "tool-use", "prompt-injection", "supply-chain"]
weight: 6
---

本模組的核心目標是把「個人 dev 在自己機器上跑本地 LLM 寫 code」這條工作流上會碰到的安全議題拆成可操作的判讀。跟 [模組一](/llm/01-local-llm-services/) / [模組五](/llm/05-discrete-gpu/) 是同一條讀者旅程的延伸：模組一/五處理「怎麼跑得起來」、本模組處理「跑起來後該注意什麼」。

本模組的 framing 是**個人 dev 視角**、不是 enterprise 資安管理視角。production LLM 服務化的特殊資安議題（多租戶 isolation、deployment 供應鏈、agent 場景 prompt injection 後果、log/PII 治理、偵測訊號）見 [Backend 模組七 資安與資料保護](/backend/07-security-data-protection/) 的 LLM 相關章節。

## 本模組的責任範圍

| 處理                                                                                                                        | 不處理                                                                                   |
| --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 個人 dev 用本地 LLM 時的模型來源信任、推論伺服器綁定、tool use 副作用權限、IDE 場景 prompt injection、跨雲端 / 本地資料邊界 | enterprise IAM、production audit log、合規認證、incident response 流程                   |
| 從個人 dev 跨進 team / production 場景的 routing 中樞                                                                       | production 多租戶推論服務 isolation、agent 場景的 prompt injection 後果（見 backend/07） |

跟 [Backend 模組七 資安與資料保護](/backend/07-security-data-protection/) 的分工：本模組的 6.1 ~ 6.4 是「個人 dev 場景下的安全議題」、用到的通用資安詞彙（identity / boundary / supply chain / transport trust 等）cross-link 回 backend/07 的既有卡片、不在本模組重新定義。

## 章節列表

| 章節                                                     | 主題                              | 關鍵收穫                                                             |
| -------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------- |
| [6.0](/llm/06-security/model-supply-chain-trust/)        | 模型供應鏈與信任邊界              | GGUF / Hugging Face / Ollama registry 信任、量化版本污染、權重完整性 |
| [6.1](/llm/06-security/inference-server-binding/)        | 推論伺服器的綁定與暴露範圍        | 127.0.0.1 vs 0.0.0.0 vs 反代、預設安全、誤開放給內網的後果           |
| [6.2](/llm/06-security/tool-use-permission-model/)       | tool use 與 MCP server 的權限模型 | 檔案系統 / shell / 網路存取邊界、第三方 MCP 信任、副作用的可逆性     |
| [6.3](/llm/06-security/prompt-injection-in-ide/)         | IDE 場景的 prompt injection       | codebase 內容、外部文件、剪貼簿作為攻擊面、跟雲端 LLM 場景的差異     |
| [6.4](/llm/06-security/cross-cloud-local-data-boundary/) | 跨雲端 / 本地的資料邊界           | Continue.dev 多 provider 設定、prompt 洩漏點、本地優先的判讀         |
| [6.5](/llm/06-security/routing-to-production-security/)  | 跨進 production 的 routing 中樞   | 個人 → 團隊 → production 三層演化、列舉 backend/07 對應卡片          |

## 跟其他模組的關係

| 模組           | 關係                                                                                                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 模組零         | 本模組沿用模組零的[隱私資料流](/llm/00-foundations/privacy-data-flow/)框架                                                                           |
| 模組一 / 五    | 本模組是模組一 / 五的安全延伸；模組一/五教怎麼跑、本模組教跑起來該注意什麼                                                                           |
| 模組四         | 本模組 6.2 / 6.3 / 6.5 跟模組四的 [tool use](/llm/04-applications/tool-use-principles/) / [agent](/llm/04-applications/agent-architecture/) 章節呼應 |
| Backend 模組七 | 本模組引用其通用資安卡片；production 場景的 LLM-specific 議題在 backend/07 補充                                                                      |

## 為什麼這個順序

本模組章節順序的設計脈絡：

1. **先 6.0 模型供應鏈**：模型權重是本地 LLM 的最上游、信任邊界從這裡開始；裝錯模型其他防護都沒意義。
2. **再 6.1 推論伺服器綁定**：模型載入後、伺服器是第一個對外的接觸面；綁定錯誤是個人 dev 場景最常見的暴露點。
3. **接 6.2 tool use 權限**：伺服器跑起來後、最大的副作用來自 tool use / MCP 對本機資源的存取。
4. **再 6.3 prompt injection**：tool use 跟 RAG 把外部內容引入 prompt、prompt injection 才有著力點。
5. **然後 6.4 跨雲端 / 本地邊界**：寫 code 場景常混用雲端 LLM、prompt 的洩漏軌跡要說清楚。
6. **最後 6.5 跨進 production**：個人 dev 工作流穩了之後、若要分享給團隊或部署成服務、需要的 routing。

## 個人 dev 視角的 threat model 預設

本模組假設的 threat model：

1. **攻擊者預期**：不是 nation-state APT、而是「不小心被執行的 malicious payload」（誤裝有問題的 GGUF、誤裝有問題的 MCP server、誤點到帶 prompt injection 的網頁 / 文件 / pull request）。
2. **保護的 asset**：本機檔案、開發中的 codebase（含未公開）、雲端 API key（OpenAI、Anthropic 等）、SSH key 與其他憑證。
3. **trust boundary**：本機 user account 邊界、prompt 邊界、tool 副作用邊界。
4. **可接受風險**：個人 dev 不需要 enterprise-grade audit log、IDS / IPS、SOC、紅藍隊演練；用基本權限隔離 + 預設安全配置 + 場景判讀為主。

production / 多人協作場景的 threat model 完全不同、見 [Backend 模組七](/backend/07-security-data-protection/)。

## 不在本模組內的主題

本模組不討論：

1. **enterprise IAM、SSO、SAML / OIDC**：個人 dev 場景用不到、屬 backend/07 [identity-access-boundary](/backend/07-security-data-protection/identity-access-boundary/)。
2. **合規認證（SOC 2、ISO 27001、HIPAA、GDPR 流程）**：個人 dev 場景的隱私判讀見 6.4、企業合規流程屬 backend/07。
3. **detection / SIEM / SOAR**：個人 dev 場景靠 OS 既有 log 跟手動觀察、企業偵測屬 backend/07 [detection-coverage-and-signal-governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。
4. **incident response 標準流程**：個人 dev 場景靠快速止血 + 重置、企業 IR 流程屬 backend/07 [incident-case-to-control-workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)。
5. **模型本身的對抗性訓練 / 後門**：屬研究範疇、本模組假設用主流模型作者發布的權重作為可信起點。
