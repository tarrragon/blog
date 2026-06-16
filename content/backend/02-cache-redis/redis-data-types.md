---
title: "2.11 Redis data types 實作"
date: 2026-06-16
description: "說明 sorted set、bitmap、HyperLogLog、counter 與 hash 各自承擔的服務語意、容量行為與原子性邊界"
weight: 11
tags: ["backend", "cache", "redis", "data-types"]
---

Redis data types 的核心責任是把服務語意映射到適合的內建結構，讓讀寫操作的複雜度、原子性與記憶體成本由結構本身保證。選對型別，排行榜更新是一次 O(log N) 操作；選錯型別，同一個需求要拉回整包資料在應用端重算再寫回。本章承接 [2.8 cache data shape](/backend/02-cache-redis/cache-data-shape-access-pattern/) 的形狀選型，往下談每個型別的實作判讀與容量行為。

## 與 2.8 的分工

[2.8](/backend/02-cache-redis/cache-data-shape-access-pattern/) 回答「這份資料是單 key、集合、排序還是計數」這層形狀選型，本章回答「選定形狀後，這個型別的操作語意、原子性與記憶體曲線是什麼」。形狀選型決定方向，型別實作決定它在真實流量下的成本與正確性邊界。兩章分工互補：2.8 判斷形狀，本章確認該型別能不能撐住預期的存取節奏。本章涵蓋 sorted set、bitmap、HyperLogLog、counter 與 hash 這五個快取場景最常用的型別；list 與 stream 的責任偏向佇列與事件流，由 [模組三 message queue](/backend/03-message-queue/) 涵蓋，geo 這類空間型別不在本章範圍。

## sorted set：排行榜與時間線

sorted set 的責任是維護一組帶 score 的成員，並讓「依 score 排序取範圍」成為一次操作。它適合排行榜、時間線、優先佇列這類「要排序、要取 top-N、要查排名」的場景。

排行榜是最直接的應用。`ZADD leaderboard 5000 player:42` 寫入或更新分數，`ZREVRANGE leaderboard 0 9 WITHSCORES` 取前十名，`ZREVRANK leaderboard player:42` 查某玩家的排名。每個操作都是 O(log N)，不需要把整個排行榜拉到應用端排序。分數變動用 `ZINCRBY` 原子遞增，避免「讀分數、加分、寫回」的競態。

時間線是第二類應用。把訊息或事件的時間戳當 score，`ZADD timeline <timestamp> <event-id>`，就能用 `ZRANGEBYSCORE` 取某個時間窗口的事件，或用 `ZREVRANGE` 取最新 N 則。這個用法要注意容量：時間線會持續增長，需要搭配 `ZREMRANGEBYRANK` 或 `ZREMRANGEBYSCORE` 定期裁剪舊資料，否則 key 會無限膨脹。

sorted set 的判讀重點是 score 語意的正確性。score 是排序的唯一依據，score 設計錯誤會造成排序漂移：用浮點數當 score 時要注意精度，相同 score 的成員按字典序排列，需要穩定排序時要把 tie-break 維度編進 score 或成員名。容量上，sorted set 內部同時維護一個支援 O(1) 查找的 hash 與一個支援 O(log N) 排序的跳躍表（skiplist），兩份索引讓查找與排序都快，但每個成員要在兩個結構各存一份，記憶體成本高於單純的 set，成員數很大的排行榜要評估記憶體佔用。

## bitmap：布林狀態的省記憶體表示

bitmap 的責任是用單一 bit 表示每個實體的布林狀態，讓「大量實體的是否」用極小記憶體承載。它建構在 string 上、以 bit 操作存取，適合日活躍標記、功能開關位、簽到記錄這類「每個 id 對應一個是否」的場景。

日活躍使用者追蹤是典型應用。用日期當 key、使用者 id 當 offset，`SETBIT active:20260616 <user-id> 1` 標記某使用者當天活躍，`BITCOUNT active:20260616` 算當天活躍總數。一千萬個使用者只需要約 1.2 MB（一千萬 bit），相比為每個使用者存一筆記錄，記憶體成本低一到兩個數量級。多天的留存分析用 `BITOP AND` 把多天的 bitmap 做交集，算出連續活躍的使用者。

bitmap 的判讀重點是 offset 的密度。bitmap 的記憶體取決於最大 offset 而非實際設置的 bit 數：如果 user id 是稀疏的大整數（例如雪花 id），直接當 offset 會撐爆記憶體，需要先把 id 映射成稠密的連續整數。offset 稠密時 bitmap 極省空間，稀疏時反而浪費，這條判讀決定 bitmap 能不能用。

## HyperLogLog：基數估計

HyperLogLog 的責任是用固定的小記憶體估算一個集合的不重複元素數量，代價是放棄精確值換取近乎常數的空間。它適合 UV 統計、不重複事件計數這類「只要不重複的數量、不需要知道具體是誰」的場景。

獨立訪客（UV）統計是典型應用。`PFADD uv:20260616 <user-id>` 把訪客加入估計，`PFCOUNT uv:20260616` 取得不重複訪客數的估計值。HyperLogLog 每個 key 的記憶體在 dense 表示下固定在約 12 KB，無論加入一千還是一億個元素都不增長，標準誤差約 0.81%；元素數少時 Redis 用 sparse 編碼、記憶體遠低於 12 KB，超過可配置的閾值（`hll-sparse-max-bytes`，預設 3000 bytes）後才切換成 dense 表示。多天 UV 合併用 `PFMERGE` 把多個 HLL 合成一個再 count，算出跨天的不重複訪客。

HyperLogLog 的判讀重點是「估計值能不能接受」。它回答的是「大約多少不重複」，不能回答「某個特定元素在不在集合裡」，也不能取出集合成員。需要精確去重、或需要判斷成員存在性時，用 set 或 bitmap；只要量級且能容忍百分之一以內的誤差時，HyperLogLog 用固定小記憶體換取巨大的空間節省。把 HLL 的估計值當精確值報給財務或計費，是越界用法。

## 原子計數器：counter

counter 的責任是提供一個原子遞增的整數，讓並發場景下的計數不需要鎖。它建構在 string 上，`INCR`、`INCRBY`、`DECR` 都是原子操作，適合限流、配額、瀏覽計數這類高並發累加。

限流計數是典型應用，也跟 [rate limit](/backend/knowledge-cards/rate-limit) 卡片直接相關。固定窗口限流用 `INCR rate:<user>:<minute>` 累加當前窗口的請求數，第一次寫入時 `EXPIRE` 設定窗口長度，超過閾值就拒絕。原子性讓多個並發請求的計數不會互相覆蓋，這是用一般 `GET`/`SET` 做計數會踩到的競態。

counter 的判讀重點是原子性與過期窗口的對齊。`INCR` 本身原子，但「INCR 後再 EXPIRE」是兩個操作，若第一次 INCR 成功、EXPIRE 失敗，這個 key 會永不過期變成髒計數。最穩健的做法是用 Lua script 把 INCR 與 EXPIRE 包成一個原子單元；`SET key 1 EX <ttl> NX` 配合後續 INCR 能減少 EXPIRE 漏掉的機率（窗口第一次寫入時就帶上過期），但這個組合的兩步之間仍非原子，不視為與 Lua script 等效。這條對齊跟 [2.8 counter 形狀](/backend/02-cache-redis/cache-data-shape-access-pattern/) 提到的「原子性與過期窗口要對齊」是同一件事，本章補上具體實作。

## hash：結構化欄位的局部更新

hash 的責任是把一個實體的多個欄位存在同一個 key 下，並讓單一欄位可以獨立讀寫。它適合使用者摘要、商品局部欄位這類「整體是一個實體、但欄位會分別更新」的場景。

相比把整個實體序列化成一個 JSON blob，hash 的優勢是局部更新：`HSET user:42 last_seen <ts>` 只改一個欄位，不需要讀出整包、改一個值、再寫回。這在欄位更新頻繁的場景省下大量序列化成本與競態風險。`HGET` 取單一欄位、`HGETALL` 取全部、`HINCRBY` 對數值欄位原子遞增。

hash 的判讀重點是欄位責任要清楚。hash 讓欄位能獨立更新，但這也讓它容易滑向「半正式狀態」：當不同欄位由不同來源在不同時間更新，整個 hash 的一致性就變得模糊，某些欄位新、某些欄位舊。判讀條件是這些欄位是否真的能獨立成立；如果它們必須一起更新才有意義，blob 的整體替換反而比 hash 的局部更新更安全。

容量上 hash 有一個要注意的轉折：欄位數與欄位值在閾值內時（`hash-max-listpack-entries` 預設 128 個欄位、`hash-max-listpack-value` 預設 64 bytes）用緊湊的 listpack 編碼、記憶體很省，超過任一閾值就轉成 hashtable 編碼，記憶體成本明顯上升。設計大 hash 時要確認欄位數落在閾值內，否則會在某個規模點遇到非線性的記憶體增長。

## 型別選型的容量與原子性判讀

選型前要把存取語意、原子性需求與記憶體曲線一起考慮，而不是只看「能不能存」。

| 型別        | 承擔語意             | 原子操作                 | 記憶體行為                       |
| ----------- | -------------------- | ------------------------ | -------------------------------- |
| sorted set  | 排序、排名、時間線   | `ZINCRBY`、範圍操作      | 隨成員數線性增長，單成員成本偏高 |
| bitmap      | 大量實體的布林狀態   | `SETBIT`、`BITOP`        | 取決於最大 offset，稠密時極省    |
| HyperLogLog | 不重複數量估計       | `PFADD`、`PFMERGE`       | 固定約 12 KB，與元素數無關       |
| counter     | 並發累加計數         | `INCR`、`INCRBY`         | 單一整數，極小                   |
| hash        | 實體的可獨立更新欄位 | `HINCRBY`、`HSET` 單欄位 | 隨欄位數增長，小 hash 有編碼優化 |

sorted set 與 bitmap 都能做「統計」，但語意不同：sorted set 保留每個成員與其分數、可取明細，bitmap 只保留是否、取不出成員但極省空間。需要明細與排名用 sorted set，只需要聚合數量用 bitmap 或 HLL。

HyperLogLog 與 set 的分界是「要不要精確、要不要成員」。set 精確且可列舉，記憶體隨成員數增長；HLL 估計且不可列舉，記憶體固定。同一個 UV 需求，用 set 在大流量下記憶體會失控，用 HLL 換取固定成本但放棄精確值，選擇取決於誤差容忍度。

## 常見誤區

把 sorted set 當成「能排序的 set」而忽略 score 設計，會造成排序漂移。score 是排序的唯一依據，相同 score 按字典序，需要穩定且可預測的排序時要把 tie-break 維度設計進 score。

把 bitmap 用在稀疏 id 上，會讓記憶體被最大 offset 撐爆。bitmap 省記憶體的前提是 offset 稠密，稀疏 id 要先映射成連續整數，或改用其他結構。

把 HyperLogLog 的估計值當精確計數，會在計費、財務這類要求精確的場景出錯。HLL 是有誤差的估計，它的價值在用固定小記憶體換量級判斷，不是替代精確計數。

把多步操作當成原子，會在並發下產生競態。`INCR` 加 `EXPIRE`、`ZADD` 加裁剪都是多個命令，需要原子保證時用 Lua script 或 `MULTI`/`EXEC` 包起來。

## 判讀訊號

| 訊號                          | 判讀重點                     | 對應動作                                     |
| ----------------------------- | ---------------------------- | -------------------------------------------- |
| 排行榜在應用端拉全量排序      | 沒用 sorted set 的範圍操作   | 改 `ZREVRANGE` / `ZREVRANK` 在 Redis 排序    |
| bitmap key 記憶體異常膨脹     | offset 稀疏、被最大 id 撐大  | 把 id 映射成稠密整數，或換結構               |
| UV 統計記憶體隨流量無上限增長 | 用 set 做大基數去重          | 容忍誤差時改 HyperLogLog 固定成本            |
| 限流計數出現永不過期的髒 key  | INCR 與 EXPIRE 未原子化      | Lua script 包成原子單元                      |
| hash 欄位新舊不一致、難判讀   | 欄位責任不清、滑向半正式狀態 | 重新判斷欄位能否獨立，必要時改 blob 整體替換 |

排行榜在應用端拉全量排序是最常見的浪費：明明 sorted set 能 O(log N) 取 top-N，卻把整個集合讀回應用端用程式排序，在成員數大時造成不必要的網路與 CPU 成本。判讀方法是看排序邏輯在哪裡發生，把它推回 Redis 的範圍操作。

limit 計數的髒 key 不產生任何錯誤訊息，因此特別容易被忽略：INCR 成功但 EXPIRE 漏掉，這個 key 不會報錯，只是悄悄永不過期，問題要等到記憶體監控異常或限流誤判時才間接浮現。把 INCR 與 EXPIRE 原子化是最可靠的修法。

## 下一步路由

要回到資料形狀的選型判斷，回到 [2.8 cache data shape 與 access pattern](/backend/02-cache-redis/cache-data-shape-access-pattern/)。要看這些型別在高並發下的讀寫邊界與連線管理，接著讀 [2.1 高併發下的 Redis 讀寫邊界](/backend/02-cache-redis/high-concurrency-access/)。要看 stream 型別承擔的事件流責任，接著讀 [2.10 Pub/Sub 與即時 fan-out](/backend/02-cache-redis/pub-sub/) 與 [模組三 message queue](/backend/03-message-queue/)。
