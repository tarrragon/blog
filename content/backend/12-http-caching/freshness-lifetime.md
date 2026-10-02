---
title: "12.2 新鮮度期限的計算：max-age、s-maxage、Expires 與啟發式期限"
slug: "freshness-lifetime"
date: 2026-10-02
description: "快取在不詢問 origin 的情況下可以直接使用一份副本多久：新鮮度期限的取用順序、Age 標頭與副本年齡的計算、沒有明確期限時規範允許的啟發式期限，以及 Chromium、Firefox、Varnish、nginx 在啟發式期限上的差異"
weight: 2
tags: ["backend", "http-caching", "cache-control", "freshness"]
---

這篇整理快取判斷一份副本還能不能直接使用的計算方式。範圍從副本已經被保存開始（哪些回應能被保存見 [12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/)）；副本過期之後怎麼處理在 [12.3 過期副本的驗證：條件請求、304 回應、no-cache 與 no-store](/backend/12-http-caching/revalidation/)。

規範用兩個量描述一份副本：**新鮮度期限**（freshness lifetime，這份副本從 origin 產生起可以被直接使用多久）與**目前年齡**（current age，這份副本從 origin 產生或最近一次驗證起過了多久）。CDN 的設定介面與 Varnish 的參數把新鮮度期限稱為 [TTL](/backend/knowledge-cards/ttl/)（time to live）。目前年齡小於新鮮度期限的那段時間稱為**新鮮期間**，兩者的差就是副本剩下的新鮮時間。判斷式只有一行：

```text
response_is_fresh = (freshness_lifetime > current_age)
```

（RFC 9111 §4.2）新鮮的副本可以不詢問 origin 直接拿來回應請求；過期的副本要先驗證，或在 [12.6 過期副本的延用：stale-while-revalidate 與 stale-if-error](/backend/12-http-caching/serving-stale/) 說明的條件下延用。

## 新鮮度期限的取用順序

快取從回應標頭裡依序找第一個存在的值當新鮮度期限（RFC 9111 §4.2.1）：

1. 快取是共用快取，而且回應有 `s-maxage`：用 `s-maxage` 的值。
2. 回應有 `max-age`：用 `max-age` 的值。
3. 回應有 `Expires`：用 `Expires` 減去 `Date` 的值；回應沒有 `Date` 時，以收到回應的時間代替。
4. 以上都沒有：沒有明確期限，快取可以改用啟發式期限（見〈沒有明確期限時的啟發式期限〉）。

用 `Expires` 減 `Date` 而不是減快取自己的時鐘，是為了避開 origin 與快取之間的時鐘偏差：兩個時間都由 origin 的時鐘產生，相減的結果不受快取那台機器的時間影響。

幾條處理衝突與異常值的規則：

- 同時有 `max-age` 與 `Expires` 時，忽略 `Expires`（RFC 9111 §5.3）。
- `Expires` 的值無法解析，特別是常見的 `Expires: 0`，當成過去的時間處理，也就是回應一送到就已經過期（RFC 9111 §5.3）。
- 指令互相衝突（例如同時有 `max-age` 與 `no-cache`）時，規範用小寫的 should（一般用語，不是 RFC 以大寫 SHOULD 標示的要求）建議採用限制最嚴的那個（RFC 9111 §4.2.1）。

## Age 標頭與副本的目前年齡

`Age` 標頭記錄的是：

> the cache's estimate of the number of seconds since the origin server generated or validated the response.（RFC 9111 §4.2.3）

快取不經驗證、直接用保存的副本回應請求時，必須在回應裡帶上 `Age`，值是這份副本目前的年齡（RFC 9111 §4）。下游的快取收到帶 `Age` 的回應，會把這個值算進自己那份副本的年齡。規範給的保守算法還計入網路傳輸的延遲，結構是：

```text
corrected_initial_age = max(收到時 Date 與自己時鐘的差, 上游給的 Age + 這次請求的往返時間)
current_age = corrected_initial_age + 副本在自己這裡放了多久
```

這個機制讓年齡沿著快取鏈累加，影響的是下游拿到的剩餘新鮮時間。一個回應帶 `Cache-Control: max-age=600`，在 CDN 上放了 500 秒之後被某個瀏覽器請求，CDN 回給瀏覽器的回應帶 `Age: 500`，瀏覽器算出的剩餘新鮮時間就只有 100 秒，不是 600 秒。origin 寫的 `max-age` 是從 origin 產生回應起算的總期限，不是每一個快取各自重新計時。

送不送 `Age`，實作之間就有差異。實測時 Varnish 7.7 每次由快取回應都送出遞增的 `Age`；nginx 1.27 的 proxy_cache 不送 `Age`，而且把 `Date` 換成送出當下的時間。下游原本可以用 `Date` 與自己時鐘的差估出副本的年齡；`Age` 沒送、`Date` 又被換成送出當下的時間，下游（例如接在 nginx 外面的 CDN）就估不出來，因此會把副本多用一段時間，長度等於副本在 nginx 裡已經放了的時間。規範也提醒，回應裡沒有 `Age` 不代表它剛從 origin 拿來（RFC 9111 §5.1）。

## 沒有明確期限時的啟發式期限

回應沒有 `s-maxage`、`max-age`、`Expires` 時，規範允許快取自己估一個期限，稱為**啟發式期限**（heuristic freshness）。允許的範圍有兩個限制（RFC 9111 §4.2.2）：

- 只能用在**狀態碼屬於可啟發式快取的回應**上，或回應用 `public` 這類指令明確標成可快取。
- 回應有明確期限時，不可以使用啟發式期限。

可啟發式快取的狀態碼由 RFC 9110 列舉：

> 200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, and 501（RFC 9110 §15.1）

302 與 307 不在這份可啟發式快取的清單裡，規範不允許快取保存沒有快取標頭的 302、307（[12.1 HTTP 回應的保存位置：私有快取與共用快取](/backend/12-http-caching/cache-storage-locations/) 的〈可以被保存的回應〉）；實測的 Varnish 7.7 與 nginx 1.27 都照做，但部分 CDN 的文件記載會替沒有快取標頭的轉址套用自己的預設保存時間，以各家文件為準。301 與 308 在清單裡，沒有快取標頭時可以被保存，能直接使用多久由快取自己估算。

規範沒有規定估算的演算法，只建議一個上限的參考做法：以回應的 `Last-Modified` 為起點，期限不超過「從那個時間點到現在」這段間隔的某個比例。

> caches are encouraged to use a heuristic expiration value that is no more than some fraction of the interval since that time. A typical setting of this fraction might be 10%.（RFC 9111 §4.2.2）

措辭是「encouraged」與「might」，10% 是例子，不是規定。一個在一年前修改過的檔案，照 10% 估算的新鮮度期限約 36 天；一個剛修改過的檔案，期限就很短。這個做法的假設是：很久沒改的內容，短期內也不太會改。

## 各實作的啟發式期限

因為規範沒有規定演算法，各實作的做法差很多。以下是 2026-10-02 讀原始碼與實測的結果，版本會變，套用到自己的環境前要查當下的文件或原始碼：

| 實作              | 啟發式期限的做法                                                                                                                                      | 資料來源                                                                     |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Chromium          | 200、203、206 用 `Last-Modified` 間隔的 10%，不設上限，沒有 `Last-Modified` 時為 0；300、301、308、410 沒有明確期限時**永不過期**；其他狀態碼為 0     | `net/http/http_response_headers.cc` 的 `GetFreshnessLifetimes`               |
| Firefox           | 用 `Last-Modified` 間隔的 10%，上限一週；410 永不過期                                                                                                 | `netwerk/protocol/http/nsHttpResponseHead.cpp` 的 `ComputeFreshnessLifetime` |
| Varnish 7.7       | 不看 `Last-Modified`，沒有明確期限時套用自己的預設存活時間（參數 `default_ttl`）；只有 `Last-Modified` 的回應與完全沒有標頭的回應，實測得到相同的期限 | 實測與 `varnishlog` 的 TTL 紀錄                                              |
| nginx proxy_cache | 沒有明確期限、也沒有用 `proxy_cache_valid`（nginx 依狀態碼指定預設保存時間的設定）指定時不保存                                                        | 實測                                                                         |

上面這張各實作的啟發式期限表，解釋了沒有快取標頭的 301 為什麼在各快取上的結果不同。這樣的 301 在 Chromium 上永不過期，副本只要還在快取裡，就不會再向 origin 確認：實測時先讓 Chrome 跟著 `/r301` 轉到 `/target-a`，再把 origin 的轉址目的地改成 `/target-b`，Chrome 再次前往 `/r301` 時沒有送出請求，直接去了 `/target-a`。Chrome 不再送出請求，origin 的存取紀錄裡也就看不到這些使用者，這類問題只會從使用者回報裡出現。同一個回應在 Varnish 上只在預設存活時間內直接使用，在 nginx 上完全不保存。同一組標頭在三個快取上得到三種結果，原因是這個回應把新鮮度期限交給了各實作自己估。

所以內容可能改變的回應，要明寫新鮮度期限：要被保存就寫 `max-age`（以及需要時的 `s-maxage`），不要被保存就寫 `no-store`。不寫等於把期限交給每一個經過的快取各自決定。

## 新鮮度期限與實際保存時間

新鮮度期限規定的是副本**最多**可以被直接使用多久，不保證快取會保存那麼久。規範把快取定位為選用功能：

> Although caching is an entirely OPTIONAL feature of HTTP（RFC 9111 §2）

規範要求的是哪些回應不能存、不能重用，不要求快取把副本存到期滿。快取空間滿了、副本太少被用到、快取重啟，都會讓副本提早消失。所以 `max-age` 不能拿來當「這段時間內 origin 一定不會收到請求」的保證：容量規劃時 origin 要能承受副本提早消失、快取命中率下降時多出來的回源流量：容量怎麼估見 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)；命中率掉下來時擋住回源尖峰的手段見 [Origin Protection](/backend/knowledge-cards/origin-protection/) 卡。

新鮮度期限也只約束快取，不約束瀏覽器怎麼顯示畫面：

> freshness applies only to cache operation; it cannot be used to force a user agent to refresh its display or reload a resource.（RFC 9111 §4.2）

使用者按上一頁看到的舊畫面，屬於瀏覽器的歷史機制，不受新鮮度期限約束，見 [12.7 瀏覽器端的快取行為：重新整理、強制重新整理與上一頁](/backend/12-http-caching/browser-cache-behavior/)。
