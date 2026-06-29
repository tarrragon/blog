---
title: "Shared Secret 安全輪替設計：雙密過渡期、自動化與緊急流程"
date: 2026-05-18
draft: false
description: "系統間 Shared Secret 輪替的核心機制：dual-secret rollover、自動化工具比較（AWS Secrets Manager / Vault / GCP）、緊急 rotation 流程與多 client 環境的失敗模式。"
tags: ["security", "secret-management", "rotation", "operations", "backend"]
---

## Shared Secret Rotation 這篇要解決什麼

Shared Secret rotation 的核心責任是讓 credential 換新時維持可用性、可追蹤性與可撤銷性。它表面上像是一行 SQL update，實際上牽涉 server 與多個 client 的切換時序：

- 兩邊不同時切、就斷線
- 多 client 場景下、總有一兩個沒升級
- 緊急洩漏要立即撤換、同時控制服務中斷範圍
- Rotation 中途失敗、舊新 secret 都不通

這些是維運層的真實痛點。只說「定期 rotate your secret」只能描述目標，還需要雙密期、測試、監控、通知與回退流程，才能把 rotation 變成可執行的操作契約。

本文聚焦三件事：

1. **雙密過渡期**：怎麼讓 client 可以在任意時點切換、不會斷線
2. **自動化工具**：AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager 各自的 rotation 機制
3. **緊急 vs 定期**：兩種流程的差異、何時用哪個

> **本文位置**：本文是 [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) Layer 2 的深入篇。主文聚焦「為什麼系統間要獨立 credential」、本文聚焦「Shared Secret 輪替的工程實務」。

---

## Rotation 解決什麼威脅

Rotation 是縮短 secret 暴露窗與清理殘留 access 的 lifecycle 控制。它降低三種具體威脅：

| 威脅                    | Rotation 怎麼緩解                                                   |
| ----------------------- | ------------------------------------------------------------------- |
| **未察覺的洩漏**        | Secret 可能已被外洩、定期換能限制攻擊者使用的時間窗                 |
| **離職員工殘留 access** | 員工離職後系統 access 沒撤徹底、rotation 把該員工知道的 secret 變廢 |
| **長期暴露的 metadata** | Secret 越久、log / backup / git history 留存的副本越多              |

Rotation 本身有成本與風險，切換設計不完整時會造成斷線。所以實務目標是「在切換可控的前提下，選一個能接受的頻率」。

常見定期頻率：

| 業界場景             | 典型頻率                   |
| -------------------- | -------------------------- |
| 一般 SaaS            | 90 天 / 180 天             |
| 金融、醫療           | 30 天 / 90 天              |
| 高敏感（國防、政府） | 7 天 / 14 天、或事件觸發   |
| 純內部、低風險       | 半年 / 一年、或永不 rotate |

> **頻率取決於威脅模型與操作能力**：NIST SP 800-63B 對多數場景認可 30-90 天足夠、過於激進的 rotation 反而提高出錯機率。7-14 天適用於合規條款明文要求或私鑰可硬體保護的場景；多數 SaaS 可以停在 30-180 天區間。

「事件觸發才換」也有合理情境。純內部 cron job、secret 外流管道少、rotation 成本大於風險時，可以選擇以事件觸發取代固定排程；重點是留下 owner、inventory 與重新評估條件。

---

## 核心機制：雙密過渡期（Dual-secret Rollover）

### 直接 atomic 切換的失效點

最直覺的 rotation 流程是：

```text
T0: 兩邊都是 secret_v1
T1: server 端換成 secret_v2
T2: client 端換成 secret_v2
```

失效點出在 T1 到 T2 之間：server 只認 v2，但 client 還在用 v1，這段窗口內的 request 都會 401。即使窗口只有幾秒，production 流量也可能產生大量錯誤。

更糟的是「client 更新後忘了 reload process」這種情境 — 配置檔已改、但跑著的 server / worker process 還握著舊 secret 在記憶體裡、直到下次重啟才生效。窗口可能拉長到幾分鐘到幾小時。

### 解法：server 端同時接受新舊兩把

雙密過渡期把 rotation 分成 3 個階段：

```text
T0：穩態
  server: [v1]
  client: [v1]
  狀態：v1 工作

T1：發新 secret、server 雙密期開始
  server: [v1, v2]   ← server 同時接受 v1 跟 v2
  client: [v1]
  狀態：兩個都 work、client 還沒切

T2：通知 client 切到 v2
  server: [v1, v2]
  client: [v2]       ← client 升級、開始用 v2
  狀態：v2 work、v1 也仍 work（過渡期）

T3：確認所有 client 都切完、關閉 v1
  server: [v2]       ← 移除 v1
  client: [v2]
  狀態：穩態、只 v1 失效
```

關鍵在於 **server 在 T1-T3 之間同時接受兩把** — 不論 client 在這段期間用哪一把都能通過驗證。client 可以在自己的時程內升級、不需要跟 server 切換同步。

### 雙密期的長度設計

雙密期是一個可用性與暴露窗的取捨。兩把同時有效時，系統需要同時保護兩把 secret，也需要追蹤兩個版本的使用比例；時間拉太短會造成 client 來不及切換，時間拉太長會擴大舊 secret 的有效窗口。

設計建議：

| 場景                    | 雙密期長度建議           |
| ----------------------- | ------------------------ |
| 純內部、可強制升級      | 24-48 小時               |
| 對外 client、需要溝通   | 7-14 天                  |
| 大量第三方整合          | 30-90 天 + 多次提醒      |
| 緊急 rotation（已洩漏） | 盡量縮短、視覆蓋速度而定 |

監控指標：在雙密期內、應該追蹤「用 v1 vs 用 v2 的 request 比例」 — 當 v1 比例降到 0%、且持續穩定一段時間後、才安全地關閉 v1。

### 怎麼實作「同時接受兩把」

實作模式有兩種：

#### 模式 A：array 比對

```python
VALID_SECRETS = [
    os.environ['SHARED_SECRET_CURRENT'],
    os.environ['SHARED_SECRET_PREVIOUS'],  # 可選、若在雙密期
]

def verify(received):
    for secret in VALID_SECRETS:
        if not secret:
            continue
        if hmac.compare_digest(secret, received):
            return True
    return False
```

這個模式適合內部固定夥伴與少量服務，因為驗證邏輯簡單、沒有額外狀態。主要風險是兩把 secret 都要部署到 server，env var / config 變多，且每個 instance 都要確認讀到相同版本。

#### 模式 B：secret store + version

```python
def verify(received):
    current_version = secret_store.get_version('shared_secret', 'current')
    previous_version = secret_store.get_version('shared_secret', 'previous')
    return hmac.compare_digest(current_version, received) or \
           hmac.compare_digest(previous_version, received)
```

這個模式適合對外 API 或 client 數量較多的系統，因為 secret 集中管理、版本狀態可查。主要風險是驗證流程依賴 secret store，需要設計 cache、fallback 與 store 失效時的行為。

對外開放 API 通常用模式 B、可結合 AWS Secrets Manager / Vault 等工具。內部固定夥伴系統可以用模式 A 起步、複雜後再遷移。

---

## 自動化 Rotation 工具

純手動 rotation 在 client 數量增加後不可持續 — 自動化工具的價值是把「**產生新 secret → 部署到 server → 通知 client → 撤銷舊 secret**」整套流程程式化。

### AWS Secrets Manager

機制：

- 註冊一個 **Rotation Lambda**、AWS 排程觸發（例如每 90 天）
- Lambda 跑 4 階段流程：`createSecret` → `setSecret` → `testSecret` → `finishSecret`
- 每個階段都有 retry、失敗會回到上一個穩態

Lambda 範例責任分工：

| 階段           | 動作                                                  |
| -------------- | ----------------------------------------------------- |
| `createSecret` | 產生新 secret、存到 AWSPENDING 版本                   |
| `setSecret`    | 把新 secret 部署到目標 service                        |
| `testSecret`   | 用新 secret 跑驗證 request                            |
| `finishSecret` | 把 AWSPENDING 升級為 AWSCURRENT、舊版改為 AWSPREVIOUS |

雙密期天然存在：AWSCURRENT + AWSPREVIOUS 兩個 staging label 同時可讀。Client 在 rotation 進行中、可以拿到 AWSPREVIOUS 作為 fallback。

適合場景：AWS 生態系、目標 service 是 RDS / Redshift / DocumentDB（有 native rotation Lambda template）或自定義（custom Lambda）。

### HashiCorp Vault

Vault 有兩種 rotation 策略：

**Static Secrets + Rotation Periodic**：傳統 shared secret、Vault 每 N 天自動換、puts 到 vault path、client poll 拿。

**Dynamic Secrets**：Vault 不存 long-lived secret、每次 client 請求時臨時產生（DB credential、AWS IAM credential 等）、TTL 短（小時到天）、過期即廢。Dynamic secret 沒有 rotation 概念 — 因為每個 secret 都只活一小段時間、洩漏窗本來就有限。

| 模式              | 適合                          | 限制                                  |
| ----------------- | ----------------------------- | ------------------------------------- |
| Static + Periodic | 跨組織 API、需可預測的 secret | 仍需 client 端處理雙密期              |
| Dynamic           | 內部 service 互呼、DB access  | 目標系統要支援 short-lived credential |

適合場景：multi-cloud、不想綁 AWS、需要 dynamic secret 跨多種 backend。

### GCP Secret Manager

機制較簡單 — Secret Manager 提供 **versioning**、每個 secret 有多個 version、client 可指定要「latest」還是特定 version。

Rotation 流程通常自己實作（GCP 沒提供類似 AWS 的 Rotation Lambda template）：

1. `addSecretVersion(name, new_secret)` — 加新 version
2. 部署到 server（server 同時讀 latest + previous）
3. 通知 client / 等 client 升級
4. `destroySecretVersion(name, old_version)` — 撤銷舊 version

雙密期靠 client 端邏輯（同時試 latest 跟 previous）實現。

適合場景：GCP 生態系、自有 rotation 邏輯不想被 vendor opinion 綁住。

### 三者比較

| 維度               | AWS Secrets Manager          | HashiCorp Vault             | GCP Secret Manager               |
| ------------------ | ---------------------------- | --------------------------- | -------------------------------- |
| 排程觸發           | 內建                         | 內建（periodic）            | 不內建（自己排 Cloud Scheduler） |
| 雙密期支援         | AWSCURRENT / PREVIOUS labels | Static 需自寫、Dynamic 不需 | Version-based                    |
| Dynamic credential | 需 custom Lambda             | Native support              | 不支援                           |
| 跨雲 / 跨 region   | AWS-only                     | 跨雲                        | GCP-only                         |
| 維運成本           | 低（managed）                | 高（自管 Vault cluster）    | 低（managed）                    |

### 自建 rotation 系統的最小元件

小規模系統可以自建最小 rotation 元件，前提是 secret 系統本身也被視為敏感基礎設施。最小元件包含：

1. **Secret 存儲**：DB table `secrets(id, version, value, created_at, retired_at)`
2. **發放 API**：`GET /secrets/current` 回 latest active version
3. **驗證邏輯**：應用層讀 current + previous 兩個 active version
4. **排程**：cron job 觸發 `rotate(secret_name)` — 產新 version、標記舊版 retired、設 retired_at
5. **監控**：log 每個 version 被驗證的次數、舊版降到 0 後關閉

這個方案適合內部小規模系統。判斷是否可行時，要同步檢查 DB encryption at rest、access log、權限分離與備援；否則自建系統可能把 rotation 風險轉移成 secret store 風險。

---

## 緊急 rotation：洩漏發生時的流程

### 跟定期 rotation 的差異

定期 rotation 目標是「**不中斷服務**」、所以雙密期長、給 client 充分時間切換。

緊急 rotation 目標是「**最快讓舊 secret 失效**」 — 即使犧牲部分可用性也要立刻撤銷。兩者流程完全不同：

| 維度          | 定期 rotation         | 緊急 rotation                |
| ------------- | --------------------- | ---------------------------- |
| 觸發          | 排程                  | 事件（洩漏、員工離職、被盜） |
| 優先級        | 不中斷服務            | 立即撤銷舊 secret            |
| 雙密期        | 長（天到月）          | 短（小時、甚至不容忍）       |
| 通知方式      | 文件、email、提早提醒 | 直接 push、必要時打電話      |
| Client 不升級 | 等                    | 強制斷線                     |

### 緊急 rotation 流程模板

```text
T0: 偵測或回報洩漏
   ↓
T0+0~15min: 評估
   - 確認洩漏範圍（哪些 secret、影響哪些 client）
   - 評估「立即斷舊 secret」對 production 的影響
   - 決定是否走緊急流程 vs 縮短的定期流程
   ↓
T0+15min~1hr: 部署新 secret
   - 產生新 secret
   - 部署到 server、開啟雙密期
   - 主動 push 新 secret 給已知 client（內部用 channel 通知、外部 client email + dashboard）
   ↓
T0+1hr~24hr: 強制切換
   - 監控用舊 secret 的 request 比例
   - 跟未升級的 client 個別聯繫
   - 視情境設「強制斷線時間點」並提早警告
   ↓
T0+24hr~72hr: 撤銷舊 secret
   - 即使仍有 client 在用舊 secret、也斷
   - 接受部分服務中斷、優先於 secret 繼續暴露
   ↓
事後: 檢討
   - 洩漏怎麼發生（log 翻查、code audit）
   - 偵測機制能否更快
   - 流程哪裡可以改進
```

關鍵權衡：**「斷線成本」vs「secret 繼續暴露的損害」**。對金融、醫療等高敏感場景、寧可斷線；對非關鍵內部服務、可能可以拉長雙密期。沒有通用答案、要場景判斷。

### 偵測洩漏的訊號

緊急 rotation 的前提是「**知道洩漏發生了**」 — 但很多洩漏直到攻擊者開始用 secret 才被發現、間隔可能是幾個月。

主動偵測手段：

| 訊號                          | 怎麼偵測                                        |
| ----------------------------- | ----------------------------------------------- |
| **Secret 出現在公開 repo**    | GitHub Secret Scanning、GitGuardian、TruffleHog |
| **異常使用 pattern**          | 異常時間、異常 IP、異常 request 量              |
| **多個 IP 同時用同一 secret** | 應用層 log 分析、SIEM 工具                      |
| **離職員工觸發 access**       | 跟 HR 系統整合的 access review                  |

把這些設成監控告警、是降低「洩漏到察覺」窗口的關鍵。

---

## 多 client 的同步難題

### 問題本質：client 不在你的控制範圍

對外開放 API 的場景，Shared Secret 散落在第三方 client 的 server。Rotation 因此變成「怎麼讓第三方在你的時程內配合」的協調問題，不只是技術問題。

常見痛點：

- 通知 email 進垃圾匣、第三方沒看到
- 第三方的工程師離職、新接手者不知道有 rotation 排程
- 第三方的 deploy 流程慢、提前一週通知還是來不及
- 第三方根本不在線（小型客戶、半年才用一次 API）

### Grace period 設計

Grace period 是「**舊 secret 撤銷後、給 client 緩衝期重新申請**」的機制。比硬性 deadline 更彈性：

```text
T0: 公告 rotation、雙密期開始
T0+30天: 雙密期結束、舊 secret 撤銷
T0+30~60天: Grace period
   - 用舊 secret 的 request 回 410 Gone（或 401 + 可讀的 error code，視 API 慣例）+ 連結到 "secret expired" 頁
   - 提供 self-service 重設 secret 的流程
   - 仍然斷線、但 client 知道怎麼自己救
T0+60天: 完全關閉、需要重新申請新 client account
```

Grace period 的關鍵是在拒絕舊 secret 的同時，提供足夠資訊讓 client 自助修復。判讀訊號是錯誤回應是否能指出 secret 已過期、去哪裡重設、何時完全關閉；若只回無上下文的 401，client 仍會被導向錯誤排障路徑。

### 強制升級的工具

對於必須統一升級的場景（例如安全合規要求）、有幾種強制手段：

| 手段                      | 怎麼運作                                    | 適合                        |
| ------------------------- | ------------------------------------------- | --------------------------- |
| **HTTP 410 + 訊息**       | 舊 secret 不只 401、回 410 + 升級指引       | 一般對外 API                |
| **暫時降級而非斷線**      | 舊 secret 仍 work、但限流 / 降級權限        | 重要 client、寧可降級不要斷 |
| **個別溝通 + 客製化期限** | 對大 client 個別協商 deadline               | 高價值合作夥伴              |
| **合約強制條款**          | 簽約時就寫清楚「Y 年內必須能配合 rotation」 | B2B SaaS                    |

---

## 失敗模式與緩解

### 失敗 1：雙密期太短、client 沒升級

**症狀**：rotation 後第二週，某 client 開始 401，才發現他沒收到通知或尚未升級。

**緩解**：

- 雙密期至少覆蓋「最大已知 client 的 deploy cycle」
- 雙密期內監控「用舊 secret 的 client 數量」、降到 0 才關
- 緊急 rotation 例外、要事先評估可接受的斷線成本

### 失敗 2：rotation 中斷、新舊都不通

**症狀**：deploy 新 secret 到 server 中途失敗、一半 server 是新、一半是舊 — request 隨機 401。

**緩解**：

- 部署用 rolling update、確認每個 instance 都生效再進下一個
- 部署前確認「server 是雙密 mode」、即使部署到一半也能容錯
- 保留快速 rollback 機制（10 分鐘內能 revert）

### 失敗 3：新 secret 沒測通就上線

**症狀**：新 secret 部署完、第一個 client 試了發現格式不對 / 長度限制 / 特殊字元編碼問題、大量 401。

**緩解**：

- Rotation 流程加 `testSecret` 階段（AWS Lambda 模式）— 切換前用新 secret 跑一輪驗證 request
- Staging 環境先跑完整 rotation 流程、再上 prod
- 新 secret 的 format 跟舊一致（同長度、同字元集）、減少 client 端的 parsing 風險

### 失敗 4：Rotation 缺少 owner、secret 長期暴露

**症狀**：上次 rotate 已是 3 年前，原本的負責人離職，接手者不知道有這個 secret 存在。

**緩解**：

- Secret 管理工具強制設 `expires_at`、過期前自動提醒
- Inventory 表：所有 production secret 列管、定期 audit
- Rotation 排程進 calendar、輪值負責

### 失敗 5：rotation 後 audit log 沒更新

**症狀**：洩漏發生、要追「這個 secret 給過誰用」、但 audit log 只記了「secret 被用了」、沒記版本、無法區分新舊。

**緩解**：

- Audit log 記 secret version、不只 secret 本身
- Rotation 事件本身也要 log（誰、什麼時候、為什麼）
- Log 保留期跨多次 rotation cycle、避免歷史追溯斷鏈

---

## 收尾

Shared Secret rotation 的本質是**有意識管理 secret 的 lifecycle**。從發放、儲存、輪替到撤銷，每個階段都有對應的工程設計與監控訊號。

幾個核心原則：

1. **雙密過渡期是底層機制** — 任何 rotation 方案都建立在「server 能同時接受兩把」之上
2. **自動化工具值得投資** — 規模小用 secret manager（AWS / Vault / GCP），規模大可以自建，避免停在純手動
3. **定期跟緊急是兩套流程** — 定期重不中斷，緊急重立刻撤，流程、通知與回退標準要分開
4. **多 client 是協調問題** — 比技術問題難解、grace period + 強制升級工具是常用解法
5. **失敗模式要演練** — production 第一次跑 rotation 前，先在 staging 演練完整流程與回退路徑

延伸閱讀：

- [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) — 本文的主篇、Shared Secret 在「Layer 2 系統層」的位置
- [Laravel Sanctum 的 Bearer Token 設計剖析](/work-log/laravel_sanctum_pat_design/) — Layer 1 使用者 token 的儲存原則（hash + constant-time）也適用於 Layer 2
- [mTLS 實際怎麼設定與運維](/work-log/mtls_setup_and_operations/) — 不用 shared secret 的另一條路、憑證 lifecycle 跟 secret lifecycle 的對照
