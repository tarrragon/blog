---
title: "6.5 跨進 production 的 routing 中樞"
date: 2026-05-12
description: "個人 dev → 團隊 → production LLM 服務的三層演化、跟 backend/07 對應卡片的 routing 清單"
tags: ["llm", "security", "production", "routing", "team", "deployment"]
weight: 6
---

模組六前五章建立了個人 dev 視角的 LLM 安全判讀（[6.0 供應鏈](/llm/06-security/model-supply-chain-trust/)、[6.1 伺服器綁定](/llm/06-security/inference-server-binding/)、[6.2 tool use 權限](/llm/06-security/tool-use-permission-model/)、[6.3 prompt injection](/llm/06-security/prompt-injection-in-ide/)、[6.4 跨雲端資料邊界](/llm/06-security/cross-cloud-local-data-boundary/)）、framing 的根基是 [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)。當工作流從個人 dev 跨進團隊共用、再跨進 production 服務時、安全議題的 framing 跟控制機制都會升級。升級的軸對應 backend 既有卡片：[attack-surface](/backend/knowledge-cards/attack-surface/)、[blast-radius](/backend/knowledge-cards/blast-radius/)、[trust-boundary](/backend/knowledge-cards/trust-boundary/)、[tenant-boundary](/backend/knowledge-cards/tenant-boundary/)、[iam](/backend/knowledge-cards/iam/) 等。本章是這兩個跨越的 routing 中樞、把每個議題在 production 場景下的對應位置（backend/07 對應卡片）整理出來、避免讀者在升級階段「不知道下一步該讀什麼」。

讀完本章後、你應該能判讀自己當前處在三層哪一階、要跨到下一階時需要補哪些議題、對應到 backend/07 哪些卡片。

## 本章目標

1. 區分個人 dev、團隊共用、production 三層 LLM 部署的安全議題差異。
2. 知道從個人 dev 跨到團隊共用時、需要補哪些控制。
3. 知道從團隊共用跨到 production 時、需要補哪些控制。
4. 認識每層演化對應的 backend/07 卡片清單。
5. 知道何時該停留在當前層、何時該主動升級。

## 三層演化的判讀軸

```text
個人 dev（本模組前五章）
   ↓
團隊共用（家裡 / 小團隊 / 內部部署）
   ↓
production 服務（對外服務 / SaaS / B2B）
```

三層的核心差異：

| 維度              | 個人 dev             | 團隊共用            | production 服務           |
| ----------------- | -------------------- | ------------------- | ------------------------- |
| 使用者數          | 1                    | 5 ~ 50              | 50+ / 對外不限            |
| 信任假設          | 自己信自己           | 同事互信、訪客不信  | 全部不信、用 IAM 控制     |
| 資料邊界          | 本機 user account    | 內網                | 多租戶、明確隔離          |
| 失誤後果          | 自己承擔             | 影響少數同事        | 影響大量用戶 / 法律責任   |
| 控制機制需求      | 基本配置 + git track | + auth + log + 政策 | + IAM + audit + IR + 合規 |
| 對應的時間 / 預算 | 小時級               | 天級                | 週 / 月級、需要專人或團隊 |

關鍵原則：**控制機制應該跟需求對齊、不該過度設計也不該不足**。個人 dev 不需要 SOC 2 audit、production 不能只靠 git track。

## 個人 dev → 團隊共用：要補什麼

從個人 dev 跨到團隊共用、典型的觸發場景：

1. 家裡跑模型給家人 / 室友用
2. 小團隊共用一台 LLM server
3. 公司內部部署、有 5 ~ 50 個工程師用

需要補的控制（在前五章的基礎上）：

| 議題     | 從個人 dev 的什麼演化而來                                                         | 對應的補強                                 | backend/07 對應卡片                                                                                                          |
| -------- | --------------------------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| 身份識別 | 自己一人 → 多人共用                                                               | 加 auth、知道誰送了什麼 prompt             | [identity-access-boundary](/backend/07-security-data-protection/identity-access-boundary/)                                   |
| 入口治理 | bind 到 LAN 加 API key                                                            | 反代 + TLS + rate limit                    | [entrypoint-and-server-protection](/backend/07-security-data-protection/entrypoint-and-server-protection/)                   |
| 傳輸信任 | 內網 HTTP 偶爾 OK                                                                 | 內網全程 HTTPS、TLS 憑證管理               | [transport-trust-and-certificate-lifecycle](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/) |
| 秘密管理 | dotfile 環境變數                                                                  | 集中 secret store（Vault / SSM / Doppler） | [secrets-and-machine-credential-governance](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) |
| 供應鏈   | 自己抓 GGUF / npm package（見 [6.0](/llm/06-security/model-supply-chain-trust/)） | 內部 mirror、固定 version、定期 audit      | [supply-chain-integrity-and-artifact-trust](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) |
| 政策     | 自己腦中的判讀                                                                    | 寫明 acceptable use、敏感內容指引          | （結合各章的政策性章節）                                                                                                     |

團隊共用階段的常見 anti-pattern：

1. **把個人 dev 的 dotfile config 直接複製到團隊 server**：API key、log 路徑、reset 機制都不對。
2. **依賴單一管理員口頭傳遞政策**：沒寫下來、新成員不知道、人離職就失傳。
3. **跳過 auth 直接用「公司內網本來就安全」當理由**：內網設備有訪客、有實習生、有 BYOD、有合作廠商；零信任的最低版本仍要做。

## 團隊共用 → production：要補什麼

從團隊共用跨到 production 服務、典型的觸發場景：

1. 把內部 LLM 服務開放給外部客戶（B2B）
2. 做 SaaS-like LLM API 對外賣
3. 把 LLM 嵌入產品給終端用戶用

需要補的控制（在前面兩層的基礎上）：

| 議題                        | 從團隊共用的什麼演化而來                                                                                                         | 對應的補強                                              | backend/07 對應卡片                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 多租戶隔離                  | 共用 server 跨同事 → 跨用戶                                                                                                      | KV cache / log / model 訪問權的多租戶隔離               | [llm-multi-tenant-isolation](/backend/07-security-data-protection/llm-multi-tenant-isolation/)                             |
| deployment 供應鏈           | 內部 mirror → 對外責任                                                                                                           | 模型 release 流程、簽章、回退機制                       | [llm-deployment-supply-chain](/backend/07-security-data-protection/llm-deployment-supply-chain/)                           |
| agent prompt injection 後果 | IDE injection（[6.3](/llm/06-security/prompt-injection-in-ide/)）→ agent 場景（[4.4](/llm/04-applications/agent-architecture/)） | tool spec 設計、限制 agent loop、人為 review checkpoint | [llm-prompt-injection-in-agent](/backend/07-security-data-protection/llm-prompt-injection-in-agent/)                       |
| log / PII 治理              | 簡單 access log → 完整 prompt log                                                                                                | log 累積的 prompt 內容、PII 偵測與過濾、保留期限        | [llm-log-and-pii-governance](/backend/07-security-data-protection/llm-log-and-pii-governance/)                             |
| 偵測訊號                    | 看 log → 主動偵測                                                                                                                | LLM agent 異常行為的訊號設計、tool use 異常模式         | [llm-as-service-detection-coverage](/backend/07-security-data-protection/llm-as-service-detection-coverage/)               |
| Workload Identity           | server 自己持 API key → workload IAM                                                                                             | 每個 workload 一個身份、可 audit                        | [workload-identity-and-federated-trust](/backend/07-security-data-protection/workload-identity-and-federated-trust/)       |
| 偵測平台                    | 手動觀察 → SIEM                                                                                                                  | 集中偵測、alert 系統                                    | [detection-coverage-and-signal-governance](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) |
| Incident response           | 重啟解決 → IR 流程                                                                                                               | IR 演練、escalation、post-mortem                        | [incident-case-to-control-workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)               |
| 合規                        | 不需要 → 對外服務需要                                                                                                            | GDPR / HIPAA / SOC 2 等                                 | [data-protection-and-masking-governance](/backend/07-security-data-protection/data-protection-and-masking-governance/)     |

production 階段不是「把團隊共用放大」、是「另一個複雜度等級」。多數議題從 backend/07 既有卡片開始讀、LLM-specific 議題在 backend/07 的 LLM 相關章節（`llm-*.md`）補充。

## 何時該停留在當前層

不是所有工作流都需要升級。停留在當前層的合理判讀：

| 當前層     | 該停留的徵兆                                  | 升級的徵兆                                                |
| ---------- | --------------------------------------------- | --------------------------------------------------------- |
| 個人 dev   | 只有自己用、不分享、沒對外暴露需求            | 開始有人想連你的 server / 想做 demo 給朋友 / 想分享給家人 |
| 團隊共用   | 5 ~ 50 人的內部使用、不對外賣、不涉及客戶 PII | 客戶要連 / 對外 SLA / 要收費 / 開始涉及客戶 PII           |
| production | 已對外服務、有 SLA、有客戶                    | （目標狀態）                                              |

升級的兩個常見錯誤：

1. **過早升級**：個人 dev 階段就上 enterprise stack（IAM、Vault、SIEM）、複雜度過高、自己用不到、維護成本反而傷工作流。
2. **過晚升級**：團隊共用階段該補的控制沒補、出事才補、可能已經有資料外洩 / 法律責任。

判讀依據：**控制機制對齊實際 threat model 跟 user 規模**、不是「越多越好」。

## 跨層升級的常見 anti-pattern

從各層往上跨時、常見的意外：

1. **把個人 dev 的 LLM client config 直接放上 production**：autocomplete model、default model、API key 都不對；production 場景需要重新設計 model 路由。
2. **把個人習慣的 prompt injection 防護當 production 防護**：「我 git track 工作流」對個人 dev 夠、production agent 場景下、git 不在迴路裡、要改用 tool spec + review checkpoint。
3. **production 場景仍然依賴使用者「看 prompt 內容」**：使用者數量大、不可能每個 prompt 都人工看；production 需要自動化偵測訊號。
4. **production 場景沒 tenant 隔離**：所有用戶的 KV cache / log / context 混在一起、A 用戶能看到 B 用戶的 cache hit。
5. **沒有 vendor 政策的書面化承諾**：team 階段口頭講「我們不訓練客戶資料」、production 階段要寫進條款 / SLA。

## 給讀者的層級判讀清單

判斷自己當前在哪一層：

```text
[ ] 只有自己用                                              → 個人 dev
[ ] 1 ~ 5 個人共用一台 server                                → 個人 dev 或團隊共用初期
[ ] 5 ~ 50 個人共用、內部部署                                → 團隊共用
[ ] 對外提供 API 服務 / SaaS                                 → production
[ ] 服務多個客戶 / 涉及客戶 PII                              → production
[ ] 有 SLA / 合約承諾                                        → production
```

對應的「要補的議題」：

```text
個人 dev → 團隊共用：
  [ ] auth                  ← backend/07 identity-access-boundary
  [ ] 入口治理               ← backend/07 entrypoint-and-server-protection
  [ ] TLS                    ← backend/07 transport-trust-and-certificate-lifecycle
  [ ] secret 集中管理        ← backend/07 secrets-and-machine-credential-governance
  [ ] 內部 supply chain      ← backend/07 supply-chain-integrity-and-artifact-trust
  [ ] 寫下 acceptable use 政策

團隊共用 → production：
  [ ] 多租戶 isolation       ← backend/07 llm-multi-tenant-isolation
  [ ] deployment 供應鏈      ← backend/07 llm-deployment-supply-chain
  [ ] agent prompt injection ← backend/07 llm-prompt-injection-in-agent
  [ ] log / PII 治理         ← backend/07 llm-log-and-pii-governance
  [ ] 偵測訊號               ← backend/07 llm-as-service-detection-coverage
  [ ] workload identity      ← backend/07 workload-identity-and-federated-trust
  [ ] 偵測平台               ← backend/07 detection-coverage-and-signal-governance
  [ ] IR 流程                ← backend/07 incident-case-to-control-workflow
  [ ] 合規                   ← backend/07 data-protection-and-masking-governance
```

## 小結

個人 dev → 團隊共用 → production 是三個複雜度等級不同的部署形態、安全議題的 framing 跟控制機制隨之升級。本模組前五章建立個人 dev 視角；要跨進團隊共用、補基本 auth + 入口 + TLS + secret + 內部供應鏈；要跨進 production、補多租戶 isolation + deployment 供應鏈 + agent 後果管理 + log/PII + 偵測 + IR + 合規。多數議題從 backend/07 既有卡片讀、LLM-specific 補充在 backend/07 的 LLM 相關章節。

本章是模組六的最後一章。下一步可以回到 [模組六 \_index](/llm/06-security/) 看其他章節、或進入 [Backend 模組七 資安與資料保護](/backend/07-security-data-protection/) 接 production 場景。
