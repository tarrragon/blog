---
title: "API 認證的三層信任邊界：使用者、系統、跨系統 Provisioning"
date: 2026-05-18
draft: false
description: "API 認證的信任邊界分層（Bearer Token / Shared Secret / Provisioning）：各層的洩漏後果與撤銷方式，以及混用造成的設計失效模式。"
tags: ["security", "authentication", "api", "backend", "provisioning"]
---

## API 認證為什麼要分層

**API 認證的核心是「身分維度的分離」** — 一個 request 同時牽涉「人」「呼叫的系統」「另一個系統有沒有對應身分」三個獨立問題，每個問題的 secret 機制不同、洩漏後果不同、撤銷方式不同。混用一個機制回答全部問題，等於用同一把鑰匙開家、車、保險箱。

看似一個 API request，其實同時要回答：

- 發起這個 request 的「**人**」是誰？（identity）
- 把這個 request 傳過來的「**系統**」是誰？（caller）
- 這個人在「**另一個系統**」有沒有對應身分？（cross-system mapping）

每個問題都需要不同的 secret 機制來回答。設計時先拆身分維度，再選 token、shared secret、mTLS 或 provisioning workflow，才有辦法讓洩漏範圍、撤銷粒度與排障路由各自清楚。

這篇整理兩層信任邊界（Layer 1 使用者、Layer 2 系統）跟一個跨系統 workflow（Layer 3 Provisioning），以及它們各自對應的 secret 機制。**每層的實作細節都另有獨立文章深入**、本文聚焦「為什麼要分」「各層解什麼問題」的心智模型。

> **前提假設**：以下所有機制都假設 transport 走 HTTPS / TLS。Token 與 secret 需要在加密通道內傳輸，否則中間人可直接取得 credential。HTTPS 是所有層共同依賴的 transport 前提。
>
> **本文 token 範圍**：本文討論「opaque token」（隨機字串、server 端 lookup），不涵蓋 JWT（self-contained token、簽章驗證）。兩者安全模型不同，比較見 Layer 1 段落。

---

## Layer 1：使用者層（Bearer Token）

**使用者層負責把 request 綁到已登入的人類或帳號主體**。它回答的問題是：「這個 request 是哪個使用者發的？」

**Bearer Token 是 capability credential（持有即授權）、不是 identity credential（身分證明）**。差別在於：身分證遺失可以掛失補辦、別人撿到也無法直接領錢；Bearer Token 一旦被取得、攻擊者就能即時用該使用者身分發 request、沒有第二道關卡。這個本質決定了 token 的儲存、傳輸、撤銷機制都必須以「持有即危險」為前提設計。

「Bearer Token」是 RFC 6750 定義的 HTTP authentication scheme（`Authorization: Bearer <token>`）、屬於通用概念 — GitHub PAT、Stripe API Key、OAuth access token、Laravel Sanctum 的 PAT、JWT 都是 Bearer Token 的不同實作。

### Opaque Token vs JWT：兩種根本不同的設計

「Bearer Token」是上位概念、實作上有兩條主線、安全模型完全不同：

| 項目         | Opaque Token（如 Sanctum）  | JWT                            |
| ------------ | --------------------------- | ------------------------------ |
| Token 本身   | 隨機字串、無內含資訊        | 簽章 payload、內嵌使用者 claim |
| 驗證方式     | server 查 DB lookup         | 驗簽章、不需 DB                |
| 載入使用者   | 從 DB row 撈                | 直接讀 claim                   |
| 撤銷         | 刪 DB row、立即生效         | 困難、需 blacklist 或短 TTL    |
| 洩漏暴露範圍 | 該 row 立即停用             | 直到 expire 都有效             |
| 跨服務驗證   | 需要共用 DB 或驗證 endpoint | 共享公鑰即可、stateless        |

兩者各有適合情境：opaque token 撤銷快、適合「使用者主動登出 / 帳號被盜要立即停權」；JWT 不需 DB lookup、適合「跨多個 microservice、想避免每次都查中央 DB」。下面 Layer 1 的內容**只聚焦 opaque token** — JWT 的設計細節（簽章演算法選擇、`alg: none` 攻擊、key rotation）是獨立議題、不在本篇範圍。

### Opaque Token 的格式設計

Opaque token 是隨機字串、但實際 format 在不同產品有兩條主流分流：

| 設計                    | 範例                                         | 解的問題                                         |
| ----------------------- | -------------------------------------------- | ------------------------------------------------ |
| **`{PK}\|{secret}`**    | `1\|abc123def456...`（Laravel Sanctum）      | 用 PK 收斂 DB 搜尋、把 timing 安全留給應用層     |
| **`{prefix}_{secret}`** | `ghp_xxx`（GitHub）、`sk_live_xxx`（Stripe） | 用語意 prefix 支援自動洩漏掃描跟 token type 辨識 |

兩種設計**沒有絕對優劣**、取決於 token 的傳播範圍：純內部使用、Sanctum 設計簡潔且足夠；對外開放、容易散落公開 repo、prefix 設計能讓 GitHub Secret Scanning / Stripe webhook 等工具自動偵測洩漏。

Sanctum 的 `{PK}|{secret}` 設計常被誤解為「業界標準」 — 其實是 Laravel 生態的特定選擇。具體機制、跟 GitHub / Stripe 設計的比較、各語言實作範例見 [Laravel Sanctum 的 Bearer Token 設計剖析](/work-log/laravel_sanctum_pat_design/)。

### Token 在 DB 的儲存原則（簡述）

無論用哪種 format、有三條跨設計通用的儲存原則：

1. **DB 只存 hash、不存原文** — token 是高熵隨機字串、SHA-256 即可、不需 bcrypt
2. **比對必須是 constant-time** — 用各語言提供的 `hash_equals` / `compare_digest` / `ConstantTimeCompare`、不用 `==`
3. **Lookup 用穩定字段、機密比對放應用層** — DB 引擎不保證 constant-time 比對、把機密比對搬離 DB

這三條的詳細推導、各語言 constant-time 函式對照、非 Laravel 環境的實作範例見 [Laravel Sanctum 的 Bearer Token 設計剖析](/work-log/laravel_sanctum_pat_design/)。

### Token 的生命週期

```text
   Login                  Use                  Expire/Revoke
─────────  ───────────────────────────  ─────────────────
issued → DB 存 hash  →  Bearer 驗證    →   row deleted
                            ↓
                       set request.user
```

- **`expires_at`**（例如 7 天、30 天）— 限制洩漏 token 的暴露窗
- **`abilities` / `scopes`** — 限縮權限粒度（「只能讀」「只能存取某 resource」），降低單一 token 洩漏的破壞範圍
- **登出即刪 row** — opaque token 的撤銷成本低，這是它相對 JWT 的關鍵優勢
- **rate limit / brute force 防護** — token 是隨機字串、攻擊者可暴力試。應用層要對「token 驗證失敗」加 rate limit、避免被掃出有效 token
- **長期 access 用 refresh token pattern** — access token 短 TTL（小時級）、refresh token 長 TTL（月級）。Access token 洩漏只影響短窗、refresh token 撤銷後新的 access token 也無法發放

### 信任邊界

```text
[ 使用者 ] ─────────▶ [ API server ]
              token        ↑
                           知道「你是誰」
                           但不會自動跨到其他系統
```

Bearer Token 是 capability credential — 任何持有它的 client 都能以該使用者身分發 request。這也是為什麼 token 一旦離開原本的 API server，就會引發下一層問題：B 系統收到 A 系統的 token、根本不知道該怎麼驗證、也不該驗證。

---

## Layer 2：系統層（System-to-system credential）

**系統層負責驗證呼叫方服務本身的身分**。它回答的問題是：「這個 request 是哪個系統發的？」

當系統 A 需要呼叫系統 B 的 API 時，Layer 1 的使用者 token 只代表「使用者」的身分。系統 B 仍需要獨立驗證「這個 request 來自合法的合作系統 A」，這個判斷要由系統層 credential 承擔。

### 為什麼分得這麼清楚

想像系統 B 收到一個請求：

```text
B 收到請求「給我會員 X 的資料」
   ↓
B 自問：這請求來自...
   ├─ 我的合作夥伴系統 A？  → 可進入授權判斷
   ├─ 未註冊的外部 caller？ → 回 401 / 403
   └─ 偽裝成 A 的 caller？  → 回 401 / 403 並記錄告警
```

純粹靠 Layer 1 的使用者 token 只能證明「這位 user 的身分」，無法證明「系統 A 的身分」。這個分工讓帳號被盜與合作系統被冒用分別走不同監控與撤銷流程。

### 「Shared Secret」與「API Key」的關係

兩者常被混用、實際上是同一個機制（一邊發、一邊存的對稱字串）的不同部署方式：

| 區分點          | Shared Secret                    | API Key                                           |
| --------------- | -------------------------------- | ------------------------------------------------- |
| Caller identity | 兩邊都用同一把、沒有 caller 區分 | 每個 client 一把、server 有 key → identity 對照表 |
| 撤銷粒度        | 換一邊、全部斷                   | 撤一把 key、只影響該 client                       |
| 典型部署        | 內部固定夥伴系統                 | 對外開放 API、多 tenant                           |

下面討論的「Shared Secret」泛指這個 pattern；要做 per-client identity 與 revoke 時、改成 API Key 結構即可。

### 常見方案的取捨

| 方案                         | 機制                                   | 撤銷粒度                                   | 適合情境                                | 主要代價                                    |
| ---------------------------- | -------------------------------------- | ------------------------------------------ | --------------------------------------- | ------------------------------------------- |
| **Shared Secret**            | 兩邊放同一把字串                       | 全部 caller                                | 內部單一夥伴、低變更頻率                | 多 client 時撤銷會牽動所有人                |
| **API Key**                  | 每個 client 一把、server 有對照表      | per-client                                 | 對外開放、多 tenant                     | server 需維護 key → identity mapping        |
| **HMAC 簽章**                | client 用 secret 簽 request body       | per-key                                    | secret 不想經過網路、需防 replay / 改寫 | 兩邊都要實作簽章邏輯、debug 較難            |
| **mTLS**                     | 雙向 TLS 憑證                          | 撤憑證                                     | 金融、醫療、零信任網路                  | 憑證生命週期管理複雜、CA / CRL 基礎建設成本 |
| **OAuth Client Credentials** | client_id + secret 換短期 access token | 撤 long-lived secret、短 token 自然 expire | 跨組織、權限粒度需要、需配合 scope      | 多一層 token endpoint、實作成本較高         |

選擇預設值的判斷：純內部固定夥伴可從 Shared Secret 起步；對外或多 client 直接上 API Key；公網跨組織 + 需要短期撤銷上 OAuth Client Credentials；合規或高威脅環境用 mTLS。

mTLS 的 CA 階層、憑證生命週期、撤銷機制、nginx / service mesh 整合見 [mTLS 實際怎麼設定與運維](/work-log/mtls_setup_and_operations/)。

### Shared Secret 的隱形成本

Shared Secret 部署簡單、但維運上有幾個固定痛點：

- **無法 per-caller 撤銷** — 一旦洩漏，所有用這把 secret 的 client 都得換
- **輪替需要兩邊同步** — 任何一邊忘了更新就斷線、需要「雙密過渡期」讓兩邊有時間切換。具體實作見 [Shared Secret 安全輪替設計](/work-log/shared_secret_rotation/)
- **常被放進 query param** — 為了簡便、會留在 nginx access log、CDN log、瀏覽器 history 裡。應放在 request header（例如 `X-System-Secret: xxx`）或走 HMAC / OAuth

### 信任邊界

```text
[ 系統 A ] ═════════▶ [ 系統 B ]
       shared secret
       (server-to-server, server-only credential)
```

**Layer 2 secret 的安全邊界是 server-side runtime**。一旦進入瀏覽器或行動 app，攻擊者就能透過反編譯、JS source map、devtools network panel 等管道取得；取得後即可假冒系統 A 呼叫系統 B。Mobile app 的反編譯工具（jadx、Hopper、Ghidra 等）讓這個攻擊成本極低，obfuscation 只能增加時間成本。

如果 client 端需要呼叫 B，安全路由是讓 client 先呼叫 A，由 A 在 server 端用 Layer 2 secret 呼叫 B（A 當 proxy / BFF）；另一條路是用 OAuth 把 short-lived token 發給 client，long-lived secret 留在 server。

---

## Layer 3：跨系統 Provisioning（身分對應 workflow、不是新的信任邊界）

**回答的問題**：「系統 A 的使用者 X、在系統 B 對應到哪個身分？」

**Layer 3 跟 Layer 1 / 2 在概念上不對等** — Layer 1 / 2 是「驗證某個身分」的信任邊界、各自需要獨立的 secret 機制；Layer 3 不引入新的 secret、是「**讓兩個系統的使用者身分對應上**」的 workflow。它建立在 Layer 1（A 已驗證使用者）跟 Layer 2（A 已被授權呼叫 B）之上、不取代任何一層。

之所以仍放進「層」的編號系統、是因為實際 API 串接時、開發者會把它跟前兩層一起遇到、必須在同一個心智模型裡處理。但設計時要清楚意識到：**Layer 3 的失敗模式是「身分對不上」、不是「身分被偽造」**、跟 Layer 1 / 2 的安全失敗模式不同。

### 為什麼需要 provisioning

當 A 跟 B 是兩個獨立 service 時，「**A 的使用者 X**」跟「**B 的使用者 X**」未必是同一筆資料。可能：

- B 從來沒見過 X 這個人
- B 有自己對 X 的 record、但跟 A 不同 schema
- B 看過 X、但兩邊的 user_id 還沒對應上

需要一個機制把兩邊綁定 — 這個動作叫 **provisioning**。

### Eager vs Lazy 兩種策略

Provisioning 策略的判斷核心是「何時承擔跨系統建檔成本」。Eager 把成本前移到註冊流程，Lazy 把成本延後到第一次使用；兩者差異不只是效能，而是資料膨脹、首用體驗與文件契約的取捨。

```text
EAGER (註冊時就跨系統建檔)
────────────────────────────
使用者註冊系統 A
   ↓
   A 新增會員 row
   ↓
   A ──同步呼叫──▶ B.createUser()  ← 即使他可能永遠不用 B
   ↓
   兩邊都有資料、可以立刻呼叫 B 的 API
```

Eager 適合大多數使用者都會用到 B 功能、且首用延遲成本高的服務。主要風險是 B 會累積大量低活躍 user，schema migration、備份與隱私刪除流程都會被放大。

```text
LAZY (第一次需要時才建)
────────────────────────────
使用者註冊系統 A
   ↓
   A 新增會員 row              ← 只有 A 這邊
   ↓
   ...日後可能很久才用到 B...
   ↓
使用者第一次需要 B 的功能
   ↓
   呼叫 A 的「provision」endpoint
   ↓
   A ──呼叫──▶ B.findOrCreateUser()  ← 這時候才建
   ↓
   之後就跟 eager 一樣
```

Lazy 適合只有一部分使用者會用到 B 功能、且第一次使用可以接受一次 provisioning 延遲的服務。主要風險是「第一次使用」這個時機需要被寫進文件、SDK 或錯誤碼，否則接手者會把 B 的 404 誤判成 request 格式或權限問題。

### Lazy 的「隱性 API 依賴順序」

Lazy provisioning 的最大成本是**隱性依賴順序造成的認知負擔**：

- 文件若沒有寫清楚「呼叫 B 前先呼叫 A 的 provision endpoint」，接手者會在「B 回 404 找不到 user」的訊號上花大量時間排查
- 用 SDK 包裝可以把 provision 自動處理、對外只暴露單一 API
- 不用 SDK 時，文件需要在快速上手與錯誤碼段落顯眼註明這個依賴順序

折衷做法：B 的 API 在第一次發現 user 不存在時、**主動回一個 `PROVISIONING_REQUIRED` 錯誤碼**、client 看到就知道要去呼叫 A 的 provision endpoint。比起靜默 500 或單純 404 更能引導 client 走到正確流程。

### 信任邊界示意

```text
[ 使用者 ] ──Layer 1──▶ [ 系統 A ] ══Layer 2══▶ [ 系統 B ]
                            │  Layer 3 workflow：
                            └─ 觸發後在 B 建立對應身分
```

Layer 3 不引入新的 secret、是「**建立兩邊身分關聯**」的 lifecycle 動作。它依賴 Layer 1（確認使用者身分）跟 Layer 2（A 被授權對 B 發指令）。沒有 Layer 1 / 2 的話、provisioning 自己無法獨立成立。

---

## 三層怎麼組合

把三層擺在一起的典型 request 流程：

```text
        ┌─────────────┐                       ┌──────────────┐
        │  使用者      │                       │   系統 A     │
        │  (Browser/  │ ──── Layer 1 ──────▶ │              │
        │   App)      │      Bearer token     │              │
        └─────────────┘                       └──────┬───────┘
                                                     │
                                            Layer 3  │ Provision
                                                     │ (第一次)
                                                     ▼
                                              ┌──────────────┐
                                              │   系統 B     │
                                              └──────────────┘
                                                     ▲
                                                     │
                                            Layer 2  │ Shared secret
                                                     │ (server-to-server)
```

每一條線都是一層信任邊界，各自需要不同 secret 機制保護。

---

## 設計時最常見的三個失效模式

### 失效模式一：讓使用者 token 也能驗 Layer 2

**責任分工**：「使用者身分」跟「呼叫系統身分」是兩個獨立維度、各自需要獨立 credential。系統 B 對「來自 A」的信任應綁定在系統層 credential，而不是任何單一使用者帳號上。

**常見誤用**：B 接受「只要 request 帶有任一合法使用者 token 就放行」。

**風險判讀**：這會把系統信任降階為使用者信任。任一帳號被盜（釣魚、密碼洩漏、token 外流）時，攻擊者就能用該使用者身分對 B 發 request，執行 B 開放給 A 的系統操作。

**操作路由**：使用者層用 Layer 1 token，系統層用 Layer 2 credential，兩層都通過才放行。

### 失效模式二：把 Layer 2 secret 放進 client

**責任分工**：Layer 2 secret 是「server 代表系統 A 對外的證明」，應留在 server 端的受信任執行環境。

**常見誤用**：把 shared secret 寫進前端 JS、行動 app 編譯時、甚至 git public repo。

**風險判讀**：client 環境（瀏覽器、mobile app）不在受控範圍。JS source 可在 devtools 直接看，mobile binary 可被反編譯出字串。Obfuscation 提高的是時間成本，沒有改變 secret 已散佈到不受信任環境的事實。

**操作路由**：client 需要 B 的功能時，走「client → A → B」，由 A 在 server 端用 Layer 2 secret 呼叫 B；或用 OAuth 把 short-lived token 發給 client，long-lived secret 留在 server。

### 失效模式三：Layer 3 依賴順序沒文件化

**責任分工**：跨系統依賴順序是 API 契約的一部分，屬 publisher 的責任，需要在文件、SDK 或錯誤訊號中顯式表達。

**常見誤用**：「呼叫 B 之前要先呼叫 A 的某個 endpoint」這個前置條件只存在於原始設計者的記憶中、文件沒寫、SDK 沒包、B 失敗時也只回 generic error。

**風險判讀**：接手者看到「呼叫 B 失敗」時，會優先檢查 B 的文件、request 格式與 network 層。若真正根因是尚未呼叫 A 的 provision endpoint，偵錯路徑會被導到錯誤層級。

**操作路由**（任選其一、優先序由上而下）：

1. SDK 包裝、自動處理 provision、對外只暴露單一 API
2. B 主動回 `PROVISIONING_REQUIRED` error code、引導 client 補上前置呼叫
3. 文件在「快速上手」段顯眼處註明依賴順序

---

## 何時可以簡化三層

三層框架的設計重點是「跨系統身分與 credential 分工」。當某一層回答的問題在架構裡不存在，設計可以縮小到實際存在的身分問題。

| 情境                               | 簡化方式                                                                                              |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 單體 application（沒有跨系統呼叫） | 只需 Layer 1。沒有 system-to-system 互動、Layer 2 / 3 不存在                                          |
| 內網微服務、共用 identity provider | Layer 1 透過 service mesh 或共用 token 傳遞、Layer 2 可用 service mesh 內建 mTLS 取代手動 secret 管理 |
| 後端 cron / batch job 之間互呼     | 只需 Layer 2（system-to-system credential）、沒有使用者觸發、Layer 1 不適用                           |
| 兩個系統共用同一份 user DB         | 可省略 Layer 3（身分天然對應），但 Layer 1 / 2 仍各自獨立                                             |

簡化的判準是「**該層回答的問題是否真實存在於這個架構**」。單體 application 沒有跨系統呼叫時，Layer 2 的 caller 驗證可以省略；兩個系統共用同一份 user DB 時，Layer 3 的身分對應 workflow 可以省略。

簡化不等於降低基礎安全前提。HTTPS / TLS 與 token 儲存原則（hash + constant-time）是任何 Layer 1 的最低要求，跟「層」的數量無關。

---

## 收尾

兩層信任邊界 + 一個身分對應 workflow：

- **Layer 1（使用者）**：解決「你是誰」 — 用 Bearer Token、注意 capability credential 的暴露成本
- **Layer 2（系統）**：解決「哪個系統呼叫的」 — 用 Shared Secret / API Key / OAuth / mTLS、secret 不離 server
- **Layer 3（Provisioning workflow）**：解決「兩邊身分怎麼對上」 — 不是新的 secret、是 lifecycle 動作

設計後端 API 時，先把這三個問題分開，secret 機制的選擇會變清楚。若排障訊號是「這個 token 在那邊不能用」，下一步是先判斷它卡在使用者層、系統層，還是 provisioning workflow。

### 各層的深入文章

本文聚焦「為什麼要分層」的心智模型、各層的具體實作細節都另有獨立文章：

- **Layer 1（使用者）** → [Laravel Sanctum 的 Bearer Token 設計剖析](/work-log/laravel_sanctum_pat_design/)：`{PK}|{secret}` format 為什麼這樣設計、DB 儲存三原則、各語言 constant-time 函式對照、跟 GitHub / Stripe 的設計比較
- **Layer 2（系統）→ Shared Secret 維運** → [Shared Secret 安全輪替設計](/work-log/shared_secret_rotation/)：雙密過渡期、自動化 rotation 工具（AWS Secrets Manager / Vault / GCP）、緊急 vs 定期流程、多 client 同步難題
- **Layer 2（系統）→ mTLS 部署** → [mTLS 實際怎麼設定與運維](/work-log/mtls_setup_and_operations/)：CA 階層、憑證生命週期、撤銷機制（CRL / OCSP / short-lived）、nginx / Envoy / service mesh 整合

### 沒展開的延伸議題

JWT 的簽章演算法選擇、`alg: none` 攻擊、token rotation 的具體實作、零信任網路下的 service-to-service 認證、OAuth flow 的完整 lifecycle、SSO（SAML / OIDC）跟本文三層的對應關係。每個都值得獨立成篇、本文聚焦在「先把層數想清楚」這個前置問題。
