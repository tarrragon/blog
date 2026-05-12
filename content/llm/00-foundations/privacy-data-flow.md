---
title: "0.7 隱私 / 資安的資料流原理"
date: 2026-05-11
description: "從「位置」到「資料流」的思考升級：信任邊界、合約模型、零信任原則套用到 LLM 工作流"
tags: ["llm", "foundations", "privacy", "security"]
weight: 7
---

[0.6 判讀框架五](/llm/00-foundations/info-judgment-frames/) 建立的反射是「隱私是資料流、不是位置」。本章把這個 framing 展開成可操作的設計原則：信任邊界該怎麼劃、本地推論 vs 雲端的合約模型差異、零信任原則套用到 LLM 工作流的具體做法、NDA / 企業合規場景的判讀框架。

本章寫的是「無論工具怎麼演變、隱私設計都該這樣思考」的原理層。具體合規法規條文（GDPR、HIPAA、各地新法）、特定工具的 telemetry 設定（每家半年一變）不在本章——這些隨時間變、用本章建立的 framework 重新評估就好。

## 本章目標

讀完本章後、你應該能：

1. 用資料流圖描述自己的 LLM 工作流、辨識每個 hop 的信任邊界。
2. 區分「物理保證」與「合約保證」兩種隱私模型的取捨。
3. 把零信任原則套用到 LLM 系統設計。
4. 對 NDA / 企業合規場景做出有條理的判讀、不只看「是否本地」。

## 從「位置 Thinking」到「資料流 Thinking」

「跑在本地、所以隱私」這個直覺假設「位置」是隱私的唯一變數。實際上隱私風險來自整條資料流的每個節點、位置只是其中一個維度。

把問題從「我的 prompt 是否離開機器」改成「我的 prompt 從打字到最終結果、經過哪些 process、儲存在哪、誰能看到」。後者覆蓋面廣得多：

- prompt 在 IDE 內被 cache？
- IDE 有沒有開雲端同步？
- 推論伺服器 log 留多久？
- 對話歷史存到哪？
- 第三方 plugin 有沒有偷 access prompt？
- 結果寫到磁碟後、有沒有被自動備份到 iCloud / Dropbox？

「位置 thinking」對所有這些都看不到——只要推論在本地就覺得安全。「資料流 thinking」把整條 hop 攤開、每個節點單獨評估。

這個 shift 是隱私設計的根本前提。沒做這個 shift、其他設計都建立在錯誤假設上。

## 信任邊界的定義

LLM 工作流通常跨多層信任邊界（IDE / 推論伺服器 / 雲端同步 / 第三方 plugin / LAN）、隱私設計的第一步是把這些邊界明確畫出來。信任邊界（trust boundary）的概念來自系統安全設計：「誰能看到什麼資料」的明確分隔。穿越邊界的資料需要明確的授權跟稽核；同邊界內的資料假設安全。

本地推論的天然信任邊界是「我的 Mac」——資料在這個邊界內預設安全（除非機器本身被入侵）。但實際 LLM 工作流會穿透這個邊界：

- **雲端同步穿透**：VS Code 同步 settings、Notion 備份對話、iCloud 同步文件——資料從 Mac 走到雲、信任邊界被擴展到供應商。
- **Telemetry 穿透**：IDE plugin、[推論伺服器](/llm/knowledge-cards/inference-server/)、作業系統都可能送遙測資料、含 prompt 片段 / metadata。
- **第三方 plugin 穿透**：裝的 VS Code extension、瀏覽器 plugin 都可能 access 同個 prompt context。
- **網路 expose 穿透**：`OLLAMA_HOST=0.0.0.0` 把本地伺服器暴露到 LAN、信任邊界從「我的 Mac」擴展到「整個區網」。

LLM 工作流通常有多層信任邊界、跟「我在本地跑」的單純直覺不一定一致。設計隱私時、先把所有信任邊界畫出來、再評估每個邊界的「誰能看到、能看到什麼」。

信任邊界的判讀問題：

- 這個 process 屬於哪個邊界內？
- 跨邊界傳資料需要什麼授權？
- 邊界外的 component 如果被入侵、能 access 到什麼？

這幾個問題答得清楚、隱私設計就有 ground truth；答得模糊、設計就建立在假設上。

## 本地 vs 雲端的合約模型

本地推論跟雲端推論的隱私保證來自不同模型：

### 物理保證（本地）

本地推論的隱私保證是「物理上資料留在這台機器」、可技術觀察：

- 用 `lsof`（list open files、看 process 持有的網路 socket）看推論伺服器的網路連線、確認沒對外送資料。
- 用 `tcpdump`（系統封包擷取工具）監聽流量、確認 prompt 沒外洩。
- 看磁碟 IO、確認對話歷史沒被寫到雲端同步資料夾。

**這些工具的能力邊界**：`lsof` / `tcpdump` 給的是「常態流量觀察」、不是完整安全證明。編譯期注入、kernel-level exfiltration、DNS tunneling 等繞過手法仍可能規避這些觀察視角。國家級威脅模型或高 stakes 合規場景下、要再加程式碼簽章驗證、SELinux / EndpointSecurity policy、出口防火牆等更深的控制；個人 / 中小企業場景下、這三個工具的觀察通常足以建立日常的信心。

物理保證的特性：

- **可單機驗證**：不需要信任供應商、能用本地工具觀察流量。
- **能力上限受硬體限制**：本地模型受 Mac 算力跟記憶體限制、能力比雲端旗艦低一個量級。
- **不依賴合約承諾**：供應商有沒有承諾「不訓練」「zero-retention」都跟本地推論無關——資料本來就沒去那裡。

### 合約保證（雲端）

雲端推論的隱私保證是「供應商承諾不留資料、不訓練、合規 X 規範」、技術上單機不可驗證、靠合約與 audit 支撐：

- Anthropic、OpenAI 的企業方案明示 zero-retention、不訓練選項（2026 年 5 月當時的 ToS、雲端 ToS 半年一變、實際採用前以最新版為準）。
- SOC 2、ISO 27001、HIPAA BAA 等合規認證提供第三方 audit。
- 供應商的 ToS / privacy policy 是法律承諾、違反可訴訟。

合約保證的特性：

- **不可單機驗證**：要信任供應商沒違反承諾、加上第三方 audit 補強。
- **能力沒上限**：能用上雲端最強模型（GPT-5、Claude Sonnet 4.6、Opus）、沒有硬體限制。
- **受法律管轄影響**：供應商所在管轄區的法律、未來變動會影響保證強度（如政府要求供應商交資料）。

### 兩種模型的取捨

兩種模型不是「誰比較好」、是「在什麼情境下哪個適合」：

- **隱私要求極高 + 模型能力夠用**：本地。物理保證可驗證、不需信任供應商。
- **能力要求極高 + 隱私要求中等**：雲端 + 合約保證。Claude / GPT 旗艦的能力本地短期內追不上。
- **合規場景**：看具體規範要求。HIPAA、PCI-DSS 等場景雲端 + BAA / DPA 合約 + technical control 是主流方案、不一定要本地。
- **NDA + 客戶明示不得送雲**：本地是預設、合約保證對「不得送雲」這條沒幫助。

判讀「該選哪邊」不是 binary、是 spectrum：許多場景混用、敏感任務本地、需要能力的任務雲端 + 合約保證。混用模式有一個隱形 leak 風險：同一個 IDE 同時接本地與雲端 backend、prompt routing 設錯就會把該走本地的內容送到雲端。實作時要明確隔離（不同 workspace / 不同帳號 / 不同 plugin set）、用配置強制路由、而非依賴每次手動切換。

## 零信任原則套用到 LLM 工作流

零信任（zero trust）的核心是「不假設任何 component 是 trusted、每個 hop 都重新驗證」。傳統信任模型假設「邊界內安全」、零信任假設「邊界本身可能被穿透」、每次 access 都驗證。

套用到 LLM 工作流的具體實踐：

### 不信任預設配置

每個 component 的預設配置往往不是「最隱私」、是「最方便」。`OLLAMA_HOST` 預設 `127.0.0.1` 還算安全、但很多工具預設打開 telemetry、預設同步到雲端。在 NDA / 合規場景下、所有 component 的隱私相關設定通常需要逐項 review、預設值會根據場景調整。

### 每個 hop 都評估

不只是「我用 Ollama 所以隱私」、要評估從打字到結果的每個 hop：IDE telemetry、plugin 行為、推論伺服器 log、對話歷史儲存、檔案系統位置、雲端同步範圍。任何一個 hop 預設設定「外洩」、整條鏈的隱私就破。

### 最小權限

每個 component 只給它必要的 access：

- 推論伺服器：不需要存 prompt 歷史就關 log。
- IDE plugin：不裝沒驗證的 third-party plugin。
- 雲端同步：個人場景白名單同步是低成本 default、NDA / 合規場景直接排除整個 LLM 相關目錄。

「最小權限」需要主動設計、不會自動發生——預設都是「方便優先」。

### 認假設、不認直覺

「跑在本地所以安全」是直覺、不是已驗證的事實。零信任要求每個假設都跑一次 audit 確認、用觀察取代感覺。

## 資料流分析的具體做法

把抽象原則落地、要做資料流分析：把整個工作流畫成 graph、每個 node 是 process、每個 edge 是資料流動、標示資料類型跟流向。

具體步驟：

1. **列出所有節點**：使用者、IDE、IDE plugin、推論伺服器、模型、磁碟、雲端服務、第三方 service。
2. **畫出所有 edge**：誰送資料給誰、什麼類型的資料、什麼觸發。
3. **標示信任邊界**：哪些節點屬同一個邊界、邊界之間的 edge 標出來。
4. **每個跨邊界 edge 評估三個問題**：
    - 誰能看到流過這條 edge 的資料？
    - 儲存多久？
    - 會不會再轉送出去？
5. **找出風險集中點**：常見集中點是 IDE telemetry、雲端同步、第三方 plugin。

這個分析做完、隱私風險不再是抽象的「會不會洩漏」、是具體的「哪個 edge 在洩漏什麼」。修補策略也跟著具體：關 telemetry、移除特定 plugin、改設定。

實務做這個分析、第一次通常會發現預期外的 edge——例如「我以為對話歷史只在本地、結果發現 IDE 的 sync settings 把它送到雲」、「我以為這個 plugin 只 access code、結果它也送 prompt 給自家 analytics」。

## NDA / 企業合規場景的判讀框架

NDA 跟企業合規場景的隱私要求比個人使用嚴格、判讀方式：

### NDA 場景

- **核心要求**：客戶明示「不得送第三方 AI 服務」、本地是預設選擇。
- **不夠的地方**：本地推論只保證模型呼叫不出去、要 audit 整條資料流（IDE telemetry、雲端同步、plugin 行為）。
- **常踩的坑**：以為 Ollama 跑就安全、但 Cursor / Copilot 同時開著還送 prompt 給自家 service、NDA 已穿透。
- **強化做法**：NDA 客戶程式碼專案開獨立 IDE workspace、停雲端同步、移除第三方 plugin、明確隔離。

### 企業合規場景

不同規範保護的核心點不同、每條規範需對應到該規範要求的 control、避免用單一 mitigation 一網打盡的做法：

| 規範    | 核心保護點                                 | 常見對位 control                                                   |
| ------- | ------------------------------------------ | ------------------------------------------------------------------ |
| HIPAA   | 健康資料（PHI）的接觸與儲存                | 雲端供應商簽 BAA（Business Associate Agreement）+ 加密 + audit log |
| PCI-DSS | 信用卡 cardholder data 的網路 segmentation | 把處理卡號的環境隔離、避免任意 process 接觸                        |
| SOC 2   | 服務組織的安全 / 可用 / 機密性整體控制     | 跨組織技術 + 流程控制、用第三方 audit 驗證                         |
| GDPR    | 資料主體的存取 / 刪除 / 移植權             | DPA（Data Processing Agreement）+ 資料分類 + 主體請求流程          |

判讀流程：列合規要求 → 對應資料流節點 → 找出缺哪個保護 → 補上技術或合約控制。本地推論滿足「資料留在內部」這條、但通常仍需要 audit log、access control、retention policy 等補強；雲端 + BAA / DPA + zero-retention 是另一條合規路徑、看規範允許哪條再做選擇。

### 個人 + 一般工作場景

- 多數場景隱私風險中等、合理控制就夠。
- 預設關掉明顯外洩管道（telemetry、雲端同步敏感內容）、敏感任務本地、其他雲端、就 cover 90% 場景。
- 過度設計反而生產力大幅下降、得不償失。

判讀框架的核心不是「該不該做隱私」、是「該做到什麼程度」。NDA / 合規場景要做到嚴、個人場景做到合理、過度都是浪費。

## 常見的隱私邊界穿透

下列五個穿透模式都符合「位置看似安全、資料流卻外洩」的 pattern、即使用本地推論仍會破隱私：

### IDE 雲端同步

VS Code、JetBrains 系列預設可能開 settings sync、把對話歷史、recent files、command history 同步到雲。對話歷史尤其敏感——可能含 prompt 跟 LLM 回應全文。

判讀訊號：登入帳號後、跨機器 settings 自動同步——這條 pipe 通常也帶其他資料。

緩解：明確查看 sync 範圍、敏感場景關閉 sync 或開選擇性 sync（只同步配置、不同步歷史）。

### 第三方 plugin 偷送 prompt

裝 VS Code extension 時、權限模型較寬：理論上 plugin 能 access 整個 workspace、含 prompt 跟 LLM 回應。多數 plugin 安全、但供應鏈攻擊或惡意 plugin 存在。

判讀訊號：plugin 不是 verified publisher、下載量少、permission 列表廣。

緩解：敏感場景只用 verified plugin、定期 audit 已裝 plugin、移除不必要的。

### Open WebUI 對話歷史備份

Open WebUI（常見的本地 Web 對話介面、通常以 Docker 部署）把對話歷史存本機 SQLite、預設安全。但很多人把 `~/.openwebui` 放在 Dropbox / iCloud 同步目錄、歷史間接同步到雲。

判讀訊號：home directory 整個被雲端服務同步。

緩解：明確排除 LLM 相關目錄、或把 LLM 資料移到不被同步的位置。

### `OLLAMA_HOST=0.0.0.0` 暴露區網

把 Ollama 從 [`127.0.0.1`](/llm/knowledge-cards/port-and-localhost/) 改成 `0.0.0.0` 是常見配置（讓區網其他機器接）、但等於把本地 LLM 暴露在 LAN 上。風險視 LAN trust level 而定：純自家信任裝置的家用網路風險低、有 IoT / 訪客機 / 公共 Wi-Fi 的 LAN 環境風險顯著上升（IoT 裝置常被植入、預設要放在 untrusted segment、用 VLAN 或 firewall 隔離後再評估能否互通）。

判讀訊號：能從另一台機器 curl `<你的 Mac IP>:11434` 成功。

緩解：純自家信任裝置的 LAN 接受、混合 trust LAN 用防火牆規則限定 source IP、公共 Wi-Fi 改回 `127.0.0.1` 或用 SSH tunnel 隧道到遠端機器。

### IDE Plugin 同時送雲

Cursor 預設 telemetry 強、Copilot 本來就送 prompt 給 GitHub。即使在這些 IDE 內用 Continue.dev 接本地 Ollama、IDE 本身可能仍送 prompt 給自家 service。

判讀訊號：IDE 是「雲端 AI 為主」的工具、本地 LLM 接入只是附加功能。

緩解：敏感場景用「本地 AI 為主」的 IDE（如 VS Code + Continue.dev）、不用混合的雲端 IDE。

## 何時過時 / 何時不過時

**不會過時的部分**：

- 「資料流 thinking」對「位置 thinking」的優越性。
- 信任邊界的定義跟畫法。
- 物理保證 vs 合約保證的雙模型 framing。
- 零信任原則的四個套用實踐。
- 資料流分析的 5 步驟方法。
- NDA / 合規 / 個人三類場景的判讀框架。

**會變的部分**：

- 具體合規法規（GDPR、HIPAA、CCPA、各國新法會持續更新）。
- 特定工具的隱私行為（IDE / 雲端服務的 ToS、telemetry policy 會調整）。
- 雲端供應商的合約細節（BAA / DPA / SCC 條款會 evolve）。
- 「常見穿透模式」的具體例子（會隨工具生態變）。

新工具、新法規、新雲端服務出來時、回到本章的方法重新跑一遍資料流分析、信任邊界評估——framework 不變、實例更新。

## 小結

LLM 隱私設計從「位置 thinking」升級到「資料流 thinking」、辨識整條資料流的信任邊界、用零信任原則重新評估每個 hop。本地推論提供物理保證（可技術驗證、能力上限受硬體限制）、雲端 + 合約提供合約保證（不可單機驗證、能力無上限），兩種模型按場景組合。NDA / 合規 / 個人場景的判讀程度不同、過度跟不足都是浪費。

讀到這裡、模組零的心智模型完整收尾。下一步：[模組一：本地 LLM 服務的安裝與應用](/llm/01-local-llm-services/)、把模組零建立的心智模型落到實際操作。
