---
title: "Client-side SDK 認證的根本限制"
date: 2026-06-24
description: "嵌在 client 端的 credential 必然可被提取 — 認清 architecture 天花板後的多層緩解策略，從 origin 驗證到 device attestation"
weight: 8
tags: ["monitoring", "security", "sdk", "authentication", "client-side", "api-key"]
---

當監控 SDK 部署在使用者裝置上（瀏覽器、手機 app、本機腳本），collector 的 ingestion endpoint 就暴露在外部網路 — 認證機制需要面對 credential 必然可被提取的前提。Client-side SDK 的認證和 server-side API 的認證面對的是結構性不同的問題。Server-side 的 API key 存在環境變數或 secret store 裡，只有 server process 能讀取。Client-side SDK 的 credential 必須嵌入到使用者手上的程式碼中 — JS bundle、APK、Python script — 使用者（或攻擊者）可以直接讀取。

這個限制來自 architecture，和 implementation 無關。混淆 JS、ProGuard 混淆 APK、編譯 Python 成 `.pyc`，都只增加提取成本，不改變「credential 在 client 端」的事實。

[Collector Access Control](/monitoring/07-security-privacy/collector-access-control/) 討論了 API key 和 mTLS 的認證機制，[Transport 安全](/monitoring/07-security-privacy/transport-security/) 討論了傳輸層加密。兩者的前提是 credential 被妥善保管。本章處理的是那個前提不成立時 — credential 已被提取或必然可被提取 — 的緩解策略。

## 商業方案的處理方式

所有主流的 client-side telemetry 方案都面對同樣的限制。它們的共同策略是：承認 client credential 會暴露，把防線從「保護 credential」轉移到「限制 credential 被濫用的影響」。

**Google Analytics 4**：Measurement ID（G-XXXXXXXXXX）直接寫在網頁的 JS snippet 中，任何人檢視網頁原始碼都能取得。GA4 的防護在 server-side — Google 用 domain 白名單過濾來源，加上自動的 bot traffic 偵測剔除機器流量。Measurement Protocol（server-to-server）需要額外的 API secret，但 client-side 的 gtag.js 不需要。

**Sentry**：DSN（Data Source Name）包含 project ID 和 public key，直接嵌在 SDK init 的程式碼中。Sentry 官方文件明確標示 DSN 是 public 的 — 攻擊者取得 DSN 只能送事件，不能讀取已收集的資料。防護靠 rate limit（每個 project 的 events/sec 上限）、allowed domains（只接受來自白名單 domain 的事件）、和 server-side 的 event 去重。

**Firebase**：整個 `google-services.json` / `GoogleService-Info.plist` 的內容 — 包含 apiKey、projectId、appId — 都視為公開資訊。Firebase 的安全模型不依賴這些 key 的保密性；它們的功能是識別（identify）而非授權（authorize）。需要保護的資源靠 Firebase Security Rules 和 App Check（device attestation）處理。

**Datadog RUM**：Client token 是獨立於 API key 的 credential。API key 可以讀寫所有 Datadog 資料，必須保護在 server-side；client token 只能寫入 RUM 事件，設計上可以暴露在 client 端。Datadog 建議搭配 intake proxy（collector 前面加一層自己的 server），讓 client token 不直接出現在瀏覽器中。

這些方案的共同模式：client-side credential 的角色是「識別來源」而非「授權存取」。即使被提取，攻擊者能做的事被限縮在「寫入事件」— 影響可控。

## 認證天花板：識別 vs 授權

[Collector Access Control](/monitoring/07-security-privacy/collector-access-control/) 的 API key 同時承擔識別和授權 — 有 key 就能寫入，沒 key 就被拒絕。在 server-side 場景下這沒有問題，因為 key 不會暴露。

Client-side 場景需要拆開這兩個功能：

**識別（identification）**：這個 request 來自哪個 app、哪個 SDK、哪個部署版本。識別資訊可以公開 — 它的價值是讓 collector 知道事件來自哪裡，用於 access log、per-app rate limit、和事件標記。

**授權（authorization）**：這個 request 有沒有權限執行寫入操作。授權依賴 credential 的保密性 — 在 client-side 場景下，credential 保密性的天花板很低。

接受這個區分後，client-side SDK 的 API key 更接近「識別 token」。它的洩漏不是安全事件（像 server-side API key 洩漏那樣），而是預期中的狀態。防護的重點從「防止 key 洩漏」轉移到「限制 key 被濫用時的影響」。

## 多層緩解策略

以下各層按實作成本遞增排列。前面的層在多數場景下足夠，後面的層在 endpoint 暴露在公開網路且面對主動攻擊時才需要。

### 第一層：寫入限制（collector 已有）

[Collector Access Control](/monitoring/07-security-privacy/collector-access-control/) 的寫入限制 — rate limit、payload size limit、schema validation — 是第一層防護。這些機制不區分「合法 SDK」和「偽造 client」，對所有寫入請求一視同仁地施加約束。

Rate limit 限制每個 API key 的事件速率。Schema validation 拒絕不符合 [event.schema.json](/monitoring/02-log-schema/event-schema-fields/) 結構的 payload。兩者合起來把偽造流量的影響限制在「每秒 N 筆符合 schema 的事件」— 這個量級的資料汙染對 error tracking 的影響有限（error 事件靠 stack trace fingerprint 去重），對 funnel 分析的影響較大（行為事件的計數會被灌水）。

### 第二層：Origin 驗證

Web SDK 的 HTTP request 帶有瀏覽器自動附加的 `Origin` header。Collector 可以檢查 Origin 是否在白名單中。

```go
func originCheck(next http.Handler, allowed []string) http.Handler {
    allowedSet := make(map[string]bool)
    for _, o := range allowed {
        allowedSet[o] = true
    }
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        origin := r.Header.Get("Origin")
        if origin != "" && !allowedSet[origin] {
            http.Error(w, "forbidden origin", http.StatusForbidden)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

Origin 驗證擋住的是「從瀏覽器中跨域呼叫」的場景 — 攻擊者在自己的網站用 JS 向你的 collector 發 request，瀏覽器會帶上攻擊者網站的 Origin，被 collector 拒絕。

**天花板**：Origin header 只有瀏覽器會自動附加。用 `curl`、Postman、或任何非瀏覽器 HTTP client 發 request 時，可以自行設定任意 Origin 值。Origin 驗證擋得住瀏覽器中的跨域呼叫，擋不住直接用 HTTP client 偽造的 request。

Mobile SDK（Flutter / native app）的 request 不帶 Origin header。Origin 驗證只對 Web SDK 有效。

### 第三層：Request signing

SDK 用 HMAC 對每個 request 簽章，collector 驗證簽章有效性。簽章的輸入包含 timestamp 和 payload hash，防止 replay attack 和 payload 竄改。

```text
X-Signature: a3f8c2e1b7d94f06...  (HMAC-SHA256 結果的 hex 編碼)
X-Timestamp: 1719216000
```

SDK 計算方式：`HMAC-SHA256(secret, timestamp + "." + SHA256(body))`，結果轉 hex 字串放入 `X-Signature` header。

Collector 端的驗證邏輯：

```go
func verifySignature(r *http.Request, secret string) bool {
    ts := r.Header.Get("X-Timestamp")
    sig := r.Header.Get("X-Signature")

    // 拒絕超過 5 分鐘的 request timestamp（防 replay）
    // 5 分鐘容忍 client-server 時鐘漂移和網路延遲；行動裝置偏差大的環境可放寬到 10 分鐘
    // 此處的 timestamp 是 HTTP request 發出時間，和事件的 timestamp 欄位（事件產生時間）無關
    tsInt, err := strconv.ParseInt(ts, 10, 64)
    if err != nil || abs(time.Now().Unix()-tsInt) > 300 {
        return false
    }

    body, _ := io.ReadAll(r.Body)
    bodyHash := sha256.Sum256(body)
    expected := hmac.New(sha256.New, []byte(secret))
    expected.Write([]byte(ts + "." + hex.EncodeToString(bodyHash[:])))

    sigBytes, err := hex.DecodeString(sig)
    if err != nil {
        return false
    }
    return hmac.Equal(sigBytes, expected.Sum(nil))
}
```

Request signing 增加偽造成本 — 攻擊者需要提取 HMAC secret 並實作簽章邏輯，而非直接複製一個 API key 貼到 curl 指令。

HMAC secret 和 API key 一樣嵌在 client 端程式碼中，反編譯 APK 或閱讀 JS bundle 可以提取。Signing 增加的是攻擊者的工程投入（需要理解簽章算法並正確實作），而非理論上的安全性。對 casual attacker（看到 API key 就想試試的人）有效，對 motivated attacker（願意花時間逆向工程的人）無效。

### 第四層：行為分析異常偵測

Collector 端統計每個 API key（或 source.app）的事件模式，建立 baseline 後偵測偏離。

正常 SDK 的行為有可預測的特徵：

| 特徵         | 正常 SDK 的 pattern                                    | 偽造流量的 pattern          |
| ------------ | ------------------------------------------------------ | --------------------------- |
| 事件類型分布 | error / event / lifecycle / metric 四類混合            | 可能只有單一類型            |
| 事件間隔     | 攢批送出，interval 接近 SDK config 的 flush interval   | 固定間隔或連續送出          |
| Payload 結構 | `source.sdk` / `source.platform` / `source.app` 值穩定 | 可能缺少 SDK 自動填入的欄位 |
| Session 行為 | 有 lifecycle 事件（session.begin / session.end）       | 可能沒有 session 邊界       |
| 時間分布     | 跟使用者活動時段相關（工作時間 / 使用高峰）            | 可能 24 小時均勻分布        |

Collector 可以用 rule engine 偵測異常模式：

- 單一 API key 的事件量在 10 分鐘內超過過去 24 小時平均值的 10 倍
- 連續 N 個 request 的事件全是同一個 type
- `source.sdk` 欄位的值不在已知的 SDK 版本清單中

偵測到異常後的處理方式是標記而非丟棄 — 在事件中加入 `_flags.suspicious = true` flag，讓 dashboard 和分析查詢可以過濾。直接丟棄有誤殺正常流量的風險（例如行銷活動導致的真實流量暴增）。

攻擊者如果研究過正常 SDK 的行為模式（事件類型分布、送出間隔、payload 結構），可以模擬出相似的流量。行為分析依賴「偽造流量和正常流量有可偵測的差異」這個前提 — 對低投入的攻擊者成立，對高投入的攻擊者不一定。

### 第五層：Device attestation

由作業系統或平台層驗證 client 的合法性，提供 SDK 自身無法產生的證明。

**Firebase App Check**：整合 DeviceCheck（iOS）、Play Integrity（Android）、reCAPTCHA Enterprise（Web），由裝置平台出具 attestation token。Collector 向 Firebase 驗證 token 的有效性。

**Apple DeviceCheck / App Attest**：iOS 裝置向 Apple server 請求 attestation，證明 request 來自一台真實的、未被篡改的 iOS 裝置上的合法 app。

**Google Play Integrity**：驗證 request 來自 Google Play 安裝的 app、在未 root 的裝置上、由合法使用者操作。

Device attestation 提供的保證比前四層都強 — 它依賴裝置硬體和平台服務（難以偽造），而非 SDK 嵌入的 secret（可提取）。

**天花板**：

- 平台綁定 — 每個平台（iOS / Android / Web）需要各自整合不同的 attestation 服務，跨平台 SDK 的實作成本高
- Root / 越獄裝置上 attestation 可能失敗或被繞過
- Web 端的 reCAPTCHA 驗證依賴 Google 服務，有隱私和可用性的考量
- 自架 collector 需要額外整合 Firebase Admin SDK 或各平台的驗證 API

Device attestation 適合商業產品級的 mobile app，對自架監控工具而言實作成本通常超出收益。

## 自架方案的規模對應

不同部署規模下，需要做到哪一層取決於 endpoint 的暴露程度和偽造流量的影響大小。

| 部署場景                     | 暴露程度                           | 建議做到的層級              | 理由                                                                     |
| ---------------------------- | ---------------------------------- | --------------------------- | ------------------------------------------------------------------------ |
| 自用（1 人，同機 / 同網段）  | 低 — endpoint 不對外               | HTTPS + basic auth          | 攻擊面只有同網段，認證足夠                                               |
| 小型團隊（< 100 人，VPN 內） | 低 — endpoint 在 VPN 後            | API key + rate limit        | VPN 已限制存取範圍，rate limit 防 SDK bug                                |
| 公開 endpoint（VPS / 雲端）  | 高 — 任何人可存取                  | 第一到第四層 + WAF          | rate limit + origin + signing + 行為分析 + CDN/WAF 的 IP reputation 過濾 |
| 商業產品（app store 發佈）   | 高 — APK 可反編譯，JS 可檢視原始碼 | 第一到第五層 + intake proxy | 需要 device attestation 和 proxy 層把 credential 從 client 端移除        |

**Intake proxy 架構**：在公開 endpoint 和商業產品場景下，可以在 collector 前面加一層自己的 server（proxy），SDK 送事件到 proxy，proxy 用 server-side API key 轉發到 collector。Client 端的 credential 只指向 proxy，proxy 的 API key 指向 collector — credential 分層，client 端的 key 洩漏不影響 collector 的認證。

```text
SDK ──(client token)──→ Intake Proxy ──(server API key)──→ Collector
```

Proxy 的額外成本是多一個 server 和網路跳躍。自用場景下不需要；endpoint 公開時值得考慮。

## 偽造流量的影響分析

偽造流量進入 collector 後，對不同類型的分析影響不同。

**Error tracking 影響較低**：error 事件的價值在 stack trace 和 error message。偽造的 error 事件缺少真實的 stack trace — 即使格式正確，內容是編造的。Error 去重靠 fingerprint（error type + message + stack trace top frame），偽造事件產生的 fingerprint 不會和真實 error 碰撞，在 dashboard 上是獨立的 error group，容易識別和過濾。

**行為分析影響較高**：funnel 和 cohort 分析依賴事件計數的準確性。偽造的 `page.view` 和 `button.click` 事件直接灌水計數，導致轉換率失真。偽造事件越接近真實事件的結構（正確的 event name、合理的 timestamp），影響越大。

**資源消耗是固定成本**：無論事件內容是否真實，每筆事件都消耗 collector 的寫入 I/O、儲存空間、和查詢時間。Rate limit 把這個成本限制在可控範圍 — 每秒 N 筆是上限，無論來源是否合法。

### 事後標記策略

偵測到可疑流量後，collector 在事件中加入標記欄位而非直接丟棄。丟棄有誤殺風險 — 行銷活動的流量暴增、SDK 版本升級改變了事件模式、新平台的 SDK 上線 — 這些正常場景可能觸發異常偵測。

標記方式是在 collector 寫入時，對符合異常條件的事件附加 metadata：

```json
{
  "v": 1,
  "type": "event",
  "name": "button.click",
  "source": { "sdk": "js", "platform": "web", "app": "main-site" },
  "_flags": { "suspicious": true, "reason": "rate_anomaly" }
}
```

Dashboard 查詢預設排除 `_flags.suspicious = true` 的事件。需要調查時可以包含 — 看可疑事件的模式有助於判斷是攻擊還是誤判。

## 下一步路由

- Collector 端的認證和授權機制 → [Collector Access Control 實作](/monitoring/07-security-privacy/collector-access-control/)
- Transport 層的加密保護 → [Transport 安全](/monitoring/07-security-privacy/transport-security/)
- Endpoint 濫用的威脅分析 → [監控資料洩漏的 Threat Model](/monitoring/07-security-privacy/monitoring-data-threat-model/)
- SDK 端的寫入速率控制 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)
- 行為分析和 rule engine → [Rule Engine 設計](/monitoring/04-collector/rule-engine/)
- 偽造流量對資料完整性的影響 → [端到端資料完整性](/monitoring/04-collector/data-integrity/)
- Error fingerprint 讓偽造 error 容易辨識 → [Error Fingerprint 與去重分群](/monitoring/04-collector/error-fingerprint/)
