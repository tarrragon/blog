---
title: "Mitigation 的 context-dependence：deployment 條件改變有效性"
slug: "mitigation-context-dependence"
date: 2026-05-01
weight: 103
description: "同一個資安 mitigation 在不同 deployment / runtime / scale / config 條件下、有效性差異很大、甚至完全失效。寫作時把 mitigation 描述成 universal（「使用 HTTPS 保護傳輸」「JWT 用簽章驗身分」）會跳過 context、讀者實作時用單一條件詮釋、deployment 條件不對時 mitigation silent 失效。每個 mitigation 必須附帶「成立條件」+「失效條件」+「deployment 變數列表」。"
tags: ["report", "事後檢討", "工程方法論", "資安", "Audit", "Context", "原則"]
---

## 核心原則

**資安 mitigation 的有效性不是 mitigation 本身決定的、是 mitigation × deployment 條件決定的。** 同一個 mitigation 在不同 deployment / config / scale / runtime 條件下、強度光譜從「完整擋」到「等同沒部署」都可能。寫作時忽略 deployment 變數、讀者實作時用最直覺條件詮釋、實際部署條件不對 mitigation silent 失效。

| 描述形態                                | 讀者實作判斷                | 部署條件不對的後果                |
| --------------------------------------- | --------------------------- | --------------------------------- |
| 「使用 X 保護 Y」（universal-flavored） | 在「正常」條件下 X 防 Y     | 條件不對、X silent 失效、無人警覺 |
| 「使用 X 保護 Y、條件 Z」               | 條件 Z 成立才用 X、否則補 W | 條件不對時 reader 知道補 W        |

差別在於：reader 在實作 review 階段有沒有 context 變數可檢查。

---

## 情境

資安 mitigation 在文獻 / 標準 / 教學裡常被描述成「方法 → 防什麼 threat」對應、跳過 deployment 條件這個變數。讀者讀完套到自己 deployment 上、條件可能不一致。常見的 context dimension 有四類：

### Context 維度 1：Config 完整性

Mitigation 通常需要多個 config 同時成立才有效、單一 config 不夠：

```text
HTTPS 防中間人：成立條件 = TLS + HSTS + cert pinning（針對重要 endpoint）+ CT log monitoring
                失效條件 = 只有 TLS、沒 HSTS → 第一次連線可被 downgrade
                          沒 cert pinning → 受信任 CA 簽出假 cert 可繞過
JWT 驗身分：    成立條件 = 簽章驗證 + 短 TTL + rotation + 安全儲存（HttpOnly cookie 或 secure storage）
                失效條件 = 簽章對但 TTL 太長 → token 被竊後長期可用
                          XSS 可讀取 → 簽章保護被繞過
                          沒 rotation → 一次外洩永久暴露
```

寫「使用 HTTPS」「使用 JWT」是把 mitigation 縮成單一 control name、reader 預設 default config、實際要 5-7 個 config 同時對才完整。

### Context 維度 2：Scale / 多實例

某些 mitigation 在單機 OK、多實例失效：

```text
Rate limit： 單實例 = local counter、per-IP rate 控管準確
            多實例 = 每實例各自 count、攻擊者打不同實例可繞過 N 倍上限
            修法 = 用 distributed counter（Redis / 共享 store）
Session 失效：單實例 = local session store、invalidate 即時
            多實例 = invalidate 訊號需 broadcast、舊 token 在其他實例還可用
            修法 = 用 stateless token + revocation list 或 共享 session store
```

Reader 看到「rate limit 防 brute force」、實作時若不知道 deployment scale、單實例 OK / 多實例 silent 失效。

### Context 維度 3：Runtime 環境

執行環境差異改變 mitigation 適用性：

```text
Cookie SameSite=Strict 防 CSRF：
  瀏覽器環境 = 有效（瀏覽器強制執行）
  Native app webview = 部分有效（依 webview 實作）
  Mobile in-app browser = 不一定有效（看實作）
  Server-to-server = 不適用（無 cookie / 無 SameSite 概念）
CSP 防 XSS：
  Modern browser = 有效
  舊瀏覽器（IE / 非 evergreen）= partial 或無效
  非 browser execution（Electron / native webview）= 看 implementation
```

### Context 維度 4：Threat actor 能力

Mitigation 的 work factor 跟 threat actor 計算能力對應：

```text
bcrypt（work factor = 10）：
  個人攻擊者 = 強保護
  Nation-state（GPU farm / FPGA）= 弱保護、需提高 work factor 或換 argon2
PBKDF2（100k iterations）：
  2010 年 = 強
  2026 年 = 弱（建議升級到 600k+ 或 argon2）
```

Threat actor 能力是 deployment 隨時間變化的變數、寫作時固定描述很快過時。

---

## 理想做法

每個 mitigation 段落明示三類條件：

### 三類條件模板

```text
[Mitigation X]
- 成立條件：[X 發揮設計強度需要的 config / scale / runtime / 其他 control 配套]
- 失效條件：[條件不對時 X 變成 etc 等同沒部署的具體情境]
- Deployment 變數：[實作時要檢查的 dimension list]
```

例（rate limit 防 brute force）：

```text
per-IP rate limit
- 成立條件：單實例部署 OR 多實例 + distributed counter（Redis / 共享 store）
- 失效條件：多實例 + local counter、攻擊者輪流打不同實例繞過上限
- Deployment 變數：實例數量、counter 部署位置（local / shared）、IP 來源真實性（NAT / proxy 後是否還能 distinguish）
```

例（HTTPS 防中間人）：

```text
HTTPS
- 成立條件：TLS + HSTS（避免首連線 downgrade）+ 受信 CA chain + 在重要 endpoint 配 cert pinning
- 失效條件：沒 HSTS → 首次連線 downgrade；CA 被攻陷 → 假 cert 可繞；no cert pinning + state-level CA 攻陷 → silent MITM
- Deployment 變數：HSTS preload / max-age 設定、cert pinning 範圍（哪些 endpoint）、CA list 是否最小化、CT log monitoring 是否到位
```

### Context 描述的層次規則

每個 mitigation 描述至少要有 deployment baseline 跟 stretch case：

| 層次              | 內容                                                                   |
| ----------------- | ---------------------------------------------------------------------- |
| Baseline 條件     | 最常見 deployment（單機 / 標準 config / mainstream browser）下的有效性 |
| Stretch 條件      | scale / 異常 runtime / 高能力 actor 下的衰減                           |
| Trigger condition | 何時 baseline 不夠、要升級到 stretch 的訊號                            |

baseline 給 reader 入門條件、stretch 給 reader 升級判準、trigger 讓升級成 actionable signal。

### 跟「規模改變可行性」的同骨

跟 [#89 Dataset 規模改變什麼可行](../dataset-scale-changes-feasibility/) 同骨——#89 在 dataset / index / cache 維度、本卡在 mitigation / config / scale 維度：

```text
#89:    < 1MB 無腦處理 → 1-10MB O(N) 可行 → > 100MB 強制 index
本卡：   單實例 local rate limit OK → 多實例需 distributed counter → 高 scale 需 token bucket + adaptive
```

「在 X 規模 / 條件下 Y 方法 OK」這個結構在資料處理跟資安都成立、是 deployment 變數驅動的工程光譜。

---

## 沒這樣做的麻煩

### 「正常條件下有效」silent 變成生產破口

讀者讀「使用 X 防 Y」、用自己 deployment 的 default config 實作、跑開發測試 OK、ship 進生產。生產可能是多實例 / 高 scale / 異常 runtime、X 在那條件下不成立、threat 進入。**Mitigation 在開發環境 silent 失效、生產環境 silent 失效——兩階段都沒訊號、直到事件**。

跟 [#100 false sense of security](../false-sense-of-security-as-primary-failure/) 同病：context 沒寫、reader 用最直覺條件詮釋、condition mismatch 不會被 catch。

### Mitigation 升級的時機不可 trace

威脅環境變化（actor 計算能力 / 攻擊變體 / scale 增長）需要 mitigation 跟著升級。Context 寫清楚的 mitigation 可 trace（bcrypt work factor 跟 actor 能力對應、定期 review）；context 含糊的 mitigation 不可 trace（「使用 bcrypt」變成 frozen「最佳實踐」、實際強度跟著時間 decay）。

### 跨環境 deployment 的 mitigation 假設衝突

同一份教學 / spec 套到不同 deployment（dev / staging / prod / 多區域 / 不同租戶）、若 context 沒寫、各 deployment 的 mitigation 強度差異被 silent。Audit 跨 deployment 時無法判定哪個強度最弱、整個系統的 baseline 取決於最弱 deployment、但沒人知道哪個是最弱。

---

## 跟其他抽象層原則的關係

| 原則                                                                                                                | 關係                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [#89 Dataset 規模改變什麼可行](../dataset-scale-changes-feasibility/)                                               | **同骨 sibling** — #89 是「資料規模 → 處理方法可行性」、本卡是「deployment 條件 → mitigation 有效性」、都是「條件變數驅動的方法光譜」                                        |
| [#87 Build-time vs Runtime 計算光譜](../build-time-vs-runtime-computation-spectrum/)                                | **同骨 spectrum** — #87 是計算位置光譜（build / runtime / hybrid）+ 四軸判準、本卡是 mitigation 條件光譜（baseline / stretch / trigger）+ 四 context 維度                    |
| [#43 最小必要範圍是 sanity 防線](../minimum-necessary-scope-is-sanity-defense/)                                     | **scope condition 同骨** — #43 把「scope」變成顯式 fact、本卡把「deployment 條件」變成顯式 fact；都在說「不顯式 = 失控的 default 詮釋」                                      |
| [#100 False sense of security 主要失敗模式](../false-sense-of-security-as-primary-failure/)                         | **#100 的 dimension 3** — context 不寫是 false sense 的第三大產地（dimension 1 = threat model 不對稱 / dimension 2 = mitigation 對位失效 / dimension 3 = context 沒寫）      |
| [#101 Threat model 明確性](../threat-model-explicitness/) + [#102 Mitigation 對位](../mitigation-threat-alignment/) | **本卡是 #101/#102 的 condition 維度** — #101 確立 in-scope threat、#102 確立 mitigation→threat 對位、本卡確立對位在 deployment 條件下的有效性；三者完整定義 mitigation 強度 |
| [#99 資安教學審查標準對應風險不對稱](../security-teaching-rigor-asymmetry/)                                         | 上游動機 — verifiability-first 的 dimension 3                                                                                                                                |

---

## 判讀徵兆

| 徵兆                                                           | 該做的事                                                                |
| -------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 「使用 X」單行 mitigation、沒寫 config / scale / runtime 條件  | 補三類條件：成立 / 失效 / deployment 變數                               |
| 標準引用（OWASP / RFC）抄整段、沒寫適用 deployment             | 標準是 universal-flavored、本地化 deployment context                    |
| Mitigation 描述沒提 work factor / iteration count / 強度參數   | 補強度參數 + 對應 actor 能力的 trigger condition                        |
| 多實例 / 多區域部署、rate limit / session 描述沒提 distributed | 補多實例 context、明示 local vs distributed 的差異                      |
| 「在 modern browser」「在 standard config」沒展開的修飾詞      | 列舉 modern / standard 涵蓋什麼、不涵蓋什麼                             |
| Threat actor 能力 / 計算成本沒列                               | 補 actor model、區分個人 / 組織 / nation-state 的 mitigation 強度       |
| 「之後 deployment 不一樣再說」                                 | 是 [#72](../external-trigger-for-high-roi-work/) 結構性跳過、補 trigger |

---

## 適用範圍與邊界

- **適用**：資安 mitigation 的所有論述（auth / crypto / 傳輸 / 防護 / scale-sensitive control）；任何「方法有效性受部署條件影響」的領域（concurrency primitive 在不同 memory model / DB transaction 在不同 isolation level / consensus 演算法在不同 network partition 假設）
- **不適用**：純歷史 / 概念介紹（不教 mitigation deployment）、研究探討（讀者預期自行 explore condition）
- **邊界**：「Context-dependence 顯式」≠「窮舉所有 deployment 排列組合」——只列 reader 直覺會誤判的 dimension（最常見 deployment 跟最常見變體）、不必涵蓋整個 deployment space；判別準則：「reader 用 default 條件詮釋會不會 silent 失效」——會 → 補 context、不會 → 不必補
- **過度條件化反例**：每個 mitigation 列 deployment matrix（10 個 dimension × 5 個值 = 50 個 case）、文章變 deployment guide、不是教學；條件描述的投資量級對應 mitigation 在系統的責任比重——核心 control（auth / crypto）值得三類條件完整、輔助 control 只列 baseline + 一個 stretch case 即可

本卡是資安 audit 第三個維度（context-dependence）、配 [#101](../threat-model-explicitness/) threat model + [#102](../mitigation-threat-alignment/) 對位、後續 #104 citation 形成完整 audit dimension 集合。
