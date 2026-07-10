---
title: "LLM Deployment 供應鏈完整性"
date: 2026-05-12
description: "把 LLM 模型權重、推論伺服器、第三方 plugin 三條 production 供應鏈納入既有 artifact trust 框架的判讀"
tags: ["backend", "security", "llm", "supply-chain", "model-trust", "deployment"]
weight: 98
---

本章的責任是把 LLM 服務的模型權重、推論伺服器、第三方 plugin / [MCP](/llm/knowledge-cards/mcp/) server 三條供應鏈、納入 [7.4 供應鏈與產物信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的既有框架。模型來源信任的判讀依據見 [model card](/llm/knowledge-cards/model-card/) 卡；通用 artifact 信任機制見 [artifact-provenance](/backend/knowledge-cards/artifact-provenance/) 卡。LLM 場景的特殊性在於模型權重既是「資料」又是「程式邏輯」、第三方 MCP 是可執行程式碼、跟一般 software artifact 的信任模型有部分差異、但 build provenance / signature / dependency isolation 等控制原則沿用同一套。

## 本章寫作邊界

本章聚焦 production LLM 服務的供應鏈完整性問題節點。個人 dev 視角的模型來源信任見 [llm/6.0 模型供應鏈與信任邊界](/llm/06-security/model-supply-chain-trust/)；本章不重複個人 dev 場景的判讀、聚焦 production 場景下的特殊議題（規模化下載、跨 region 鏡像、retry 策略、模型 release 流程）。

## 本章 threat scope

**In-scope**：模型權重 build provenance（HF organization / 量化者 / Ollama registry）、GGUF / safetensors artifact 完整性、production 下載與鏡像策略、第三方 MCP / plugin 的 deployment 供應鏈、模型版本回退機制。

**Out-of-scope**（路由到他章）：

- 一般 software artifact 信任 → [7.4 supply-chain-integrity-and-artifact-trust](../supply-chain-integrity-and-artifact-trust/)
- 機器憑證 → [7.6 secrets-and-machine-credential-governance](../secrets-and-machine-credential-governance/)
- 入口治理 → [7.3 entrypoint-and-server-protection](../entrypoint-and-server-protection/)
- 個人 dev 模型來源信任 → [llm/6.0 model-supply-chain-trust](/llm/06-security/model-supply-chain-trust/)
- 部署平台 → `05-deployment-platform`、可靠性 → `06-reliability`

## 從本章到實作

本章是 routing layer、沿兩條 chain 進入 implementation：

- **Mechanism**：問題節點表的 control link 進 knowledge-card、看具體機制與 LLM 場景的差異。
- **Delivery**：「交接路由」欄位指向 `05-deployment-platform / 06-reliability / 08-incident-response`、接配置 / 驗證 / 處置交付。

## LLM 供應鏈的三條 chain

LLM 服務的供應鏈跟一般 software 服務的差異在「同時管三條 chain」：

1. **模型權重 chain**：原始作者 → 官方 release → 量化者 → registry → production 鏡像
2. **推論伺服器 chain**：llama.cpp / vLLM / Ollama 等 server software 的一般 software artifact chain
3. **第三方 plugin / MCP chain**：MCP server / Continue.dev 等的程式碼供應鏈

三條 chain 在 production 階段都需要 build provenance、簽署驗證、依賴隔離跟回退機制。差異主要在模型權重 chain 的特殊性：權重是大型 binary（GB 級）、難以靜態 audit、且權重本身會影響推論行為。

## 分析模型

production LLM 供應鏈的分析依五個層次拆解、跟 [7.4](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的層次模型保持一致：

1. **來源層**：模型 build provenance 是否可回溯（哪個 base model、用哪個 dataset、由誰量化）。
2. **產物層**：GGUF / safetensors 在傳遞過程的完整性（hash / 簽署）。
3. **依賴層**：MCP server / inference framework / model 各自獨立信任、影響面隔離。
4. **節奏層**：模型版本切換、回退、freeze 流程。
5. **收斂層**：供應鏈事件能否路由到 IR 流程。

## 判讀流程

判讀流程的責任是把「可部署的 LLM 服務」轉成「可信的 LLM 服務」。

1. 先確認模型來源 organization、量化版本、build provenance 可關聯。
2. 再確認 GGUF / safetensors 的完整性證據（hash、size、metadata）。
3. 接著確認模型 + server + plugin 三條 chain 的依賴隔離。
4. 最後交接到可靠性與 incident 流程、追蹤回退能力。

## 問題節點（案例觸發式）

| 問題節點                     | 判讀訊號                                        | 風險後果                                | 前置控制面                                                             |
| ---------------------------- | ----------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------- |
| 模型來源不可追溯             | HF organization 不明、量化者沒公開 build script | 模型可信度下降、無法 audit、合規問題    | [ci-pipeline](/backend/knowledge-cards/ci-pipeline/)                   |
| GGUF artifact 完整性斷點     | 缺 hash 比對、CDN 鏡像未驗證、未簽署            | 模型權重被替換、影響推論行為            | [deployment-contract](/backend/knowledge-cards/deployment-contract/)   |
| 第三方 MCP / plugin 風險放大 | 多服務共用同一 MCP server、依賴版本固定         | 單一 MCP server 漏洞波及多 service      | [dependency-isolation](/backend/knowledge-cards/dependency-isolation/) |
| 模型版本切換節奏混亂         | 版本切換條件不一致、回退測試缺失                | 切換時行為差異未測、production incident | [release-gate](/backend/knowledge-cards/release-gate/)                 |
| 量化版本污染                 | 信任未知量化者、未做 behavior regression        | 量化過程引入後門或非預期行為            | [contract-test](/backend/knowledge-cards/contract/)                    |
| 跨 region 鏡像不一致         | 不同 region 跑不同版本權重、cache 政策衝突      | 一致性議題、debug 困難                  | [deployment-contract](/backend/knowledge-cards/deployment-contract/)   |

## 常見風險邊界

風險邊界的責任是界定何時 LLM 供應鏈風險已進入高壓狀態。

- 模型來源（base + dataset + 量化者）長期無法回溯時、代表 provenance 模型失效。
- 模型 artifact 在 CDN / 鏡像層沒有簽署驗證時、代表完整性邊界不足。
- MCP server / plugin 跟 inference framework 共用單一信任域時、代表依賴隔離不足。
- 模型版本切換沒有 behavior regression test 時、代表 release 流程不收斂。

## LLM 場景的特殊判讀

LLM 供應鏈相對一般 software 供應鏈有幾個特殊點：

1. **權重是大型 binary、難以靜態 audit**：跟 source code 不同、權重檔案無法用 grep / diff / linter 找後門；只能用 behavior testing 跟 hash 比對。
2. **量化過程可能改變推論行為**：同一 base model 不同量化版本、回答品質有差；量化者的可信度影響整體可信度、需 case-by-case 信任。
3. **模型 supply chain 跟 production deployment 解耦**：模型釋出方（如 Meta、Qwen 團隊）跟 production 部署方通常不同單位、責任邊界要明確。
4. **「license」議題**：模型權重的 license（如 Llama Community License）跟一般 software license 不同、production 使用需 legal review、不只是技術議題。
5. **MCP server 多為 Node / Python 程式**：跟一般 dependency 一樣有 supply chain 風險、但 LLM 場景下、MCP 對主機資源的副作用面比一般 dependency 大、需更嚴格的 isolation。

## 案例觸發參考

LLM 場景的供應鏈事件案例尚在累積中、本章先沿用 [7.4](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的通用案例。LLM-specific 案例累積後會補入 `red-team/cases/llm-supply-chain/`：

- 開源組件滲透與下游衝擊：[XZ Backdoor 2024](/backend/07-security-data-protection/red-team/cases/supply-chain/xz-backdoor-2024-open-source-supply-chain/)（同類威脅在 MCP server / inference framework 也適用）
- 平台級供應鏈事件：[SolarWinds 2020](/backend/07-security-data-protection/red-team/cases/supply-chain/solarwinds-2020-sunburst/)（模型釋出方平台級事件適用）

> **事實查核註**：LLM 供應鏈的公開事件案例累積還在早期、本章列舉的通用案例提供 mechanism 對照、不代表 LLM 場景已有等同規模的事件記錄。建議引用前以最新的 [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) 跟社群 incident 報告為準。

## 引用標準

LLM 場景的供應鏈標準在發展中、本章沿用 [7.4 供應鏈與產物信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) 的標準作為 mechanism 層 anchor、補上 LLM-specific 參考：

| 標準                                | 版本 / 年份 | 適用場景                                       |
| ----------------------------------- | ----------- | ---------------------------------------------- |
| SLSA                                | v1.0 (2023) | 套用於 inference server + MCP build provenance |
| Sigstore（cosign / Rekor / Fulcio） | continuous  | 模型 artifact 簽署實驗階段                     |
| OWASP LLM Top 10                    | 2025        | LLM application security 通用 reference        |
| Hugging Face Model Card spec        | continuous  | 模型來源 metadata                              |

引用版本與 cadence 規則見 [security-citation-currency-and-precision](/report/security-citation-currency-and-precision/)。Last reviewed: 2026-05-12。

## 下一步路由

- 交付平台與部署治理：`05-deployment-platform`
- 發佈驗證與回退演練：`06-reliability`
- 多租戶 LLM 推論隔離：[llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)
- 偵測訊號設計：[llm-as-service-detection-coverage](/backend/07-security-data-protection/llm-as-service-detection-coverage/)
- 分級與跨部門收斂：`08-incident-response`
