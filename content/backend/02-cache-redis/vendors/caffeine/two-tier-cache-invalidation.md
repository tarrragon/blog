---
title: "Caffeine + Redis 兩層 cache：搭起來很容易，跨實例失效才是全部的問題"
date: 2026-06-16
description: "L1 Caffeine（process-local）+ L2 Redis（共享）的兩層 cache 程式碼三十行就寫完，但每個 JVM 實例有自己的 L1 副本、一個實例更新不會通知其他實例——跨實例 invalidation 才是這個架構的全部難度。本文展開兩層讀寫路徑、用 Redis pub/sub 廣播失效、5 個把 L1 stale 與 GC 寫成事故的 production 踩坑，以及哪些資料適合放 L1"
weight: 11
tags: ["backend", "cache", "caffeine", "two-tier", "invalidation", "deep-article"]
---

> 本文是 [Caffeine](/backend/02-cache-redis/vendors/caffeine/) overview 的 implementation-layer deep article。選型層（Caffeine vs Redis、process-local 的定位）見 overview；本文只處理「決定用 L1 Caffeine + L2 Redis 後，跨實例一致性怎麼處理」。API 以 [Caffeine wiki](https://github.com/ben-manes/caffeine/wiki) 為準、最後檢查日 2026-06-16。

## 兩層 cache 搭起來容易，難的在後面

L1 Caffeine + L2 Redis 的兩層 cache，讀寫路徑三十行 Java 就寫完：讀的時候先查 L1（process-local、奈秒級），miss 再查 L2（Redis、毫秒級），再 miss 才回源。它擋掉了大部分 Redis 的網路往返，對「每個請求重複讀同一份小資料」的場景效果立竿見影。

真正的難度不在搭兩層，在「每個 JVM 實例有自己的 L1 副本」這個事實。假設有 10 個 application 實例，就有 10 份獨立的 Caffeine cache。實例 A 更新了某個 user 的資料、寫進 L2 Redis，但實例 B、C、D... 的 L1 還握著舊值——它們不知道資料變了。下一個打到實例 B 的請求，L1 命中，回的是舊值。Redis 是對的，但讀不到 Redis，因為 L1 先攔截了。

這就是兩層 cache 的核心問題：L1 的速度來自「不跟任何人協調」，而一致性恰恰需要協調。本文聚焦這個矛盾——兩層讀寫路徑只是背景，跨實例 invalidation 才是全部的工程量。

## 核心概念：L1 的 stale 從哪裡來

兩層 cache 的一致性問題，根源是 L1 的三個特性：

**L1 是 per-instance 的私有副本**。Caffeine 活在 JVM heap 內，每個實例一份。這是它快的原因（無網路、無序列化），也是它難一致的原因（無法被其他實例直接更新或清除）。L2 Redis 是共享的，所以 L2 一致相對容易；L1 才是 stale 的來源。

**寫入只更新本地 L1 + 共享 L2**。實例 A 處理一個更新：寫 L2 Redis（所有實例可見）+ 更新或清除自己的 L1。但 A 沒有辦法直接碰 B 的 L1——B 的 L1 還是舊的，直到它自己過期或被通知。

**沒有通知機制，L1 只能靠 TTL 自然過期**。如果不做任何跨實例協調，L1 的 stale window 就等於 L1 的 TTL。把 L1 TTL 設短（幾秒到幾十秒）是最簡單的「容忍 stale」策略——犧牲一點新鮮度換掉協調的複雜度。需要更快失效就得主動廣播。

跨實例失效的標準解法是用 L2 Redis 的 pub/sub 當廣播通道：任一實例更新資料時，往一個 channel 發一條「key X 失效了」的訊息，所有實例訂閱這個 channel、收到就清掉自己 L1 對應的 entry。這把「各自為政的 L1」連成一個能協同失效的網。

## 配置：兩層讀寫 + pub/sub 失效的程式碼

兩層讀取路徑（L1 → L2 → origin）：

```java
public User getUser(String id) {
    // L1：Caffeine、奈秒級、命中就回
    User u = l1.getIfPresent(id);
    if (u != null) return u;

    // L1 miss → L2 Redis、毫秒級
    String json = redis.get("user:" + id);
    if (json != null) {
        u = deserialize(json);
        l1.put(id, u);                 // 回填 L1
        return u;
    }

    // L2 miss → 回源 + 雙層回填
    u = userRepository.findById(id);
    redis.setex("user:" + id, 300, serialize(u));  // L2 TTL 5 分鐘
    l1.put(id, u);                     // L1
    return u;
}
```

跨實例失效（寫入時往 Redis pub/sub 廣播、所有實例清 L1）：

```java
// L1 設短 TTL 當保險（廣播漏掉時的上界）
Cache<String, User> l1 = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofSeconds(30))  // 廣播失效之外的兜底
    .build();

// 寫入：更新 L2 + 廣播失效
public void updateUser(User u) {
    userRepository.save(u);
    redis.setex("user:" + u.id(), 300, serialize(u));  // 更新 L2（TTL 對齊讀路徑的 300s）
    redis.publish("cache:invalidate", u.id());   // 廣播給所有實例
    l1.invalidate(u.id());                        // 清自己的 L1
}

// 每個實例啟動時訂閱、收到就清本地 L1
redis.subscribe("cache:invalidate", message -> l1.invalidate(message));
```

關鍵：L1 的短 TTL 是廣播機制的兜底——即使某個實例漏掉一條 pub/sub 訊息（pub/sub 是 fire-and-forget、訂閱者離線會錯過），L1 最多 stale 到 TTL 過期。廣播負責「快」，TTL 負責「最終」。

## Production 故障演練

### Case 1：更新後其他實例持續回舊值

**徵兆**：使用者改了資料、自己刷新看到新值（打到處理寫入的實例），但同事看到的還是舊值（打到別的實例），且持續好幾分鐘。

**根因**：只更新了寫入實例的 L1 與 L2，沒有跨實例廣播。其他實例的 L1 還握著舊值、攔截了讀取、根本沒查到已更新的 L2。stale window 等於 L1 TTL（如果 TTL 設很長就是好幾分鐘）。

**修法**：

1. 加 Redis pub/sub 廣播失效，寫入時通知所有實例清 L1
2. 廣播之外把 L1 TTL 設短當兜底（幾秒到幾十秒），縮短漏訊息時的 stale 上界
3. 強一致需求的資料根本不該進 L1——L1 的本質就是「容忍一個 stale window 換速度」
4. 對應 [cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/) 的新鮮度邊界判斷

### Case 2：pub/sub 漏訊息、個別實例 L1 卡舊值

**徵兆**：多數實例更新後正常，但偶爾某個實例持續回舊值，直到重啟或 TTL 過期。

**根因**：Redis pub/sub 是 fire-and-forget——訂閱者在訊息發出的瞬間若斷線（網路抖動、GC pause、重連中），就永久錯過那條失效訊息。沒有兜底的話，那個實例的 L1 會一直 stale 到 TTL。

**修法**：

1. L1 TTL 設短是必要兜底，不要依賴 pub/sub 100% 送達（它不保證）
2. 需要可靠失效用 Redis Streams（有 consumer group + 重放）取代 pub/sub，代價是複雜度
3. 監控各實例的 L1 命中率與 stale 投訴，個別實例異常代表漏訊息
4. 接受 pub/sub 的 at-most-once 語意，用 TTL 補足最終一致

### Case 3：L1 太大撐爆 heap、Full GC 風暴

**徵兆**：加了 L1 後 application 的 GC 時間變長、偶發 Full GC 導致請求暫停（STW），延遲尖刺。

**根因**：Caffeine 預設 on-heap，L1 的 `maximumSize` 設太大、cache 的物件佔據大量 heap，增加 GC 掃描與回收壓力。大物件 + 大容量直接推高 old gen 佔用。

**修法**：

1. `maximumSize` 對齊 heap 預算，用 `recordStats()` 看實際記憶體佔用
2. 用 `maximumWeight` + weigher 按物件實際大小限制（不只筆數），避免大物件撐爆
3. L1 只放「小、熱、重複讀」的資料，大物件留 L2 Redis（off-heap 視角）
4. 監控 GC 時間與 old gen 佔用，L1 容量是可調的 GC 旋鈕

### Case 4：L1 快取了不該快取的 per-user 大物件

**徵兆**：L1 命中率偏低、heap 壓力大、效果不如預期。

**根因**：把 per-user 的大物件或低重複率的資料放 L1。L1 的價值在「少量資料被大量重複讀」（如設定檔、熱門商品、權限表），per-user 資料每個 user 一份、重複率低、塞滿 L1 又命中率低。

**修法**：

1. L1 只放高重複率的共享熱資料（config、feature flag、熱門 item、權限）
2. per-user 低重複資料放 L2 Redis 就好，不要進 L1
3. 用 `recordStats()` 的 hit rate 驗證——L1 命中率低代表放錯資料
4. 對應 [2.4 cache data shape](/backend/02-cache-redis/cache-data-shape-access-pattern/) 的存取形狀判斷

### Case 5：refreshAfterWrite 與 expireAfterWrite 混淆、行為不如預期

**徵兆**：以為設了自動刷新、結果到期還是 miss 阻塞回源；或以為會過期、結果一直回舊值。

**根因**：`expireAfterWrite`（到期 entry 失效、下次讀 miss + 阻塞載入）跟 `refreshAfterWrite`（到期後第一個讀觸發背景刷新、舊值立即回、不阻塞）語意不同，混用導致行為不符預期。

**修法**：

1. 要「到期就不可用」用 `expireAfterWrite`；要「到期背景刷新、舊值先頂」用 `refreshAfterWrite`
2. 兩者可組合：`refreshAfterWrite` 短 + `expireAfterWrite` 長，得到「背景刷新 + 最終過期」
3. `refreshAfterWrite` 避免 [stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)（舊值先服務、單一背景刷新），適合熱 key
4. 用 `LoadingCache` 的 `build(key -> load)` 配 refresh，行為以官方 wiki 為準

## Capacity / cost 邊界

兩層 cache 的容量判讀，核心在 L1 命中率、stale window 與 GC：

| 訊號                   | 健康區間                   | 警戒與動作                                     |
| ---------------------- | -------------------------- | ---------------------------------------------- |
| L1 hit rate            | 高（放對高重複資料）       | 低 → 放錯資料（per-user 大物件）、改放 L2      |
| L1 stale window        | ≤ L1 TTL（廣播正常更短）   | 過長 → TTL 太長或廣播沒做                      |
| GC 時間 / old gen 佔用 | 穩定、無 Full GC 風暴      | 升高 → L1 太大、降 maximumSize / maximumWeight |
| pub/sub 失效送達率     | 高（但不保證 100%）        | 漏訊息 → TTL 兜底、或改 Streams                |
| L1 vs L2 命中分層      | L1 擋大部分、L2 擋 L1 miss | L1 命中低 → 兩層沒分工好                       |

撞牆後的路由判斷：

- **需要強一致 / 不能容忍任何 stale**：L1 process-local 本質有 stale window，不該放這類資料。強一致只用 [Redis / Valkey](/backend/02-cache-redis/vendors/redis/) 共享層（甚至直接回源）。
- **L1 容量需求超過 heap**：on-heap Caffeine 撐不住，用 off-heap 方案（Ehcache off-heap tier）或把資料留 L2 Redis。
- **可靠失效（不能漏）**：pub/sub 是 at-most-once，要可靠用 Redis Streams 的 consumer group，代價是複雜度。
- **非 JVM 服務**：Caffeine 綁 JVM，其他語言用對應的 process-local cache（Go ristretto、Rust moka），兩層架構的思路相同。

## 整合 / 下一步

兩層 cache 的工程量集中在跨實例一致性，它跟多個議題交織：

- **跟 [Caffeine overview](/backend/02-cache-redis/vendors/caffeine/)**：overview 點到「跨實例 invalidation 是固有限制」、本文展開 pub/sub 廣播 + TTL 兜底的具體解法。
- **跟 [Redis connection / pipeline](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)**：L1 的價值正是消除 L2 Redis 的 RTT 稅，兩層 cache 是 RTT 優化的極致（L1 命中連網路都省）。
- **跟 [2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)**：hot key 的兩層解法（local cache + Redis）就是這個架構，L1 擋掉打在單一熱 key 的洪峰。
- **跟 [Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)**：每次互動查多個 cache 的服務，L1 Caffeine 可擋掉重複讀、降低 L2（ElastiCache）的壓力與 RTT——但 per-user 配對資料重複率低、要判斷哪些放得進 L1。

## 相關連結

- 上游 vendor 頁：[Caffeine](/backend/02-cache-redis/vendors/caffeine/)
- L2 對照：[Redis 記憶體與淘汰](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)、[Redis 連線 / pipeline](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)
- 上游概念：[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)、[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
