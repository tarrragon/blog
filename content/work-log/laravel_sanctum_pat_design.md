---
title: "Laravel Sanctum 的 Bearer Token 設計剖析：{PK}|{secret} 為什麼這樣設計"
date: 2026-05-18
draft: false
description: "拆解 Laravel Sanctum Personal Access Token 的 {PK}|{secret} 格式設計 — 為什麼把 DB primary key 直接放進 token、hash 儲存的取捨、constant-time 比對的位置，以及跟 GitHub PAT、Stripe API Key 的設計差異。"
tags: ["security", "authentication", "laravel", "php", "sanctum", "bearer-token"]
---

## 為什麼專門寫這篇

Laravel Sanctum 的 Personal Access Token（簡稱 PAT）長這樣：

```text
1|abc123def456ghi789jkl012mno345pqr678stu
↑           ↑
DB 主鍵     真正的祕密
```

豎線前的數字是 `personal_access_tokens` 資料表的 primary key、豎線後是高熵隨機字串。這個設計在 Laravel 生態裡很常見、但常被誤解為「業界標準 token 格式」 — 實際上是 Sanctum 特定的設計選擇、跟 GitHub PAT（`ghp_...`）、Stripe API Key（`sk_live_...`）的設計取捨完全不同。

本文拆解 Sanctum PAT 三個關鍵設計決策：

1. 為什麼把 PK 公開放進 token
2. DB 為什麼只存 hash 不存原文
3. constant-time 比對為什麼放在應用層、不放在 DB

讀完後你能判斷自己的 application 該用 Sanctum 風格還是其他 token format、以及這些原則在非 Laravel 環境下如何套用。

> **本文位置**：本文是 [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) Layer 1 的深入篇。主文聚焦「為什麼要分層」的心智模型、本文聚焦「Sanctum 這個特定實作怎麼設計、為什麼」。

---

## Sanctum 在 Laravel 認證生態的位置

Laravel 官方提供三套認證套件、各自解的問題不同：

| 套件                 | 解的問題                               | Token 機制                               |
| -------------------- | -------------------------------------- | ---------------------------------------- |
| **Laravel Breeze**   | server-rendered 應用的登入註冊 starter | session cookie                           |
| **Laravel Sanctum**  | SPA / mobile app / 簡單 API token 認證 | session cookie + PAT（`{PK}\|{secret}`） |
| **Laravel Passport** | 完整 OAuth 2.0 server 實作             | JWT-based access token                   |

Sanctum 的設計目標是「**比 Passport 簡單、比手刻 token 嚴謹**」 — 不引入 OAuth 的完整 flow，但解決 token issue、storage、revoke 的常見坑。`{PK}|{secret}` 是這個設計目標下的具體 trade-off。

---

## 設計決策一：為什麼把 PK 公開放進 token

### 表面問題：怎麼快速驗證 token

Server 收到 client 傳來的 token、要做兩件事：

1. **找到** DB 裡對應的 row（這個 token 是哪個 user 的）
2. **比對** 確認 token 沒被偽造

如果 token 只是純隨機字串（沒有 PK 前綴）、validation 的 SQL 會是：

```sql
SELECT * FROM personal_access_tokens WHERE token = ?
```

這要求 `token` 欄位有 index、且 server 要做整欄查詢。看起來沒問題 — 但深一層是 **timing attack** 的隱患。

### 深層問題：DB 比對的 timing 不可控

當 `WHERE token = ?` 在 DB 執行時、執行時間可能洩漏：

- B-tree index 的查找路徑長度（同 prefix 的 row 多時、走的 page 不同）
- 字串比對的短路行為（多數 DB 引擎不保證 constant-time 比對）
- Buffer pool hit / miss 造成的時間差

攻擊者透過大量探測、可能推斷出有效 token 的部分結構。雖然實務上利用這個 leak 攻擊成本很高、但「**安全機制不該依賴 DB 引擎的實作細節**」是更穩健的設計原則。

### Sanctum 的解法：用 PK 收斂搜尋、把比對搬到應用層

`{PK}|{secret}` 的設計把驗證拆成兩步：

```text
client 傳來: "1|abc123..."
       ↓
   server 拆解
       ↓
   ┌──────────────┐
   │ PK = 1       │ ──→ SELECT * FROM tokens WHERE id = 1
   │ secret = abc │      （O(log N)、行為穩定）
   └──────────────┘
       ↓
   拿到該 row 的 hash
       ↓
   hash_equals(stored_hash, sha256(secret))
       ↓
   constant-time 比對、不洩漏 timing
```

關鍵在於 **DB 只負責「找到單一 row」、不負責「比對機密」**：

| 動作                      | 由誰處理             | 為什麼                                       |
| ------------------------- | -------------------- | -------------------------------------------- |
| 用 PK 找到 row            | DB（O(log N)）       | PK 是公開資訊、即使 timing 洩漏也沒安全意義  |
| 比對 secret hash 是否相等 | 應用層 constant-time | 在控制範圍內、可保證不依輸入內容變化執行時間 |

### 常見誤解：「PK 讓查詢變 O(1)」

很多 Sanctum 教學文章寫「PK 把查詢變 O(1)、避免 full scan」 — 這是不準確的論述。事實是：

- **hash 欄位也能 index** — `WHERE token_hash = ?` 用 B-tree index 是 O(log N)、不是 full scan
- **兩條路都是 B-tree index lookup** — token 規模下都不會是效能瓶頸；clustered（PK）跟 secondary（hash）的 IO cost 微差在多數場景可忽略

PK 設計的**主要價值在安全可預測性**、效能差距在多數場景可忽略：把比對機密的責任明確劃在「應用層 constant-time 函式」、不依賴 DB 引擎不保證的 timing 行為。

效能差異反而出現在「**hash 欄位是否要 index**」 — 如果用 hash lookup、`token_hash` 欄位需要 unique index、寫入成本變高；用 PK lookup、`token_hash` 不需要 index、寫入更輕量。但這在 token 規模通常不是 bottleneck。

---

## 設計決策二：DB 為什麼只存 hash 不存原文

### 威脅模型：DB 被攻陷

Token 是 capability credential — 持有即授權。如果 DB 直接存 plaintext token、任何能讀取 DB 的人（SQL injection、備份外流、運維 dump 不小心 push 到 GitHub）都能直接拿 token 假冒使用者發 request。

Sanctum 的做法：

```php
// 發放 token
$plaintext = Str::random(40);  // Sanctum 預設 40 char、base62 字元集
$hash = hash('sha256', $plaintext);
DB::table('personal_access_tokens')->insert([
    'token' => $hash,           // DB 只存 hash
    'tokenable_id' => $userId,
]);
return $tokenId . '|' . $plaintext;  // 只此一次回給 client、之後再也拿不到
```

意義：**DB 被 dump 也無法直接還原 plaintext token**。攻擊者拿到 `hash`、要還原 `plaintext` 需要對 SHA-256 做 preimage attack — 對 40 字元高熵隨機字串而言、計算上不可行。

### 為什麼用 SHA-256、不用 bcrypt

密碼儲存用 bcrypt / Argon2 是因為**密碼通常熵低**（人類記得住的東西、entropy 通常 < 40 bit）、要刻意慢、抵抗 offline brute-force。

Token 是**高熵隨機字串**（40 char base62 ≈ 238 bit entropy、比一般人類記得住的 password 高約 6 個數量級的熵）— 攻擊者就算拿到 hash、暴力枚舉 plaintext 的搜尋空間是 `62^40 ≈ 10^71`、宇宙年齡內試不完。在這個前提下：

| 演算法            | 處理時間（每次驗證） | 對 token 是否合理   |
| ----------------- | -------------------- | ------------------- |
| SHA-256           | ~微秒                | ✅ 完全足夠         |
| bcrypt（cost=12） | ~250ms               | ❌ 浪費 CPU、無增益 |

用 bcrypt 反而拖累每個 API request 的延遲、卻沒帶來實質安全增益。

### Salt 為什麼不需要

bcrypt 用 salt 是為了防 **rainbow table 攻擊**（預算好常見密碼的 hash、查表）。Rainbow table 對「人類選的密碼」有效、對「40 char 高熵 token」無效（搜尋空間太大、預算表的成本超過直接 brute-force）。

所以 Sanctum 對 token 用 unsalted SHA-256 — 不是設計缺陷、是符合威脅模型的選擇。

---

## 設計決策三：constant-time 比對放在應用層

### Constant-time 比對在解什麼

`==` 或 `strcmp` 比對字串時、會「**短路**」 — 一發現不同就回傳 false：

```c
// 偽程式碼：strcmp 的典型實作
for (i = 0; i < len; i++) {
    if (a[i] != b[i]) return false;  // ← 在這裡 return、不跑完
}
return true;
```

攻擊者可量測「server 從收到 request 到回 401」的時間、推斷「前幾個 byte 是對的」：

| 嘗試的 token  | 跑了幾個 byte 才 return | server 回應時間 |
| ------------- | ----------------------- | --------------- |
| `aaaaaaaa...` | 1（第 1 byte 就錯）     | ~1 μs           |
| `1aaaaaaa...` | 2（第 2 byte 才錯）     | ~2 μs           |
| `1a aaaaa...` | 3                       | ~3 μs           |

實務上單次 request 的網路抖動遠大於這幾 μs、但攻擊者可重複幾百萬次取平均、把雜訊濾掉、最終推出整個 hash。這就是 **timing attack**。

### Constant-time 函式的實作策略

Constant-time 比對的核心是「**不論輸入長什麼樣、都跑完整個比對長度**」：

```c
// 偽程式碼：constant-time 比對
result = 0;
for (i = 0; i < len; i++) {
    result |= a[i] ^ b[i];  // 用 XOR 累積差異、不 return
}
return result == 0;
```

每次呼叫都跑完整個 loop、結果用 bitwise OR 累積、最後一次性比對。執行時間不依輸入內容變化。

### 各語言的 constant-time 比對函式

| 語言        | 函式                                                     | 注意事項                                                |
| ----------- | -------------------------------------------------------- | ------------------------------------------------------- |
| **PHP**     | `hash_equals($known, $user_input)`                       | 第一個參數要是 known、第二個是 user input               |
| **Python**  | `hmac.compare_digest(a, b)`                              | 也可用 `secrets.compare_digest`                         |
| **Go**      | `subtle.ConstantTimeCompare(a, b)`                       | 回傳 int (0 / 1)、不是 bool                             |
| **Ruby**    | `ActiveSupport::SecurityUtils.secure_compare(a, b)`      | Rails；純 Ruby 用 `OpenSSL.fixed_length_secure_compare` |
| **Java**    | `MessageDigest.isEqual(a, b)`                            | Java 6+ 保證 constant-time                              |
| **Node.js** | `crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b))` | 兩個 Buffer 長度必須相同、否則 throw                    |

**反模式**：用 `==`、`===`、`strcmp`、`String.equals` 比對 hash — 全部都是 timing-unsafe。

### 為什麼不放在 DB 層

DB 引擎大多不保證 constant-time 比對 — MySQL、PostgreSQL 的字串比對為了效能、底層仍可能走短路邏輯。所以「`WHERE hash = ?`」即使加 index、也不該假設它對 timing attack 免疫。

Sanctum 的設計把 secret 比對完全搬到應用層用 `hash_equals` — DB 只負責「用 PK 找到單一 row」、應用層負責「比對 hash」。職責清楚、安全可預測。

---

## Sanctum vs GitHub PAT vs Stripe API Key

三者都是 opaque token（隨機字串、server lookup）、但 format 設計取捨完全不同：

| 維度                | Sanctum `{PK}\|{secret}`  | GitHub `ghp_xxx`                     | Stripe `sk_live_xxx`                           |
| ------------------- | ------------------------- | ------------------------------------ | ---------------------------------------------- |
| **找到 row 的方式** | 用 PK lookup              | 用 hash lookup                       | 用 hash lookup                                 |
| **格式可辨識性**    | 低（看起來像一般字串）    | 高（`ghp_` 前綴）                    | 高（`sk_live_` / `sk_test_` 前綴）             |
| **洩漏掃描**        | 困難                      | 容易（GitHub 自己 scan 公開 repo）   | 容易（Stripe webhook scan）                    |
| **Token type 辨識** | 需查 DB                   | 從前綴直接知道（user / app / OAuth） | 從前綴直接知道（live / test、public / secret） |
| **適合場景**        | 單一 Laravel app 內部使用 | 對外開放、需要洩漏偵測               | 對外開放、多環境（live / test）                |

### 各自的設計動機

**Sanctum**：使用情境是「單一 Laravel application 自己發、自己驗」。Token 不會散落在公開 repo（除非開發者犯錯）、洩漏偵測不是首要需求。把 PK 直接放進 token、換 timing 安全與設計簡潔。

**GitHub PAT**：使用情境是「使用者把 token 寫進 CI config、push 到 public repo」。GitHub 把 `ghp_` 前綴標準化、自家服務（Push Protection、Secret Scanning）會主動 scan 公開 repo、發現 `ghp_...` pattern 就通知 user 並 revoke。Token 的可辨識性是**洩漏偵測 infrastructure 的一環**、不是浪費字元。

**Stripe API Key**：使用情境跨 live 跟 test 環境、且有 public / secret 兩種 key。前綴設計：

- `sk_live_` — secret key、live 環境（會收真錢）
- `sk_test_` — secret key、test 環境
- `pk_live_` — publishable key、live 環境（可放 client）
- `pk_test_` — publishable key、test 環境

工程師看一眼就知道「這把 key 能幹嘛」、避免把 live key 寫進 test config。

### 怎麼選

| 你的場景                               | 建議設計                     |
| -------------------------------------- | ---------------------------- |
| 單一 Laravel app、token 只內部用       | Sanctum 預設即可             |
| 對外開放 API、token 會散落第三方環境   | 學 GitHub / Stripe 加 prefix |
| 多環境（dev / staging / prod）容易誤用 | 加環境 prefix（如 `_live_`） |
| 多 token type（user / bot / OAuth）    | 加 type prefix               |

可以混用 — 同樣是 `{prefix}|{PK}|{secret}` 結構、結合兩種設計的優點。

---

## 在非 Laravel 環境怎麼套用

Sanctum 的三個原則跨語言通用：

1. **DB 只存 hash** — 用任何語言的 SHA-256 / SHA-512 即可。Python: `hashlib.sha256`、Go: `crypto/sha256`、Node: `crypto.createHash('sha256')`
2. **Lookup 用穩定字段** — 把「找到 row」跟「比對機密」分開、`WHERE id = ?` 是穩定的、`WHERE hash = ?` 在 timing 上不可控
3. **應用層 constant-time 比對** — 用本文上面表格列的函式、絕不用 `==`

非 Laravel 框架的等效實作：

```python
# Python + SQLAlchemy 範例
import secrets, hashlib, hmac

def issue_token(user_id):
    plaintext = secrets.token_urlsafe(32)
    hash_value = hashlib.sha256(plaintext.encode()).hexdigest()
    token = PersonalAccessToken(user_id=user_id, hash=hash_value)
    db.session.add(token)
    db.session.commit()
    return f"{token.id}|{plaintext}"  # 只此一次回給 client

def verify_token(raw_token):
    # production 範例需多一層 try-except 涵蓋 int() 轉型與 DB 例外
    try:
        token_id, plaintext = raw_token.split('|', 1)
        token = PersonalAccessToken.query.get(int(token_id))
    except (ValueError, TypeError):
        return None
    if not token:
        return None
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    if not hmac.compare_digest(token.hash, expected_hash):
        return None
    return token.user
```

```go
// Go + sqlx 範例
func IssueToken(ctx context.Context, userID int64) (string, error) {
    plaintext := generateRandomString(40)
    hash := sha256.Sum256([]byte(plaintext))
    var tokenID int64
    err := db.QueryRowContext(ctx,
        "INSERT INTO personal_access_tokens (user_id, hash) VALUES ($1, $2) RETURNING id",
        userID, hex.EncodeToString(hash[:]),
    ).Scan(&tokenID)
    if err != nil {
        return "", err
    }
    return fmt.Sprintf("%d|%s", tokenID, plaintext), nil
}

func VerifyToken(ctx context.Context, raw string) (*Token, error) {
    parts := strings.SplitN(raw, "|", 2)
    if len(parts) != 2 {
        return nil, ErrInvalidFormat
    }
    tokenID, err := strconv.ParseInt(parts[0], 10, 64)
    if err != nil {
        return nil, ErrInvalidFormat
    }
    var token Token
    err = db.GetContext(ctx, &token, "SELECT * FROM personal_access_tokens WHERE id = $1", tokenID)
    if err != nil {
        return nil, err
    }
    expectedHash := sha256.Sum256([]byte(parts[1]))
    storedHash, _ := hex.DecodeString(token.Hash)
    if subtle.ConstantTimeCompare(storedHash, expectedHash[:]) != 1 {
        return nil, ErrInvalidToken
    }
    return &token, nil
}
```

兩者的關鍵都是：`SELECT WHERE id = ?` + 應用層 `compare_digest` / `ConstantTimeCompare`、不依賴 DB 比對 hash。

---

## 收尾

Sanctum 的 `{PK}|{secret}` 是一個**特定情境下的優秀設計**、不是業界通用標準：

- 它假設 token 不會散落到公開環境、所以不需要 prefix-based 洩漏偵測
- 它把比對機密的責任明確劃在應用層、不依賴 DB 引擎的 timing 行為
- 它用 SHA-256 + 不加 salt、因為 token 高熵時這個選擇符合威脅模型

如果你的場景符合這些假設、Sanctum 的設計可以直接拿來用。如果不符合（對外 API、需要洩漏偵測、多環境、多 token type）、應該學 GitHub / Stripe 改用 prefix-based format — 但儲存原則（hash + constant-time）跨設計通用。

延伸閱讀：

- [API 認證的三層信任邊界](/work-log/api_auth_trust_boundaries/) — 本文的主篇、Sanctum 在「Layer 1 使用者層」的位置
- [Shared Secret 安全輪替設計](/work-log/shared_secret_rotation/) — Layer 2 系統間 secret 的輪替議題
- [mTLS 實際怎麼設定與運維](/work-log/mtls_setup_and_operations/) — Layer 2 進階方案的部署細節
