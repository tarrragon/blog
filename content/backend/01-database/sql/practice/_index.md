---
title: "SQL 漸進式練習網站規格與題庫設計"
breadcrumb: "SQL 練習"
date: 2026-11-24
description: "規劃從基礎 SQL 語法到進階查詢設計與效能取捨的選擇題練習網站，以及透過作答困惑回頭補強 SQL 教材時"
weight: 85
tags: ["sql", "practice", "curriculum", "spec"]
draft: true
---

這份規格書整理 SQL 自我練習網站的設計方案與完整題庫藍圖，負責把[SQL：這個語言為什麼長這樣](/backend/01-database/sql/)的語意模型與設計原則，接回從零開始的語法練習與真實商業決策。網站尚未開始撰寫程式，這個階段先鎖定學習梯度、多商業領域與多題組隨機抽題機制、高複雜度複合陷阱題、各階段選擇題與選項優劣分析，以及把練習困惑回饋到既有 SQL 教材的閉環。

## 設計動機與現有 SQL 教材的缺口

既有的 SQL 分類（`SQL.0` 至 `SQL.23`）以「寫得出基本 `SELECT` 與 `JOIN`」為起點，專注討論宣告式求值順序、連接保護範圍、靜默錯誤、執行計畫代價與跨引擎差異。沒有基礎語法實作經驗的學習者直接讀這套文章時，會在三個位置卡關：

- **缺基礎語法的肌肉記憶**：文章直接對比 `ON` 與 `WHERE`、`GROUP BY` 與視窗函式，沒有先透過基礎單表查詢、排序、聚合與寫入建立語法手感。
- **難以體會原則背後的業務意義**：只看抽象規則（「外連接補 `NULL`」「`NOT IN` 遇 `NULL` 回空」），沒有先在商業需求下犯過錯、看過資料反例，讀文章時只看到規則條文。
- **面對開放寫法缺乏取捨座標**：SQL 容許用多種合法寫法解同一個需求；學習者需要的判定能力包含辨別對錯，更包含在資料量、索引、約束與並行條件下比較不同寫法的成本與失效條件。

因此本練習系統採用**選擇題為主、全選項優劣分析為核心**的設計：前段透過語法選擇題建立基本讀寫能力，中段透過「都能跑但不報錯」的靜默錯誤題建立語意模型直覺，後段透過商業情境設計題訓練在效能、資料分布、跨引擎與並行寫入之間的工程取捨。

## 反背題與長期鑑別力架構

如果每個考點只綁死同一套題目，練習兩三輪後學習者會記住表名與選項長相（「看到評價表就選 `NOT EXISTS`」），即使觀念沒有真正內化也能拿到滿分，題庫隨即失去鑑別能力。單純把題目裡的常數 `300` 換成 `500` 或只打亂選項字母，學習者仍能靠辨認 SQL 骨架直接猜中答案。

為讓反覆練習持續具備鑑別力並拉高實戰複雜度，本規格把「要檢驗的能力」與「單次呈現的題目」拆開，導入四層結構化變形機制：

| 機制                       | 做法                                                                                                                                                                                                                                 | 防止的失真形態                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| 能力節點 × 多題組變體池    | 將 30 個學習目標定義為獨立**能力節點**（`S1-01` 至 `S6-05`），每個節點至少配置 3 套結構相異的變體題（基本題池 90 題起跳，並可持續擴充），每次抽題優先避開近期做過的變體，渲染時同步打亂選項順序                                      | 防止靠記住「Q08 選 B」刷出假進步                                                         |
| 三大真實商業領域輪替       | 除「紙頁書店」外，另建「雲課堂」線上訂閱制平台與「捷配物流」B2B 配送調度平台兩套獨立 Schema；同一個 SQL 觀念在三個領域換成完全不同的資料表、業務問句與干擾項                                                                         | 防止把觀念綁死在單一表名（如 `reviews`、`orders`），驗證跨情境遷移能力                   |
| 前提翻轉與多視角出題       | 同一能力節點的變體池輪替四種出題視角：**寫法挑選**、**反例擊破**（給一段會靜默出錯的查詢，選出能讓它算錯的那筆資料）、**執行計畫／事故診斷**、**前提翻轉**（把約束、索引或資料量前提改掉，讓原本較慢或違規的選項成為新前提下的正解） | 防止把條件式取捨背成死口訣（例如無條件排斥 `NOT IN` 或無條件盲選 `EXISTS`）              |
| 跨概念複合陷阱題與盲測模式 | 在單點題池之外獨立建立**跨概念複合陷阱題池**（每題同時疊加兩個以上陷阱，例如外連接撤銷保護疊加列數膨脹與整數除法截斷），並提供隱藏階段與考點標籤的**盲測鑑別模式**                                                                   | 防止只在「題目已經提示本題考 `ON` 與 `WHERE`」的輔助下答對，真實檢驗面對陌生需求的診斷力 |

### 熟練度判定標準

練習網站評定一個能力節點是否達到「觀念掌握（Mastered）」，不採用單次答對，必須同時滿足三項條件：

1. 在至少**兩個不同商業領域**的變體題作答正確。
2. 至少通過一次**非寫法挑選視角**（反例擊破、執行計畫診斷或前提翻轉）的題目。
3. 在**盲測模式**（隱藏階段標題與對應教材提示）下作答正確一次。

## 三套貫穿式商業網站情境與 Schema

三大商業領域各自模擬一套真實營運網站，且都內建專屬的邊界反例資料。領域甲沿用既有 SQL 教材的小書店背景，作為初學起手與對照基準；領域乙與領域丙提供結構不同的關聯形狀（訂閱狀態機、階層課程、時序事件流、多倉派工排班），用於隨機抽題與跨領域鑑別。

### 領域甲（`bookstore`）：「紙頁書店」線上書城與門市系統

為讓練習結果直接對應既有 SQL 教材，領域甲沿用[SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)的業務背景，將它從剛開張的小書店擴展為隨規模演化的電商網站。所有練習題統一使用小寫英文識別字（`snake_case`），方便直接匯入 SQLite 與 PostgreSQL 執行。

### 資料庫 Schema 的三期演化

學習者不需要一次背下所有資料表；練習網站會依階段逐步解鎖新表，對應網站真實的成長歷程。

#### 營運初期（階段一至階段二使用）：核心銷售與評價

```sql
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL,
  city        TEXT,
  created_at  TEXT NOT NULL
);

CREATE TABLE categories (
  category_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  parent_id   INTEGER REFERENCES categories(category_id)
);

CREATE TABLE books (
  book_id     INTEGER PRIMARY KEY,
  title       TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(category_id),
  price       INTEGER NOT NULL,
  stock       INTEGER NOT NULL,
  is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE orders (
  order_id     INTEGER PRIMARY KEY,
  customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
  status       TEXT NOT NULL, -- 'pending' | 'paid' | 'shipped' | 'cancelled' | 'refunded'
  total_amount INTEGER NOT NULL,
  ordered_at   TEXT NOT NULL
);

CREATE TABLE order_items (
  order_item_id INTEGER PRIMARY KEY,
  order_id      INTEGER NOT NULL REFERENCES orders(order_id),
  book_id       INTEGER NOT NULL REFERENCES books(book_id),
  quantity      INTEGER NOT NULL,
  unit_price    INTEGER NOT NULL
);

CREATE TABLE reviews (
  review_id  INTEGER PRIMARY KEY,
  order_id   INTEGER REFERENCES orders(order_id), -- 刻意允許 NULL 模擬匯入缺漏資料
  book_id    INTEGER NOT NULL REFERENCES books(book_id),
  rating     INTEGER NOT NULL, -- 1 到 5
  created_at TEXT NOT NULL
);
```

#### 營運成長期（階段三至階段五使用）：行銷、對帳與效能壓力

```sql
CREATE TABLE coupons (
  coupon_id     INTEGER PRIMARY KEY,
  code          TEXT NOT NULL,
  discount_type TEXT NOT NULL, -- 'fixed' | 'percent'
  discount_val  INTEGER NOT NULL
);

CREATE TABLE order_coupons (
  order_id  INTEGER NOT NULL REFERENCES orders(order_id),
  coupon_id INTEGER NOT NULL REFERENCES coupons(coupon_id),
  PRIMARY KEY (order_id, coupon_id)
);

CREATE TABLE daily_sales_snapshots (
  snapshot_date TEXT NOT NULL,
  store_code    TEXT NOT NULL,
  revenue       INTEGER NOT NULL,
  PRIMARY KEY (snapshot_date, store_code)
);
```

#### 多實例高流量期（階段六使用）：背景任務與門市排班

```sql
CREATE TABLE export_jobs (
  job_id     INTEGER PRIMARY KEY,
  status     TEXT NOT NULL, -- 'queued' | 'running' | 'done' | 'failed'
  payload    TEXT NOT NULL,
  claimed_by TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE store_shifts (
  shift_id    INTEGER PRIMARY KEY,
  staff_id    INTEGER NOT NULL,
  store_code  TEXT NOT NULL,
  starts_at   TEXT NOT NULL,
  ends_at     TEXT NOT NULL
);
```

### 刻意埋設的邊界資料（供反例驗證）

網站內建的基準測試資料集固定包含以下邊界列，讓每道選擇題的「選項差異」都能用真實輸出證明：

- 沒有下過任何訂單的顧客（例如顧客 `雅文`），以及未填寫 `city`（`NULL`）的顧客。
- 有訂單但沒有評價的訂單、同一筆訂單對應兩則以上評價（五星與三星並存）的資料，以及一筆 `order_id` 為 `NULL` 的異常匯入評價。
- 同一天同一分鐘成立的多筆同金額訂單（用來驗證分頁排序鍵不唯一時的重複與遺漏）。
- 大小寫混排的顧客 `email`（例如 `Alice@Example.com` 與 `alice@example.com`），以及單一熱點重複出現上千次的測試資料分片。
- 某個門市在連續日期中刻意跳過公休日（缺測日期），用來驗證視窗函式 `LAG()` 與日曆「前一天」的差異。

### 領域乙（`cloud-academy`）：「雲課堂」線上訂閱制教學平台

SaaS 訂閱與學習進度系統天然包含「試用期、多筆續約帳單、未開課學員、重複 Webhook、多裝置同時更新進度」等複雜關聯，特別適合出題檢驗狀態篩選、去重、冪等寫入與分組彙總。

```sql
CREATE TABLE users (
  user_id      INTEGER PRIMARY KEY,
  display_name TEXT NOT NULL,
  email        TEXT NOT NULL,
  country      TEXT,
  joined_at    TEXT NOT NULL
);

CREATE TABLE courses (
  course_id        INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  track            TEXT NOT NULL, -- 'backend' | 'data' | 'devops'
  prerequisite_id  INTEGER REFERENCES courses(course_id),
  monthly_fee_tier INTEGER NOT NULL,
  is_published     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE subscriptions (
  sub_id     INTEGER PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(user_id),
  plan_code  TEXT NOT NULL, -- 'free' | 'pro' | 'team'
  status     TEXT NOT NULL, -- 'trialing' | 'active' | 'past_due' | 'canceled'
  started_at TEXT NOT NULL,
  ended_at   TEXT
);

CREATE TABLE invoices (
  invoice_id INTEGER PRIMARY KEY,
  sub_id     INTEGER REFERENCES subscriptions(sub_id), -- 允許 NULL 模擬手動補單匯入缺漏
  amount     INTEGER NOT NULL,
  status     TEXT NOT NULL, -- 'open' | 'paid' | 'void' | 'refunded'
  issued_at  TEXT NOT NULL
);

CREATE TABLE lesson_progress (
  progress_id   INTEGER PRIMARY KEY,
  user_id       INTEGER NOT NULL REFERENCES users(user_id),
  course_id     INTEGER NOT NULL REFERENCES courses(course_id),
  lesson_no     INTEGER NOT NULL,
  completed_at  TEXT,
  watch_seconds INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE webhook_events (
  event_id    INTEGER PRIMARY KEY,
  provider    TEXT NOT NULL, -- 'stripe' | 'newebpay'
  external_id TEXT NOT NULL,
  status      TEXT NOT NULL, -- 'pending' | 'processing' | 'done' | 'dead'
  received_at TEXT NOT NULL
);
```

領域乙刻意埋設的邊界資料：

- 註冊了帳號但從未訂閱、以及訂閱過但從未開啟任何課程的學員。
- 同一位學員先取消方案後又重新訂閱（一人對應多筆 `subscriptions`），以及每筆訂閱對應多期 `invoices` 與多筆 `lesson_progress`（雙重一對多膨脹）。
- `invoices.sub_id` 為 `NULL` 的歷史人工開立帳單，以及 `lesson_progress.completed_at` 為 `NULL`（看過一半但未完課）的列。
- 來自金流商重送的重複 `external_id` 與多位 worker 同時輪詢的 `webhook_events` 佇列。

### 領域丙（`swift-logistics`）：「捷配物流」B2B 倉儲與配送調度平台

物流與排班系統天然帶有「一筆托運單多件包裹、跨時區掃描事件流、司機時段防重疊、海量歷史運單分頁與高基數對帳」等壓力，適合出題檢驗視窗函式時間間隔、大表分頁、索引形狀與並行約束。

```sql
CREATE TABLE warehouses (
  warehouse_id INTEGER PRIMARY KEY,
  code         TEXT NOT NULL,
  region       TEXT NOT NULL,
  parent_hub_id INTEGER REFERENCES warehouses(warehouse_id)
);

CREATE TABLE merchants (
  merchant_id INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  account_key TEXT NOT NULL,
  tier        TEXT -- 允許 NULL 代表未分級新客戶
);

CREATE TABLE shipments (
  shipment_id  INTEGER PRIMARY KEY,
  merchant_id  INTEGER NOT NULL REFERENCES merchants(merchant_id),
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
  status       TEXT NOT NULL, -- 'created' | 'in_transit' | 'delivered' | 'returned'
  fee_cents    INTEGER NOT NULL,
  created_at   TEXT NOT NULL
);

CREATE TABLE shipment_events (
  event_id    INTEGER PRIMARY KEY,
  shipment_id INTEGER REFERENCES shipments(shipment_id), -- 允許 NULL 模擬掃碼槍異常孤兒事件
  event_type  TEXT NOT NULL, -- 'picked' | 'hub_in' | 'out_for_delivery' | 'signed' | 'exception'
  recorded_at TEXT NOT NULL
);

CREATE TABLE driver_shifts (
  shift_id   INTEGER PRIMARY KEY,
  driver_id  INTEGER NOT NULL,
  route_code TEXT NOT NULL,
  starts_at  TEXT NOT NULL,
  ends_at    TEXT NOT NULL
);

CREATE TABLE dispatch_tasks (
  task_id      INTEGER PRIMARY KEY,
  shipment_id  INTEGER NOT NULL REFERENCES shipments(shipment_id),
  status       TEXT NOT NULL, -- 'queued' | 'claimed' | 'completed'
  claimed_by   TEXT,
  priority     INTEGER NOT NULL,
  created_at   TEXT NOT NULL
);
```

領域丙刻意埋設的邊界資料：

- 尚未寄出任何包裹的簽約商家、沒有任何掃描事件的已建單運單，以及同時有 `exception` 與 `signed` 多筆事件的運單。
- 掃碼槍離線重傳造成的同秒多筆事件與 `shipment_id IS NULL` 的異常回傳紀錄。
- 單一大電商客戶貢獻超過全表三成運單的資料傾斜分片（用來驗證熱點重複與索引選擇率）。
- 同一位司機跨午夜的夜班排程與多調度員同時搶領高優先度 `dispatch_tasks` 的並行情境。

## 題型體例與作答解析設計

每道題目在網站上都由五個固定區塊組成，避免選完對錯就結束：

| 區塊               | 呈現內容                                                                 | 學習作用                                       |
| ------------------ | ------------------------------------------------------------------------ | ---------------------------------------------- |
| 商業需求與資料前提 | 產品經理或維運的一句需求、涉及的表結構、當下資料量級與索引狀態、目標引擎 | 養成寫查詢前先看資料量、索引與引擎的習慣       |
| 選項清單           | 四個 SQL 寫法或設計方案（渲染時隨機洗牌，避免固定位置記憶）              | 聚焦在核心決策點，降低初學者拼字與環境架設摩擦 |
| 結果與反例對照     | 選完後呈現各選項在「正常資料」與「邊界反例資料」上的實際輸出或報錯       | 讓學習者親眼看到「小資料全對、加一筆反例就錯」 |
| 全選項優劣矩陣     | 逐一列出每個選項的優點、缺點、成立前提與失效條件                         | 建立取捨座標，理解為何沒有脫離前提的最佳寫法   |
| 對應教材與回饋入口 | 連回對應的 `SQL.x` 篇章與知識卡，並提供一鍵記錄「不理解的地方」          | 把練習過程轉成驅動教材迭代的證據               |

本題庫分為四種出題視角與三級難度，隨階段與抽題策略輪替：

- **寫法挑選視角（`choose-query`）**：給出需求與前提，從四個 SQL 中選出正確或代價最可控的寫法。
- **反例擊破視角（`pick-counterexample`）**：給出一段看起來合法、小資料跑得對的 SQL，從四筆待插入的邊界資料中選出會讓該查詢靜默算錯的一筆。
- **計畫與事故診斷視角（`diagnose-plan`）**：給出線上查詢與其 `EXPLAIN` 輸出或錯誤現象（翻頁重複、超賣、換引擎錯序），選出根因與最小修法。
- **前提翻轉與權衡視角（`tradeoff-design`）**：與既有標準題同考點但刻意翻轉前提（補上 `NOT NULL` 約束、補上複合索引、切換單寫入者／多連線引擎），檢驗學習者能否依題幹前提推導，擺脫死背口訣。

## 學習階段總覽與教材對照

六個階段對應 30 個核心能力節點（`S1-01` 至 `S6-05`），每個節點至少配置 3 組跨領域變體（基礎題池共 90 題），再加上獨立的跨概念複合陷阱題池（`C01` 起跳）。

| 階段     | 主題定位                                 | 能力節點與基準題                    | 變體池規模       | 對應既有 SQL 教材與知識卡                                     |
| -------- | ---------------------------------------- | ----------------------------------- | ---------------- | ------------------------------------------------------------- |
| 階段一   | 單表查詢與基礎語法（補足站上前置缺口）   | `S1-01`–`S1-05`（基準 `Q01`–`Q05`） | 15 題（3 領域）  | 前置補強；銜接 `SQL.1`、`SQL.2`、`SQL.6`、`SQL.11`            |
| 階段二   | 多表連接與語意模型核心                   | `S2-01`–`S2-06`（基準 `Q06`–`Q11`） | 18 題（3 領域）  | `SQL.1`、`SQL.2`、`SQL.3`、`SQL.4`、`SQL.5`、`SQL.6`、`SQL.7` |
| 階段三   | 存在性判斷、分組、視窗函式與分頁         | `S3-01`–`S3-05`（基準 `Q12`–`Q16`） | 15 題（3 領域）  | `SQL.8`、`SQL.9`、`SQL.10`、`SQL.11`、`SQL.12`、`SQL.13`      |
| 階段四   | 資料寫入、約束、識別字、字串比較與權限   | `S4-01`–`S4-05`（基準 `Q17`–`Q21`） | 15 題（3 領域）  | `SQL.14`、`SQL.15`、`SQL.16`、`SQL.18`、`ddl-dml` 卡          |
| 階段五   | 效能瓶頸、執行計畫、資料分布與宣告一致性 | `S5-01`–`S5-04`（基準 `Q22`–`Q25`） | 12 題（3 領域）  | `SQL.17`、`SQL.21`、`SQL.22`、`sargable` 與 `query-plan` 卡   |
| 階段六   | 跨引擎遷移、高並行寫入與從需求到上線     | `S6-01`–`S6-05`（基準 `Q26`–`Q30`） | 15 題（3 領域）  | `SQL.0`、`SQL.19`、`SQL.20`、`SQL.23`、`backend 1.16`         |
| 綜合挑戰 | 跨概念複合陷阱題（雙陷阱與三陷阱疊加）   | `C01`–`C06`（持續擴充）             | 6 題起（跨領域） | 跨章節綜合，對應盲測鑑別模式                                  |

## 領域甲基準題組（紙頁書店，30 題完整設計）

以下列出各階段所有題目的商業需求、選項設計、正確選擇、各選項優劣分析與對應教材。各題的「推薦選擇」皆建立在題幹給定的前提之上；前提改變時，解析明確指出何時應改選其他選項。

### 階段一：單表查詢與基礎語法（Q01–Q05）

這個階段假設學習者剛接觸 SQL，從「紙頁書店」單張 `books`、`customers`、`orders` 表出發，建立基本語句閱讀與撰寫能力，同時埋下後續語意模型與效能章節的伏筆。

#### Q01：書籍列表 API 要顯示書名與定價——`SELECT` 欄位挑選與 `SELECT *`

- **商業需求**：書店首頁列表只需要顯示 `book_id`、`title` 與 `price`；未來 `books` 表預計加入數千字的 `description` 長文字欄。哪一種查詢最適合寫進正式 API？
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT book_id, title, price FROM books WHERE is_active = 1;`
  - `B`：`SELECT * FROM books WHERE is_active = 1;`
  - `C`：`SELECT book_id, title, price AS sale_price FROM books;`
  - `D`：`SELECT DISTINCT * FROM books WHERE is_active = 1;`
- **推薦選擇**：`A`
- **各選項優劣分析**：
  - `A`（優）：只讀必要欄位，未來表新增長文字欄時傳輸量不暴增，且有機會命中覆蓋索引（covering index）；（缺）：前端多要一個欄位時須同步修改 SQL。
  - `B`（優）：臨時人工排查資料時省打字；（缺）：schema 擴充長欄位後會無聲拉大網路與記憶體負擔，也無法利用覆蓋索引。
  - `C`（優）：示範了合法的輸出欄位別名 `AS`；（缺）：漏掉 `WHERE is_active = 1`，把下架書籍一併暴露到前台。
  - `D`（優）：語法合法；（缺）：主鍵 `book_id` 已保證每列唯一，`DISTINCT` 迫使引擎做多餘去重排序，且對後續維護者釋出錯誤訊號（暗示表內可能有重複列）。
- **對應教材**：[SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)、[backend 1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)

#### Q02：篩選促銷書單——`AND` 與 `OR` 優先順序、`IN` 與 `BETWEEN`

- **商業需求**：找出「狀態為上架（`is_active = 1`），且屬於分類 `2` 或分類 `3`，定價介於 `300` 到 `600` 元（含端點）」的書籍。
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT book_id, title FROM books WHERE is_active = 1 AND category_id = 2 OR category_id = 3 AND price BETWEEN 300 AND 600;`
  - `B`：`SELECT book_id, title FROM books WHERE is_active = 1 AND category_id IN (2, 3) AND price BETWEEN 300 AND 600;`
  - `C`：`SELECT book_id, title FROM books WHERE is_active = 1 AND category_id IN (2, 3) AND price > 300 AND price < 600;`
  - `D`：`SELECT book_id, title FROM books WHERE is_active = 1 AND (category_id = 2 OR category_id = 3) AND price >= 300 AND price <= 600;`
- **推薦選擇**：`B`（與 `D` 語意等價，在多值集合時優先 `B`）
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：`AND` 運算優先於 `OR`，引擎會解析成 `(is_active = 1 AND category_id = 2) OR (category_id = 3 AND price BETWEEN 300 AND 600)`，會漏掉分類 2 的價格限制並混入分類 3 的下架書。
  - `B`（優）：語意精確、`IN (2, 3)` 比多重 `OR` 好讀且易於擴充成多個分類，`BETWEEN` 明確包含端點 300 與 600；（缺）：用於日期時間戳記欄位時，`BETWEEN` 的閉區間容易在午夜邊界出錯，時間區間改用半開區間 `>=` 與 `<` 較安全。
  - `C`（優）：語意清楚；（缺）：排除了剛好 300 元與 600 元的書籍，不符「含端點」需求。
  - `D`（優）：結果與 `B` 完全相同，顯式括號消除了優先順序歧義；（缺）：分類數增加到十個以上時重複寫 `category_id = ...` 可讀性低於 `IN`。
- **對應教材**：前置基礎語法；延伸見[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)

#### Q03：找出尚未填寫居住城市的會員——`NULL` 比較與 `COALESCE`

- **商業需求**：行銷團隊要寄送地區活動通知，先列出所有 `city` 欄位還沒填寫的顧客。
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT customer_id, name FROM customers WHERE city = NULL;`
  - `B`：`SELECT customer_id, name FROM customers WHERE city IS NULL;`
  - `C`：`SELECT customer_id, name FROM customers WHERE city = '';`
  - `D`：`SELECT customer_id, name FROM customers WHERE COALESCE(city, '') = '';`
- **推薦選擇**：`B`（若確認表內只用 `NULL` 表示缺漏）；若表內混雜 `NULL` 與空字串則選 `D`
- **各選項優劣分析**：
  - `A`（優）：引擎不會報語法錯；（缺）：在三值邏輯下 `NULL = NULL` 的結果是 `UNKNOWN`，永遠回傳 0 列。
  - `B`（優）：精確表達「值缺席」，且現代資料庫的索引支援 `IS NULL` 查找；（缺）：若前端曾經送出空字串 `''` 寫進資料庫，`B` 抓不到空字串那幾筆。
  - `C`（優）：精確抓空字串；（缺）：抓不到 `NULL`。
  - `D`（優）：同時抓出 `NULL` 與空字串，在歷史資料未清理時能兜底；（缺）：把欄位包進 `COALESCE(...)` 會讓一般 B-tree 索引失效（non-sargable），且掩蓋了資料模型混用 `NULL` 與空字串的技術債。
- **對應教材**：[NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)、[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)

#### Q04：高價書籍前五名——`ORDER BY`、`LIMIT` 與預設列序

- **商業需求**：從上架書籍中取出定價最高的前 5 本；若同價，按 `book_id` 由小到大排。
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT book_id, title, price FROM books WHERE is_active = 1 ORDER BY price DESC LIMIT 5;`
  - `B`：`SELECT book_id, title, price FROM books WHERE is_active = 1 ORDER BY price DESC, book_id ASC LIMIT 5;`
  - `C`：`SELECT book_id, title, price FROM books WHERE is_active = 1 LIMIT 5 ORDER BY price DESC;`
  - `D`：`SELECT book_id, title, price FROM books WHERE is_active = 1 ORDER BY price, book_id DESC LIMIT 5;`
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：簡潔；（缺）：同價書籍的排列順序未定義，資料庫建索引或做清理後前 5 名名單會漂移。
  - `B`（優）：以主鍵 `book_id` 打破平手，結果具決定性，每次查詢順序一致；（缺）：比 `A` 多一個排序鍵，但成本極低。
  - `C`（優）：無；（缺）：違反子句書寫順序，`LIMIT` 必須寫在 `ORDER BY` 之後，引擎當場報語法錯誤。
  - `D`（優）：語法合法；（缺）：`price` 沒寫 `DESC` 預設為升冪（最便宜在前），`DESC` 只套用在 `book_id` 上，取到的是最便宜的 5 本書。
- **對應教材**：[SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)

#### Q05：統計已付款訂單數與平均客單價——聚合函式、`GROUP BY` 與 `HAVING`

- **商業需求**：計算每位顧客「狀態為 `paid` 或 `shipped`」的訂單數與總消費金額，只保留總消費金額大於 `1000` 元的顧客。
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT customer_id, COUNT(*) AS order_cnt, SUM(total_amount) AS spent FROM orders WHERE status IN ('paid', 'shipped') AND SUM(total_amount) > 1000 GROUP BY customer_id;`
  - `B`：`SELECT customer_id, COUNT(*) AS order_cnt, SUM(total_amount) AS spent FROM orders WHERE status IN ('paid', 'shipped') GROUP BY customer_id HAVING SUM(total_amount) > 1000;`
  - `C`：`SELECT customer_id, COUNT(*) AS order_cnt, SUM(total_amount) AS spent FROM orders GROUP BY customer_id HAVING status IN ('paid', 'shipped') AND SUM(total_amount) > 1000;`
  - `D`：`SELECT customer_id, COUNT(order_id) AS order_cnt, SUM(total_amount) AS spent FROM orders WHERE status IN ('paid', 'shipped') GROUP BY customer_id HAVING COUNT(*) > 0;`
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：`WHERE` 排在 `GROUP BY` 之前，分組尚未發生，寫聚合函式會被引擎當場拒絕。
  - `B`（優）：先用 `WHERE` 縮減進入分組的列數（可用 `status` 索引），再用 `HAVING` 篩選分組後的聚合結果，語意與效能都正確；（缺）：無明顯缺點。
  - `C`（優）：無；（缺）：`status` 是單列欄位而非分組鍵或聚合值，標準 SQL 與 PostgreSQL 會報錯，SQLite 雖放寬但會隨意挑一列的 `status` 判斷導致靜默算錯。
  - `D`（優）：語法合法；（缺）：`HAVING COUNT(*) > 0` 沒篩選總金額大於 1000，答非所問。
- **對應教材**：[SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)、[SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)

---

### 階段二：多表連接與語意模型核心（Q06–Q11）

這個階段讓學習者跨過「會寫單表」到「讀懂多表語意模型」的門檻，題目設計直接對應 `SQL.2` 至 `SQL.7`。

#### Q06：別名在 `WHERE` 與 `ORDER BY` 的可用範圍——求值順序與引擎寬鬆

- **商業需求**：計算每筆訂單明細的小計 `quantity * unit_price AS line_total`，只留小計超過 `1000` 元的列並由大到小排。寫法要同時在 SQLite、PostgreSQL 與 MySQL 上通過。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT order_item_id, quantity * unit_price AS line_total FROM order_items WHERE line_total > 1000 ORDER BY line_total DESC;`
  - `B`：`SELECT order_item_id, quantity * unit_price AS line_total FROM order_items WHERE quantity * unit_price > 1000 ORDER BY line_total DESC;`
  - `C`：`SELECT order_item_id, quantity * unit_price AS line_total FROM order_items GROUP BY order_item_id HAVING line_total > 1000 ORDER BY line_total DESC;`
  - `D`：`SELECT * FROM (SELECT order_item_id, quantity * unit_price AS line_total FROM order_items) t WHERE t.line_total > 1000 ORDER BY t.line_total DESC;`
- **推薦選擇**：`B`（表達式簡單時）；表達式複雜且避免重複撰寫時選 `D`
- **各選項優劣分析**：
  - `A`（優）：少寫一次乘法；（缺）：求值順序裡 `WHERE` 早於 `SELECT`，PostgreSQL 與 MySQL 當場報欄名不存在（DuckDB 放寬）。
  - `B`（優）：符合標準求值順序，三家引擎全部通過，`ORDER BY` 排在 `SELECT` 之後因此可直接用別名 `line_total`；（缺）：公式重複出現兩次，公式很長時修改 `SELECT` 算式容易漏改 `WHERE` 裡同一段算式。
  - `C`（優）：無；（缺）：為了用別名而硬塞無意義的 `GROUP BY`，PostgreSQL 的 `HAVING` 依然不收 `SELECT` 別名，且增加分組負擔。
  - `D`（優）：公式只寫一次，跨引擎 100% 可攜，現代最佳化器會將簡單子查詢合併（subquery flattening）不增代價；（缺）：查詢多一層巢狀，簡短算式寫起來略顯冗長。
- **對應教材**：[SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)、[SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)

#### Q07：統計所有會員的下單次數——`INNER JOIN`、`LEFT JOIN` 與 `COUNT(*)` 陷阱

- **商業需求**：列出「全部註冊顧客」（含從未下單的顧客）的 `customer_id`、`name` 與訂單張數，未下單者顯示 `0`。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_cnt FROM customers c INNER JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.name;`
  - `B`：`SELECT c.customer_id, c.name, COUNT(*) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.name;`
  - `C`：`SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.name;`
  - `D`：`SELECT c.customer_id, c.name, (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS order_cnt FROM customers c;`
- **推薦選擇**：`C`（多數查詢優先）；若只要查少數顧客（例如已加 `WHERE c.city = 'Taipei' LIMIT 20`）且 `orders(customer_id)` 有索引時可選 `D`
- **各選項優劣分析**：
  - `A`（優）：語法正確；（缺）：`INNER JOIN` 直接丟掉沒下單的顧客 `雅文`，名單不完整。
  - `B`（優）：保留了未下單顧客；（缺）：外連接會為未下單顧客補出一列 `orders` 全為 `NULL` 的列，`COUNT(*)` 把補出來的列算成 1 張訂單，未下單顧客變成顯示 `1` 而非 `0`。
  - `C`（優）：`LEFT JOIN` 保留所有顧客，`COUNT(o.order_id)` 略過 `NULL`，未下單顧客正確得到 `0`，且可走一次 hash/merge join 掃描；（缺）：若還要再接另一張一對多表（例如 `reviews`），直接加 `JOIN` 會引發列數膨脹。
  - `D`（優）：沒有連接膨脹風險、語意直覺；（缺）：對全表顧客掃描時會變逐列相關子查詢，若缺 `orders(customer_id)` 索引，效能會急劇惡化。
- **對應教材**：[SQL.3 連接的起手式：配對條件的位置與連接種類的選擇](/backend/01-database/sql/join-starts-from-the-relationship/)、[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)

#### Q08：所有顧客與他們 2026 年 3 月的訂單——`ON` 與 `WHERE` 的職責分岔

- **商業需求**：報表要列出「每一位顧客」，旁邊顯示他在 2026 年 3 月的已付款訂單總額；3 月沒有付款訂單的顧客仍要列在報表上（顯示 `0`）。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT c.customer_id, COALESCE(SUM(o.total_amount), 0) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01' GROUP BY c.customer_id;`
  - `B`：`SELECT c.customer_id, COALESCE(SUM(o.total_amount), 0) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01' GROUP BY c.customer_id;`
  - `C`：`SELECT c.customer_id, COALESCE(SUM(o.total_amount), 0) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE (o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01') OR o.order_id IS NULL GROUP BY c.customer_id;`
  - `D`：`SELECT c.customer_id, COALESCE(SUM(CASE WHEN o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01' THEN o.total_amount END), 0) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;`
- **推薦選擇**：`B`（若同一查詢只算 3 月一個指標）；若同一報表要同時算出 2 月與 3 月兩欄總額則選 `D`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：`WHERE` 在外連接之後執行，對未配到 3 月訂單的顧客，`o.status` 為 `NULL`，`NULL = 'paid'` 判成未知，把外連接保護的顧客全濾掉，實質退化成 `INNER JOIN`。
  - `B`（優）：把「哪些訂單有資格配對」寫進 `ON`，沒配到 3 月已付款訂單的顧客仍保留並補 `NULL`，再由 `COALESCE` 轉成 `0`，語意精確且可先過濾 `orders`；（缺）：只適合單一條件切片。
  - `C`（優）：保留了從未下過任何訂單的顧客；（缺）：對「2 月有下單、3 月沒下單」的顧客，`o.order_id IS NULL` 為假且 2 月訂單不符 3 月條件，這位顧客仍然消失。這是最隱蔽的錯法。
  - `D`（優）：結果正確，且同一張表掃一次就能用多個 `CASE WHEN` 同時算不同月份或狀態的總額；（缺）：會先把該顧客歷年全部訂單都連接進來再條件加總，若 `orders` 累積數年資料且只需要單月，掃描量遠大於 `B`。
- **對應教材**：[SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)

#### Q09：三表鏈式連接的保護範圍——`customers → orders → reviews`

- **商業需求**：列出所有顧客、他們的訂單編號與評價星等；沒有訂單的顧客要保留，有訂單但沒有評價的訂單也要保留。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT c.name, o.order_id, r.rating FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id INNER JOIN reviews r ON r.order_id = o.order_id;`
  - `B`：`SELECT c.name, o.order_id, r.rating FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id LEFT JOIN reviews r ON r.order_id = o.order_id;`
  - `C`：`SELECT c.name, o.order_id, r.rating FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id RIGHT JOIN reviews r ON r.order_id = o.order_id;`
  - `D`：`SELECT c.name, o.order_id, r.rating FROM customers c LEFT JOIN (orders o INNER JOIN reviews r ON r.order_id = o.order_id) ON o.customer_id = c.customer_id;`
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：第二個 `INNER JOIN` 的左運算元是「`customers LEFT JOIN orders` 的累積結果」，它把沒有評價的訂單以及沒有訂單的顧客全部濾掉。
  - `B`（優）：整條鏈都用 `LEFT JOIN`，每一步都保護左邊累積出來的結果集，滿足兩層保留需求且閱讀方向一致；（缺）：若每筆訂單有多則評價，訂單列會依評價數複製。
  - `C`（優）：無；（缺）：鏈中間的 `RIGHT JOIN` 改為保護右表 `reviews`，把沒評價的顧客與訂單全部丟棄。
  - `D`（優）：語法合法，示範括號改變連接結合順序；（缺）：括號內是 `orders INNER JOIN reviews`，所以「有訂單但沒評價」的訂單不會出現（顧客雖保留，但訂單編號變成 `NULL`），不符合保留無評價訂單的需求。
- **對應教材**：[SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)

#### Q10：同時算總消費金額與評價數——一對多連接造成的列數膨脹

- **商業需求**：算出每位顧客的「訂單總消費金額」與「送出的評價總則數」。已知同一筆訂單可能有多則評價（一筆訂單買多本書各自評價）。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT c.customer_id, SUM(o.total_amount) AS spent, COUNT(r.review_id) AS review_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id LEFT JOIN reviews r ON r.order_id = o.order_id GROUP BY c.customer_id;`
  - `B`：`SELECT c.customer_id, SUM(DISTINCT o.total_amount) AS spent, COUNT(DISTINCT r.review_id) AS review_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id LEFT JOIN reviews r ON r.order_id = o.order_id GROUP BY c.customer_id;`
  - `C`：`WITH order_agg AS (SELECT customer_id, SUM(total_amount) AS spent FROM orders GROUP BY customer_id), review_agg AS (SELECT o.customer_id, COUNT(r.review_id) AS review_cnt FROM orders o JOIN reviews r ON r.order_id = o.order_id GROUP BY o.customer_id) SELECT c.customer_id, COALESCE(oa.spent, 0) AS spent, COALESCE(ra.review_cnt, 0) AS review_cnt FROM customers c LEFT JOIN order_agg oa ON oa.customer_id = c.customer_id LEFT JOIN review_agg ra ON ra.customer_id = c.customer_id;`
  - `D`：`SELECT c.customer_id, (SELECT COALESCE(SUM(o.total_amount), 0) FROM orders o WHERE o.customer_id = c.customer_id) AS spent, (SELECT COUNT(r.review_id) FROM orders o JOIN reviews r ON r.order_id = o.order_id WHERE o.customer_id = c.customer_id) AS review_cnt FROM customers c;`
- **推薦選擇**：`C`（全表彙總報表）；只查單一顧客（`WHERE c.customer_id = ?`）時可選 `D`
- **各選項優劣分析**：
  - `A`（優）：寫法短；（缺）：訂單 101 有 2 則評價時，該筆訂單在連接後變成 2 列，`SUM(o.total_amount)` 把同一張訂單金額重複加兩次，結果靜默算錯。
  - `B`（優）：表面上消除了重複評價造成的膨脹；（缺）：只要同一位顧客有兩張不同訂單剛好都是 `300` 元，`SUM(DISTINCT o.total_amount)` 會把兩張真實訂單合併只算一次，造成另一種靜默少算。
  - `C`（優）：先把 `orders` 與 `reviews` 各自聚合到「每位顧客一列」的相同粒度再連接，徹底根除列數膨脹，全表報表效能平穩；（缺）：SQL 較長，需要理解 CTE 或衍生表。
  - `D`（優）：沒有膨脹風險，查單一顧客搭配索引時極快；（缺）：對十萬顧客跑全表報表時相關子查詢開銷遠高於 `C`。
- **對應教材**：[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)、[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)

#### Q11：顯示子分類與所屬父分類名稱——表的出現與自連接

- **商業需求**：後台分類管理頁要列出每個分類的名稱，以及它的上層父分類名稱；頂層分類（`parent_id IS NULL`）也要顯示，父分類名稱欄位顯示 `NULL`。
- **題型**：語法判讀題
- **選項**：
  - `A`：`SELECT categories.name, categories.name FROM categories LEFT JOIN categories ON categories.parent_id = categories.category_id;`
  - `B`：`SELECT child.name AS category_name, parent.name AS parent_name FROM categories child INNER JOIN categories parent ON child.parent_id = parent.category_id;`
  - `C`：`SELECT child.name AS category_name, parent.name AS parent_name FROM categories child LEFT JOIN categories parent ON child.parent_id = parent.category_id;`
  - `D`：`SELECT c1.name AS category_name, c2.name AS parent_name FROM categories c1 LEFT JOIN categories c2 ON c1.category_id = c2.parent_id;`
- **推薦選擇**：`C`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：同一張表在 `FROM` 出現兩次未取別名，引擎無法區分兩個出現位置，當場報錯。
  - `B`（優）：別名以角色命名（`child` / `parent`）清晰易讀；（缺）：用 `INNER JOIN` 濾掉了所有頂層分類（`parent_id IS NULL`）。
  - `C`（優）：以角色命名別名，`LEFT JOIN` 保留頂層分類並讓 `parent_name` 自然呈現 `NULL`；（缺）：只能展開一層父子關係；若需要展開任意深度分類樹，須改用遞迴 CTE（`WITH RECURSIVE`）。
  - `D`（優）：語法合法；（缺）：連接方向寫反，變成「每個分類配它底下的子分類」，不只角色顛倒，有三個子分類的父分類還會被複製成三列；用 `c1` / `c2` 這類無意義編號也讓寫反更難被肉眼發現。
- **對應教材**：[SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)

---

### 階段三：存在性判斷、分組、視窗函式與分頁（Q12–Q16）

這個階段進入日常後端最常寫錯的四類查詢：存在性與否定存在性、分組粒度、明細加組彙總（視窗函式）以及生產環境分頁。

#### Q12：找出曾購買「資料庫」分類書籍的顧客名單——`IN`、`EXISTS` 與 `JOIN`

- **商業需求**：行銷名單需要「買過分類編號 `5`（資料庫）書籍的顧客 `customer_id` 與 `name`」，不需要顯示買了哪幾本書，且每位顧客只出現一次。
- **題型**：情境權衡題
- **選項**：
  - `A`：`SELECT c.customer_id, c.name FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id JOIN books b ON b.book_id = oi.book_id WHERE b.category_id = 5;`
  - `B`：`SELECT DISTINCT c.customer_id, c.name FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id JOIN books b ON b.book_id = oi.book_id WHERE b.category_id = 5;`
  - `C`：`SELECT c.customer_id, c.name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN books b ON b.book_id = oi.book_id WHERE o.customer_id = c.customer_id AND b.category_id = 5);`
  - `D`：`SELECT c.customer_id, c.name FROM customers c WHERE c.customer_id IN (SELECT o.customer_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN books b ON b.book_id = oi.book_id WHERE b.category_id = 5);`
- **推薦選擇**：`C`（或 `D`，兩者皆不產生列膨脹，多數情境下 `C` 的存在性宣告最清晰，且容易延伸到否定式）
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：買過三本資料庫書籍的顧客會重複出現三次，違反名單唯一需求。
  - `B`（優）：結果正確；（缺）：先展開所有訂單明細再靠 `DISTINCT` 收掉重複，浪費中間列運算，且對讀程式的人來說看不出 `DISTINCT` 是為了解決多表膨脹還是原表有重複。
  - `C`（優）：語意直接表達「存在性判斷」（semi-join），結果列數上限鎖死在 `customers` 列數，找到第一筆符合的明細即可短路停止，改寫成「沒買過」只需加 `NOT`；（缺）：不能在最外層 `SELECT` 取出 `books` 的欄位（若未來需求改成要同時顯示書名，必須改回 `JOIN`）。
  - `D`（優）：同樣不膨脹列數，語意簡明，且若子查詢命中顧客很少時最佳化器容易先算子查詢集合；（缺）：一旦需求反轉成 `NOT IN`，遇到 `NULL` 就會整段失效。
- **對應教材**：[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)、[Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/)

#### Q13：找出「沒有五星評價」的訂單——否定存在性的三種靜默陷阱

- **商業需求**：客服團隊要追蹤所有「沒有收到任何五星評價」的訂單（包含完全沒評價的訂單，以及只有 1–4 星評價的訂單）。已知 `reviews.order_id` 允許 `NULL` 且一張訂單可有多則評價。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT o.order_id FROM orders o LEFT JOIN reviews r ON r.order_id = o.order_id WHERE r.rating <> 5;`
  - `B`：`SELECT o.order_id FROM orders o WHERE o.order_id NOT IN (SELECT r.order_id FROM reviews r WHERE r.rating = 5);`
  - `C`：`SELECT o.order_id FROM orders o LEFT JOIN reviews r ON r.order_id = o.order_id WHERE r.review_id IS NULL;`
  - `D`：`SELECT o.order_id FROM orders o WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.order_id AND r.rating = 5);`
- **推薦選擇**：`D`（另與 `LEFT JOIN ... ON ... AND r.rating = 5 WHERE r.review_id IS NULL` 等價，但 `NOT EXISTS` 對「一對多不膨脹」更安全）
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：問錯問題（變成「至少有一則非五星評價」），同時 `WHERE r.rating <> 5` 濾掉沒評價的訂單，若某訂單同時有一則五星與一則三星，它還會錯誤把該訂單列出來。
  - `B`（優）：在沒有 `NULL` 的測試資料上輸出正確；（缺）：`reviews` 只要出現一筆 `order_id IS NULL` 且 `rating = 5` 的列，`NOT IN` 展開成 `<> NULL` 判未知，整個查詢靜默回傳 0 列。
  - `C`（優）：在「有評價就全是五星」的小資料上剛好回對；（缺）：實際篩選條件是「沒有任何評價的訂單」，一旦訂單出現一則三星評價，`C` 會把它漏掉。
  - `D`（優）：對 `NULL` 免疫，同一訂單同時有五星與三星時正確排除，沒有評價的訂單正確保留，且不產生重複列；（缺）：需要在 `reviews(order_id, rating)` 或 `reviews(order_id)` 上建索引以維持大表速度。
- **對應教材**：[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)、[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)

#### Q14：依顧客統計訂單數——分組鍵選擇與非分組欄位

- **商業需求**：統計每位註冊顧客（含未下單者）的訂單數量，輸出 `customer_id`、`name` 與 `order_cnt`。查詢須在 PostgreSQL 與開啟 `ONLY_FULL_GROUP_BY` 的 MySQL 上正常執行。
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY o.customer_id;`
  - `B`：`SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;`
  - `C`：`SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id, c.name;`
  - `D`：`SELECT c.name, COUNT(o.order_id) AS order_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.name;`
- **推薦選擇**：`C`（跨引擎最穩；在確認 `customer_id` 是主鍵的 PostgreSQL／MySQL 8 上 `B` 因函數相依也合法）
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：拿右表 `o.customer_id` 當分組鍵，所有沒下單的顧客 `o.customer_id` 都是 `NULL`，會全部被併成同一組，在 SQLite 上不報錯卻把多名未下單顧客合併成一列。
  - `B`（優）：PostgreSQL 與 MySQL 8 辨識出 `c.customer_id` 是主鍵、`c.name` 函數相依於主鍵，因此放行；（缺）：DuckDB 與部分資料庫（或當來源是子查詢／檢視表失去主鍵資訊時）會拒絕未列進 `GROUP BY` 的 `c.name`。
  - `C`（優）：分組鍵落在受保護的左表主鍵，並顯式列出 `c.name`，所有引擎一致通過且語意明確；（缺）：輸出欄位增加時須同步補進 `GROUP BY`。
  - `D`（優）：無；（缺）：拿非唯一的 `c.name` 分組，兩位同名顧客的訂單會被默默加在一起。
- **對應教材**：[SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)

#### Q15：每筆訂單旁邊顯示顧客總消費比例，以及比較「前一天」營收——`GROUP BY` 與視窗函式

- **商業需求**：這道題拆成兩個日常分析需求，先鎖定第二個需求：從 `daily_sales_snapshots` 找出「哪幾天的日營收比前一個日曆天高」（表內有多個 `store_code`，且門市公休日沒有資料列）。哪一個寫法正確？
- **題型**：靜默錯法與反例題
- **選項**：
  - `A`：`SELECT snapshot_date, store_code, revenue FROM (SELECT *, LAG(revenue) OVER (ORDER BY snapshot_date) AS prev_rev FROM daily_sales_snapshots) t WHERE revenue > prev_rev;`
  - `B`：`SELECT snapshot_date, store_code, revenue FROM (SELECT *, LAG(revenue) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_rev FROM daily_sales_snapshots) t WHERE revenue > prev_rev;`
  - `C`：`SELECT snapshot_date, store_code, revenue FROM (SELECT *, LAG(revenue) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_rev, LAG(snapshot_date) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_date FROM daily_sales_snapshots) t WHERE prev_date = date(snapshot_date, '-1 day') AND revenue > prev_rev;`
  - `D`：`SELECT store_code, MAX(revenue) FROM daily_sales_snapshots GROUP BY store_code HAVING MAX(revenue) > MIN(revenue);`
- **推薦選擇**：`C`（若「前一天」經確認是指日曆上的前一天）；若需求定義為「該門市上一個營業日」則選 `B`
- **各選項優劣分析**：
  - `A`（優）：語法簡短；（缺）：漏掉 `PARTITION BY store_code`，會把台北店今天拿去跟台中店同一天或前一天比較，且沒檢查日期相隔天數。
  - `B`（優）：補了 `PARTITION BY store_code`，計算「上一個有資料的營業日」時最簡潔且只需一次排序掃描；（缺）：遇到週一公休（週二上一列是週日）時，把週二拿去跟週日比，不符合「日曆前一天」定義。
  - `C`（優）：同一次視窗排序同時取出前一列營收與前一列日期，驗證兩列確實只差 1 天才比較，兼顧正確性與單次掃描效能（O(N log N)）；（缺）：日期加減函式因引擎而異（SQLite 用 `date(..., '-1 day')`，PostgreSQL 用 `snapshot_date - INTERVAL '1 day'`），換引擎時須調整日期運算語法。
  - `D`（優）：無；（缺）：`GROUP BY` 把每家門市收成一列，失去了「每一天」的明細粒度。
- **對應教材**：[SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/)、[SQL.23 查詢設計的完整示範：把「哪幾天氣溫比前一天高」從需求做到上線](/backend/01-database/sql/requirement-to-shipped-query/)

#### Q16：百萬筆訂單後台分頁列表——`OFFSET` 與 Keyset（接續標記）分頁

- **商業需求**：後台訂單管理頁要支援「依 `ordered_at DESC` 瀏覽歷史訂單，每頁 20 筆」，資料表已有 200 萬筆訂單，且前台每秒持續有新訂單寫入。客服反映翻頁時偶爾會看到同一筆訂單重複出現，翻到第 500 頁時畫面卡頓超過 2 秒。哪個方案最適合「無限捲動／下一頁」介面？
- **題型**：情境權衡題
- **選項**：
  - `A`：`SELECT * FROM orders ORDER BY ordered_at DESC LIMIT 20 OFFSET 10000;`
  - `B`：`SELECT * FROM orders ORDER BY ordered_at DESC, order_id DESC LIMIT 20 OFFSET 10000;`
  - `C`：`SELECT order_id, customer_id, status, total_amount, ordered_at FROM orders WHERE (ordered_at, order_id) < (:last_ordered_at, :last_order_id) ORDER BY ordered_at DESC, order_id DESC LIMIT 20;`（搭配複合索引 `(ordered_at DESC, order_id DESC)`）
  - `D`：`SELECT order_id, customer_id, status, total_amount, ordered_at FROM orders WHERE ordered_at < :last_ordered_at ORDER BY ordered_at DESC LIMIT 20;`
- **推薦選擇**：`C`（若介面只需要上一頁／下一頁或無限捲動）；若業務硬性要求任意跳轉「第 37 頁」且資料量可控，才在補全序前提下評估 `B`
- **各選項優劣分析**：
  - `A`（優）：實作最簡單；（缺）：同時存在兩個缺陷——排序鍵不唯一（同秒訂單順序不穩）且新訂單寫入會推移位移造成重複／遺漏；`OFFSET 10000` 必須先掃出並丟棄前 10,000 列，越翻越慢。
  - `B`（優）：補上主鍵形成全序，解決同秒同分列漂移，且仍支援直接跳到第 N 頁；（缺）：新訂單插入頂部時翻頁仍會重複看到前一頁末尾的列，且深頁 `OFFSET` 效能隨頁數線性惡化。
  - `C`（優）：以 `(ordered_at, order_id)` 全序值作為接續標記，翻到第 10,000 頁也能透過複合索引直接定位、維持常數級查詢時間，且新訂單插入頂部不會影響已翻過的邊界；（缺）：無法直接跳轉至任意指定頁碼（例如「跳到第 50 頁」），且若兩欄排序方向一升一降時不可直接用列值比較 `(a, b) < (x, y)`，須改寫成展開式條件。
  - `D`（優）：效能與 `C` 接近；（缺）：若同一個 `ordered_at` 時間戳記下有多筆訂單跨頁，用嚴格 `<` 會直接遺漏同秒的其餘訂單。
- **對應教材**：[SQL.12 分頁的排序鍵與接續標記：同分的列、全序與 OFFSET 的代價](/backend/01-database/sql/pagination-needs-a-total-order/)

---

### 階段四：資料寫入、約束、識別字、字串比較與權限（Q17–Q21）

這個階段補上 DML 寫入基礎，並切入「文字之外的決定者」：約束、識別字規則、collation 與權限模型。

#### Q17：批次將過期未付款訂單改為取消——DML 寫入邊界與交易安全

- **商業需求**：排程要把「超過 24 小時仍為 `pending`」的訂單改為 `cancelled`，同時把被取消訂單的 `order_id` 回傳給應用程式以便歸還庫存。哪一個設計最安全？
- **題型**：語法判讀題 + 情境權衡題
- **選項**：
  - `A`：`UPDATE orders SET status = 'cancelled' WHERE ordered_at < :cutoff;`
  - `B`：`UPDATE orders SET status = 'cancelled' WHERE status = 'pending' AND ordered_at < :cutoff RETURNING order_id;`（包在與歸還庫存相同的交易內）
  - `C`：`DELETE FROM orders WHERE status = 'pending' AND ordered_at < :cutoff;`
  - `D`：先執行 `SELECT order_id FROM orders WHERE status = 'pending' AND ordered_at < :cutoff;`，應用程式拿到清單後再逐筆 `UPDATE orders SET status = 'cancelled' WHERE order_id = ?;`
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：漏掉 `status = 'pending'`，把 24 小時以前所有已付款、已出貨的歷史訂單全部改成取消，屬於災難性寫入錯誤。
  - `B`（優）：條件鎖定 `status = 'pending'` 與時間邊界，單一原子語句完成狀態轉換並透過 `RETURNING` 精確取得「這一次真正被改到」的訂單清單（SQLite 3.35+ 與 PostgreSQL 皆支援），包在同一交易內確保取消與還庫存同成同敗；（缺）：一次鎖定過多列（例如數十萬筆積壓）可能長時間佔鎖，大批量時須搭配分批限制筆數。
  - `C`（優）：減少表大小；（缺）：直接刪除會破壞 `order_items`／`reviews` 參照關係與財務稽核軌跡。
  - `D`（優）：相容不支援 `RETURNING` 的舊引擎；（缺）：在 `SELECT` 與 `UPDATE` 之間若顧客剛好完成付款，`UPDATE` 未檢查 `status = 'pending'` 會把剛付款的訂單覆蓋成取消。
- **對應教材**：[DDL 與 DML](/backend/01-database/sql/knowledge-cards/ddl-dml/)、[backend 1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)

#### Q18：書籍下架與顧客註銷帳號——外鍵 `ON DELETE` 策略與 SQLite 生效檢查

- **商業需求**：書籍下架或顧客刪除帳號時，歷史訂單明細必須保留金額與書名供會計對帳，同時要防止寫入指向不存在 `book_id` 的訂單明細。團隊目前開發環境用 SQLite、正式環境用 PostgreSQL。哪一個做法正確？
- **題型**：情境權衡題
- **選項**：
  - `A`：建表宣告 `FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE`，讓刪書時自動清掉關聯明細。
  - `B`：建表宣告 `FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT`，下架改用 `is_active = 0`（軟下架）不刪 `books` 列；並在 SQLite 每一條新建連線上執行 `PRAGMA foreign_keys = ON`。
  - `C`：只在 `CREATE TABLE` 寫好 `REFERENCES books(book_id)` 即可，SQLite 與 PostgreSQL 都會自動擋下孤兒列。
  - `D`：不建外鍵約束，改在應用程式的 `INSERT` 之前自己跑 `SELECT 1 FROM books WHERE book_id = ?` 驗證。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：不會殘留孤兒列；（缺）：刪除一本書會把歷史所有包含這本書的 `order_items` 連帶刪光，財務對帳金額立刻失真。
  - `B`（優）：`RESTRICT` 防止誤刪有歷史訂單的書、軟下架保留關聯完整性，並處理了 SQLite 預設每條連線關閉外鍵執法的差異；（缺）：需要規範應用程式連線池初始化流程，確保每條 SQLite 連線都開啟 `PRAGMA foreign_keys = ON`。
  - `C`（優）：宣告本身合法；（缺）：SQLite 預設不執行外鍵檢查，宣告存在但沒有生效，開發測試期間壞資料會悄悄通過，上到 PostgreSQL 才報錯。
  - `D`（優）：在分庫分表無法建跨庫外鍵時是必要替代方案；（缺）：單庫環境下，兩個並行請求（一邊刪書、一邊下單）或人工腳本直接寫入都能繞過應用層檢查，無法提供資料表級別的保證。
- **對應教材**：[SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)

#### Q19：跨引擎維護資料表與欄名——識別字大小寫摺疊與引號策略

- **商業需求**：團隊設計新表「訂單明細」時，有人提議用駝峰命名 `"orderItems"` 與 `"unitPrice"`，也有人主張全部用小寫加底線 `order_items` 與 `unit_price` 且不加引號。專案會同時跑在 SQLite 與 PostgreSQL。該選哪一種？
- **題型**：情境權衡題
- **選項**：
  - `A`：建表寫 `CREATE TABLE "orderItems" ("unitPrice" INT)`，查詢時為了方便不加引號寫 `SELECT unitPrice FROM orderItems`。
  - `B`：建表與查詢一律使用全小寫加底線且避開保留字（`order_items`、`unit_price`），不加引號。
  - `C`：一律用反引號包住表名與欄名（`` `order_items` ``），讓各家引擎都認得。
  - `D`：建表用 `CREATE TABLE Order (order INT)`，遇到衝突時再個別加引號。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：PostgreSQL 會把未加引號的 `orderItems` 摺疊成小寫 `orderitems`，與建表時加引號鎖住的大寫 `"orderItems"` 對不上而報表不存在；SQLite 大小寫不敏感所以本機全過、上線全壞。
  - `B`（優）：全小寫、無保留字、不加引號，在 SQLite、PostgreSQL、MySQL、DuckDB 四家行為完全一致，省去跨引擎引號符號差異與摺疊陷阱；（缺）：若外部系統匯出表已經含大小寫或保留字，才需要對該外部表顯式加雙引號。
  - `C`（優）：MySQL 與 SQLite 可接受反引號；（缺）：PostgreSQL 不認反引號當識別字引號（標準 SQL 用雙引號 `"`），當場報語法錯誤。
  - `D`（優）：無；（缺）：`order` 是 SQL 保留字，每次查詢都得加引號且極易在 ORM、手寫腳本或遷移工具中漏掉。
- **對應教材**：[SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)

#### Q20：會員登入不分大小寫比對 Email——Collation、函式與索引可用性

- **商業需求**：書店改用 PostgreSQL 後，原本在 MySQL 可以用 `alice@example.com` 登入 `Alice@Example.com` 帳號的會員突然登入失敗。資料庫已有 50 萬會員，要求不分大小寫比對且查詢必須走索引。哪一種方案最合適？
- **題型**：情境權衡題
- **選項**：
  - `A`：把登入查詢改成 `SELECT * FROM customers WHERE LOWER(email) = LOWER(:input);`，不改索引。
  - `B`：建立運算式索引 `CREATE INDEX idx_customers_lower_email ON customers (LOWER(email));`，查詢使用 `WHERE LOWER(email) = LOWER(:input)`（或寫入時統一正規化存成小寫，並加 `CHECK (email = LOWER(email))` 與 `UNIQUE (email)`）。
  - `C`：維持 `WHERE email = :input`，改用 `LIKE` 因為 `LIKE` 一律不分大小寫。
  - `D`：直接把整個資料庫的預設 collation 改成不分大小寫，不另外評估其他欄位。
- **推薦選擇**：`B`（新建系統優先「寫入前正規化＋`CHECK` 約束＋`UNIQUE` 索引」；舊資料必須保留使用者原始大小寫顯示時選運算式唯一索引 `UNIQUE INDEX ON (LOWER(email))`）
- **各選項優劣分析**：
  - `A`（優）：改動最小、立刻解決大小寫問題；（缺）：`LOWER(email)` 把欄位包進函式，原本建在 `email` 上的索引失效，50 萬列每次登入都掃全表。
  - `B`（優）：查詢走索引（O(log N)），且若建成 `UNIQUE INDEX ON (LOWER(email))` 連「同信箱不同大小寫重複註冊」都由資料庫擋下；（缺）：使用運算式索引時，查詢寫法必須與索引定義的函式形狀完全一致才會命中。
  - `C`（優）：無；（缺）：PostgreSQL 的 `LIKE` 區分大小寫（不分大小寫是 `ILIKE`），且 SQLite 的 `LIKE` 僅對 ASCII 字母不分大小寫，跨引擎行為不穩，也容易把 `_` 與 `%` 當成萬用字元造成安全漏洞。
  - `D`（優）：不用改既有查詢；（缺）：影響範圍擴及所有表與索引（包含需要區分大小寫的 token、代碼或排序規則），副作用過大。
- **對應教材**：[SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)、[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/)

#### Q21：切分正式環境資料庫帳號權限——角色與最小權限

- **商業需求**：書店系統上線 PostgreSQL，同時有「Web API 應用」「每日跑報表的 BI 分析師」「部署時跑 Schema Migration 的工具」三個存取方。該如何規劃資料庫角色與 `GRANT`？
- **題型**：情境權衡題
- **選項**：
  - `A`：三者共用資料庫擁有者（owner）帳號，省去維護多組連線密碼與權限設定。
  - `B`：將三個角色分離：`app_role` 只拿所需資料表的 `SELECT / INSERT / UPDATE / DELETE`（不給 `CREATE / DROP / ALTER`）；`bi_readonly` 只拿報表相關表或遮罩檢視表的 `SELECT`；`migrator` 擁有 schema 變更權限且僅在部署管線使用。
  - `C`：建立新角色後只授權 `GRANT SELECT ON DATABASE bookstore TO bi_readonly;`，不個別授表權限。
  - `D`：給 `app_role` 全部權限，但要求開發人員在 code review 時不可寫 `DROP TABLE`。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：初期設定最快；（缺）：一旦 Web API 出現 SQL injection 或誤操作，攻擊者可直接 `DROP TABLE` 或修改 schema；BI 查詢錯誤也可能寫壞正式資料。
  - `B`（優）：事故與入侵半徑被資料庫強制切開，且能搭配檢視表遮蔽 `customers.email` 等個資欄位；（缺）：部署流程須管理多組憑證，新增資料表時須記得透過 `ALTER DEFAULT PRIVILEGES` 或 migration 補授權。
  - `C`（優）：無；（缺）：PostgreSQL 的 `SELECT` 權限單位落在資料表而非資料庫層級，該語句語法無效；新角色預設沒有任何表的讀取權限。
  - `D`（優）：無；（缺）：人工紀律擋不住漏洞利用、第三方套件錯誤或自動化腳本失誤。
- **對應教材**：[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)

---

### 階段五：效能瓶頸、執行計畫、資料分布與宣告一致性（Q22–Q25）

這個階段把焦點移到「同樣都回傳正確答案，為什麼在正式環境差了三個量級」，建立讀執行計畫（`EXPLAIN`）與檢驗宣告一致性的能力。

#### Q22：撈取單月訂單變慢——Sargable 條件形狀與索引失效

- **商業需求**：`orders` 表有 500 萬列並在 `ordered_at` 建有 B-tree 索引，格式為 ISO-8601 字串 `'2026-03-15 10:20:00'`。月報要撈 2026 年 3 月的全部訂單，哪個寫法能走索引且沒有月底邊界漏洞？
- **題型**：情境權衡題
- **選項**：
  - `A`：`SELECT order_id, total_amount FROM orders WHERE substr(ordered_at, 1, 7) = '2026-03';`
  - `B`：`SELECT order_id, total_amount FROM orders WHERE ordered_at BETWEEN '2026-03-01' AND '2026-03-31';`
  - `C`：`SELECT order_id, total_amount FROM orders WHERE ordered_at >= '2026-03-01 00:00:00' AND ordered_at < '2026-04-01 00:00:00';`
  - `D`：`SELECT order_id, total_amount FROM orders WHERE ordered_at LIKE '%2026-03%';`
- **推薦選擇**：`C`
- **各選項優劣分析**：
  - `A`（優）：文字短、一眼看懂要查哪個月；（缺）：欄位被包進 `substr(...)`，屬於 non-sargable 條件，普通 B-tree 索引失效而觸發 500 萬列全表掃描（除非另外針對該表達式建運算式索引）。
  - `B`（優）：能走索引；（缺）：`'2026-03-31 08:00:00'` 在字串比較下大於 `'2026-03-31'`，會把 3 月 31 日整天的訂單全部漏掉。
  - `C`（優）：欄位維持裸欄比較，完整命中 `ordered_at` 範圍索引掃描（index range scan），半開區間 `[3/1, 4/1)` 涵蓋 3 月 31 日最後一微秒且不用算大小月或閏年；（缺）：寫法比 `A` 長一點。
  - `D`（優）：無；（缺）：前導萬用字元 `%` 讓 B-tree 索引完全無法定位起點，觸發全表掃描。
- **對應教材**：[Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)、[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)、[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/)

#### Q23：稽核重複註冊的 Email——資料分布與索引如何改寫三種寫法的效能排名

- **商業需求**：要從 50 萬筆 `customers` 找出所有重複出現的 `email`（歷史匯入曾造成同一個測試信箱 `test@bookstore.tw` 重複 2,000 次）。三種寫法都能回傳正確清單，在「尚未確定是否建有索引，且存在高重複熱點」的前提下，哪一種結構最穩？
- **題型**：情境權衡題
- **選項**：
  - `A`：分組法——`SELECT email FROM customers GROUP BY email HAVING COUNT(*) > 1;`
  - `B`：自連接法——`SELECT DISTINCT c1.email FROM customers c1 JOIN customers c2 ON c1.email = c2.email AND c1.customer_id <> c2.customer_id;`
  - `C`：`EXISTS` 法——`SELECT DISTINCT c1.email FROM customers c1 WHERE EXISTS (SELECT 1 FROM customers c2 WHERE c2.email = c1.email AND c2.customer_id <> c1.customer_id);`
  - `D`：把表全撈回應用程式記憶體用迴圈兩兩比對。
- **推薦選擇**：`A`
- **各選項優劣分析**：
  - `A`（優）：無論單一 email 重複 2 次還是 2,000 次，只掃描一次表並分組計數，完全不展開配對，無論是否建有索引都能維持線性或近線性穩定時間；（缺）：若還要同時取出每一筆重複列的完整明細欄位，須搭配子查詢或視窗函式 `COUNT(*) OVER (PARTITION BY email) > 1`。
  - `B`（優）：在重複極少且有索引時表現尚可；（缺）：高重複熱點會產生 `n * (n - 1)` 筆配對（重複 2,000 次展開近 400 萬對）再靠 `DISTINCT` 丟棄，成本隨重複次數平方爆炸，屬結構性退化。
  - `C`（優）：在 `email` 有索引時可對每列快速透過覆蓋索引定位並短路，效能接近 `A`；（缺）：缺少索引且引擎未轉寫為 hash semi-join 時（例如 SQLite），相關子查詢退化為每列掃全表，時間差到三個量級。
  - `D`（優）：無；（缺）：50 萬列網路傳輸與記憶體反序列化遠慢於資料庫內部處理，且雙層迴圈同樣是平方級複雜度。
- **對應教材**：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)、[Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)

#### Q24：找出各分類中高於該分類平均定價的書籍——相關子查詢、CTE 與視窗函式的取捨

- **商業需求**：商品分析頁要列出「定價高於所屬分類平均定價」的所有上架書，並顯示該書定價與該分類均價。`books` 表規模成長到 20 萬筆。哪一個寫法兼顧可讀性與穩定效能？
- **題型**：情境權衡題
- **選項**：
  - `A`：相關子查詢——`SELECT b.book_id, b.title, b.price, (SELECT AVG(b2.price) FROM books b2 WHERE b2.category_id = b.category_id AND b2.is_active = 1) AS avg_price FROM books b WHERE b.is_active = 1 AND b.price > (SELECT AVG(b2.price) FROM books b2 WHERE b2.category_id = b.category_id AND b2.is_active = 1);`
  - `B`：CTE 先按分類聚合再連接——`WITH cat_avg AS (SELECT category_id, AVG(price) AS avg_price FROM books WHERE is_active = 1 GROUP BY category_id) SELECT b.book_id, b.title, b.price, ca.avg_price FROM books b JOIN cat_avg ca ON ca.category_id = b.category_id WHERE b.is_active = 1 AND b.price > ca.avg_price;`
  - `C`：視窗函式——`WITH ranked AS (SELECT book_id, title, price, AVG(price) OVER (PARTITION BY category_id) AS avg_price FROM books WHERE is_active = 1) SELECT book_id, title, price, avg_price FROM ranked WHERE price > avg_price;`
  - `D`：用 `GROUP BY category_id HAVING price > AVG(price)` 直接寫在單層查詢裡。
- **推薦選擇**：`B` 或 `C`（需同時實測目標引擎的 `EXPLAIN`；分類數遠少於書本數時 `B` 常省下整表排序，支援視窗函式且要一次算多個統計值時 `C` 最精簡）
- **各選項優劣分析**：
  - `A`（優）：逐字貼合中文題意；（缺）：同一段相關子查詢寫了兩次，在不會自動去相關（decorrelation）的引擎上（如 SQLite）會對每本書重算整個分類平均，時間隨資料量超線性成長。
  - `B`（優）：各分類平均只算一次，語意清晰、跨引擎表現穩定（SQLite / PostgreSQL / MySQL 8 皆線性成長）；（缺）：`books` 被掃描兩次（一次算均價、一次讀明細）。
  - `C`（優）：只掃描一次 `books` 表即可同時保留明細與分類均價，後續要加「分類內價格排名」只需加一個視窗欄；（缺）：視窗函式須依 `category_id` 排序整批資料，記憶體與排序緩衝壓力取決於表大小。
  - `D`（優）：無；（缺）：`price` 不是分組鍵也不是聚合值，在標準 SQL 下報錯，且 `GROUP BY` 會把每個分類收成一列，無法列出個別書籍。
- **對應教材**：[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/)、[SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/)

#### Q25：Code Review 發現「答案對但關鍵字說謊」——宣告落空的查證動作

- **商業需求**：審查一段舊報表查詢，它在目前資料上輸出完全正確，內容如下：

```sql
SELECT DISTINCT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.status = 'paid';
```

審查者應該提出什麼意見？

- **題型**：情境權衡題
- **選項**：
  - `A`：輸出已經經過測試驗證完全正確，不必修改，避免動到既有查詢引入風險。
  - `B`：把 `LEFT JOIN` 改成 `INNER JOIN`，因為 `WHERE o.status = 'paid'` 已撤銷左連接保護；進一步確認只需要存在性時，改寫成 `WHERE EXISTS (...)` 以拿掉掩蓋連接重複的 `DISTINCT`。
  - `C`：保留 `LEFT JOIN`，只把 `DISTINCT` 刪掉以提高速度。
  - `D`：把 `WHERE o.status = 'paid'` 搬到 `ON` 裡面，其他不動。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：當下改動成本為零；（缺）：`LEFT JOIN` 對下一個讀這段程式的人宣告「要保留沒下單的顧客」，與實際行為相反；未來有人加條件或重構時會依錯的宣告做出錯誤修改。
  - `B`（優）：讓文字宣告與引擎實際行為重新對齊——把關鍵字換成最弱的版本（`LEFT` 換 `INNER`）輸出不變，證實 `LEFT` 落空；改用 `EXISTS` 連同多餘的 `DISTINCT` 一起消除，且更清楚表達「找至少有一筆已付款訂單的顧客」；（缺）：需跑回歸測試確認結果一致。
  - `C`（優）：減少一次去重；（缺）：同一位顧客有多筆已付款訂單時會立刻出現重複列，破壞正確性。
  - `D`（優）：讓 `LEFT JOIN` 真正生效；（缺）：直接改變了原本報表的業務語意（沒付款的顧客突然全出現在已付款名單裡）。
- **對應教材**：[SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)

---

### 階段六：跨引擎遷移、高並行寫入與從需求到上線（Q26–Q30）

最後一個階段把前面學到的全部能力放進真實成長中的生產環境：從單機 SQLite 遷移到多連線 PostgreSQL、解決並行競態、評估 schema 設計定價，以及把一句模糊商業需求逐步拆解並推進到上線驗收。

#### Q26：從 SQLite 遷移到 PostgreSQL——跨引擎差異的分級與處理順序

- **商業需求**：紙頁書店準備從單機 SQLite 遷到 PostgreSQL。團隊盤點舊查詢時發現四類寫法，哪一類最危險、即使全站整合測試綠燈仍可能在上線後悄悄出錯，必須優先靠靜態稽核與邊界反例查清？
- **題型**：情境權衡題
- **選項**：
  - `A`：`WHERE` 子句引用了 `SELECT` 別名（PostgreSQL 解析階段直接報欄名不存在）。
  - `B`：`ORDER BY rating DESC` 未寫 `NULLS LAST` 或 `NULLS FIRST`，以及字串比對依賴預設 collation（兩家引擎都能正常執行，但 `NULL` 排在開頭還是結尾、大小寫是否相等的輸出不同）。
  - `C`：使用了 SQLite 專屬的 `date(ordered_at, '-1 day')` 函式（PostgreSQL 執行時當場報函式不存在）。
  - `D`：`GROUP BY` 漏列非分組欄位（PostgreSQL 規劃階段直接報錯）。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：這類屬「當場報錯」等級，只要跑一次查詢就會被擋下，容易發現與修復。
  - `B`（優）：這正是跨引擎遷移中最高風險的「靜默而輸出不同」等級——SQLite 預設 `ORDER BY DESC` 把 `NULL` 排最後、PostgreSQL 預設把 `NULL` 排最前；沒有補上顯式 `NULLS LAST` 或明確排序規則，查詢不報錯、開發資料缺 `NULL` 時測試也全過，上線後分頁與排行榜卻靜默錯亂；（缺）：不能靠跑過語法檢查抓出來，必須在寫作規範與遷移稽核清單中明列並強制顯式宣告。
  - `C`（優）：無；（缺）：同樣屬「當場報錯」，測試涵蓋到的查詢就會立即曝光。
  - `D`（優）：無；（缺）：同樣在 PostgreSQL 準備執行時即報錯，不會靜默交付錯誤資料。
- **對應教材**：[SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)、[SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)

#### Q27：限量書高並行搶購扣庫存——多連線先讀後寫競態

- **商業需求**：簽名版書籍只剩 `stock = 1`，上線 PostgreSQL 後兩位顧客在同一毫秒按下結帳。原本在單寫入者 SQLite（`BEGIN IMMEDIATE`）跑得穩的「先 `SELECT stock` 檢查再 `UPDATE stock = stock - 1`」出現超賣（庫存變 `-1`）。哪一個寫法最直接防住超賣且鎖競爭最小？
- **題型**：情境權衡題
- **選項**：
  - `A`：維持先 `SELECT` 再 `UPDATE`，只在應用程式程式碼裡加一個 `if stock >= 1` 檢查。
  - `B`：單句帶條件更新——`UPDATE books SET stock = stock - :qty WHERE book_id = :id AND stock >= :qty RETURNING stock;`，依影響列數是否為 1 判斷扣庫存成功或庫存不足（同時加 `CHECK (stock >= 0)` 兜底）。
  - `C`：在交易開頭對整張 `books` 表加 `LOCK TABLE books IN EXCLUSIVE MODE`。
  - `D`：把交易改用 `SELECT stock FROM books WHERE book_id = :id FOR UPDATE`，檢查後再 `UPDATE`。
- **推薦選擇**：`B`（單一商品直接扣減時最簡短、鎖持有時間最短）；若同一個交易內須依讀出來的多個欄位做複雜商業計算或一次鎖多件商品（固定依 `book_id` 升冪鎖定防死鎖）則選 `D`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：在 PostgreSQL 預設 `READ COMMITTED` 下，兩個交易都會讀到 `stock = 1`、雙雙通過應用層 `if` 檢查再各自減 1，必定超賣。
  - `B`（優）：把條件檢查與扣減放進單一語句的列鎖內執行，第二個交易會等第一個提交後重估 `WHERE stock >= :qty` 並得到 0 列受影響，鎖時間極短；搭配 `CHECK (stock >= 0)` 形成最後一道資料庫防線；（缺）：一次結帳買多本書時須注意更新順序（依 `book_id` 排序）以避免死鎖，且交易內其他複雜狀態判斷仍需 `FOR UPDATE`。
  - `C`（優）：確實不會超賣；（缺）：鎖住整張 `books` 表，買 A 書的人會擋住買 B 書的人，並行吞吐量崩潰。
  - `D`（優）：同樣正確防超賣，且允許在扣減前讀取商品價格、促銷狀態做複雜驗證再決定是否更新；（缺）：多一次往返查詢，鎖從 `SELECT FOR UPDATE` 一路持到交易結束，若中間穿插外部金流呼叫會拉長鎖等待。
- **對應教材**：[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)、[backend 1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)

#### Q28：背景匯出 Worker 認領佇列與門市班表防重疊——PostgreSQL 並行構造選擇

- **商業需求**：書店後台有 4 台 worker 同時輪詢 `export_jobs` 認領 `status = 'queued'` 的報表匯出任務，希望各 worker 互不重複領取、且不被其他 worker 正在領的那一列擋住等待。哪一種 PostgreSQL 認領查詢最合適？
- **題型**：情境權衡題
- **選項**：
  - `A`：`SELECT job_id FROM export_jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1;` 再另外 `UPDATE`。
  - `B`：`SELECT job_id FROM export_jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1 FOR UPDATE;` 再在同一交易內 `UPDATE`。
  - `C`：`WITH picked AS (SELECT job_id FROM export_jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) UPDATE export_jobs j SET status = 'running', claimed_by = :worker FROM picked WHERE j.job_id = picked.job_id RETURNING j.*;`
  - `D`：把整個認領交易設成 `ISOLATION LEVEL SERIALIZABLE`，不加任何鎖子句。
- **推薦選擇**：`C`（註：若另一項需求是「門市班表 `store_shifts` 禁止同一員工時間區間重疊」，因無法鎖住尚未存在的列，則須改用 PostgreSQL 排除約束 `EXCLUDE USING gist` 或 `SERIALIZABLE`）
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：多台 worker 同時讀到同一筆 `job_id`，重複匯出同一份報表。
  - `B`（優）：避免重複認領；（缺）：worker 2、3、4 都會堵在第一筆已被 worker 1 鎖住的列上排隊等待，等於把四台 worker 串行化。
  - `C`（優）：`SKIP LOCKED` 讓其他 worker 直接跳過正在被鎖定的列去領下一筆，同時保證不重複認領與高並行吞吐；（缺）：屬 PostgreSQL（與 MySQL 8+）多連線伺服器專用構造，SQLite 無對應語法；且不保證嚴格 FIFO（被跳過的列若交易回滾會稍後才被別台領走）。
  - `D`（優）：能防重複認領；（缺）：衝突發生時會拋出 serialization failure，應用層必須寫重試迴圈，在高並行佇列認領下重試率高、效率遠低於 `SKIP LOCKED`。
- **對應教材**：[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)

#### Q29：建表時的決定替未來查詢定價——訂單單價複製 vs 外鍵引用

- **商業需求**：設計 `order_items` 表時，針對「這筆訂單當時這本書賣多少錢」，有兩種 schema 方案：一是只在 `order_items` 存 `book_id`，算歷史營收時 `JOIN books` 拿 `books.price`；二是在下單當下把價格複製存進 `order_items.unit_price`。該選哪一種？
- **題型**：情境權衡題
- **選項**：
  - `A`：只存 `book_id`、不存 `unit_price`，避免資料重複（嚴格遵守正規化）。
  - `B`：在 `order_items` 複製儲存下單當下的 `unit_price`（並保留 `book_id` 供查詢商品維度）。
  - `C`：只在 `orders` 存整張訂單的 `total_amount`，不建 `order_items` 明細表，明細改存成一個 JSON 字串塞在 `orders` 裡。
  - `D`：每次書籍改價都建一筆新的 `book_id`，舊 `book_id` 永遠不修改價格。
- **推薦選擇**：`B`（一般電商標準解）；若業務同時需要稽核完整商品版本歷史（例如合約／費率版本），則進一步評估帶版本編號的價格版本表
- **各選項優劣分析**：
  - `A`（優）：省下一個整數欄位、少寫一次欄位值；（缺）：只要書店把某本書從 400 元調漲到 450 元，所有歷史訂單的營收報表會瞬間全部改寫成新價格，財務對帳完全損毀。
  - `B`（優）：鎖住交易當下的歷史事實，算歷史營收與單品退貨退款都不用回查變動的商品價目表，查詢更單純且歷史金額不可變；（缺）：多佔一個欄位空間，且開發者須區分「下單時成交價（`order_items.unit_price`）」與「目前定價（`books.price`）」。
  - `C`（優）：單張訂單讀取不需 `JOIN`；（缺）：要算「哪本書這週賣最好」「某分類總銷量」時無法利用關聯索引與外鍵，只能全表解析 JSON，日後查詢代價極高。
  - `D`（優）：歷史價格不會變動；（缺）：同一個商品被拆成多個 `book_id`，查「這本書累積評價與總銷量」時必須跨版本歸併，大幅複雜化所有商品層查詢。
- **對應教材**：[SQL.0 一段查詢從需求到上線的決定：追問需求、設定判斷標準、選寫法、補前提、量代價、對邊界與交付](/backend/01-database/sql/decisions-from-requirement-to-shipping/)、[backend 1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則、外鍵執法，以及從另一張表取值時的複製與引用](/backend/01-database/design-decisions-price-every-query/)

#### Q30：綜合實戰——把「哪些書這週銷量比上週成長超過 50%」從需求做到上線

- **商業需求**：營運主管在 Slack 丟來一句話：「幫我撈一下哪些書這週銷量比上週成長超過 50%，下週一開會要看。」在動手寫 SQL 與準備上線之前，哪一個工作順序與邊界處置最完整？
- **題型**：情境權衡題
- **選項**：
  - `A`：立刻寫一段兩週 `GROUP BY book_id` 自連接查詢，在本機開發資料庫跑出 10 筆結果，確認欄位齊全就直接上線排程。
  - `B`：先追問需求把規則定死（銷量算「本數」還是「金額」？這週與上週以哪個時區、週一還是週日起算？只算 `paid/shipped` 還是排除 `refunded`？上週銷量為 `0` 本週為 `3` 是否計入成長超過 50%？）；接著造含「上週為 0、退款單、跨午夜時區、同一訂單買多本」的反例資料當驗收基準；再依資料量與 `orders(ordered_at, status)` 索引挑寫法並跑 `EXPLAIN` 驗證；最後記錄事後退款會讓歷史週報變動的對帳邊界。
  - `C`：直接套用萬用模板 `WHERE (this_week - last_week) / last_week > 0.5`，把所有上週為 0 的書一律過濾掉以避免除以零錯誤。
  - `D`：為了查詢最快，把過去一年的訂單先全部複製成一張寬表，不追問退款與時區定義。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：產出第一份 SQL 最快；（缺）：跳過追問需求、驗收反例、執行計畫驗證與邊界盤點四個步驟——只要時區差 8 小時、整數除法截斷（SQLite 中 `3 / 2 = 1` 而非 `1.5`）、或上週銷量為 0 觸發除以零或靜默排除，會議上就會交出錯數字。
  - `B`（優）：完整走完 `SQL.0` 的七個決定（追問需求、設定判斷標準、選寫法、補前提、量代價、對邊界、交付），用乘法 `this_week * 2 > last_week * 3` 避開整數除法與除以零，並把上週為 0 與事後退款的處理方式事先與需求方對齊；（缺）：開工前多了 10 至 15 分鐘的溝通與造反例成本，但在生產系統上遠低於報表錯帳後的重算與信任損失。
  - `C`（優）：避免程式崩潰；（缺）：在 SQLite／PostgreSQL 裡兩個整數相除會做整數除法（`3 / 2` 變成 `1`、`(14 - 10) / 10` 變成 `0`），而且未經確認就排除了「新品爆紅（上週 0、這週 500 本）」最值得主管關注的書。
  - `D`（優）：查詢單次執行時間短；（缺）：在需求定義還沒對齊前就做寬表最佳化，只是用更快的速度算出錯誤答案，還多出同步維護寬表的工程成本。
- **對應教材**：[SQL.0 一段查詢從需求到上線的決定：追問需求、設定判斷標準、選寫法、補前提、量代價、對邊界與交付](/backend/01-database/sql/decisions-from-requirement-to-shipping/)、[SQL.23 查詢設計的完整示範：把「哪幾天氣溫比前一天高」從需求做到上線](/backend/01-database/sql/requirement-to-shipped-query/)

## 多題組變體池規格（領域乙與領域丙，共 60 組對應變體）

每個能力節點除了上面的領域甲基準題（`Q01`–`Q30`），在領域乙（雲課堂）與領域丙（捷配物流）各設一組結構相異的變體題，並刻意輪替出題視角與前提翻轉，讓系統在每次隨機抽題時能產出截然不同的測驗卷。

| 能力節點 | 基準題 | 領域乙變體（雲課堂）與出題視角                                                                                                    | 領域丙變體（捷配物流）與出題視角                                                                                                               |
| -------- | ------ | --------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `S1-01`  | `Q01`  | `choose-query`：課程卡片 API 挑選欄位（未來將新增長文字 `syllabus_markdown`）                                                     | `diagnose-plan`：運單清單用 `SELECT *` 後新增大 JSON 欄導致延遲暴增與覆蓋索引失效                                                              |
| `S1-02`  | `Q02`  | `pick-counterexample`：找出會讓未加括號 `AND`/`OR` 混進免費方案的課程列                                                           | `choose-query`：運費與狀態複合條件篩選（含閉區間端點與半開時間區間對照）                                                                       |
| `S1-03`  | `Q03`  | `choose-query`：找出未完課（`completed_at IS NULL`）且 `country` 未填的學員                                                       | `tradeoff-design`（前提翻轉）：`merchants.tier` 設有 `NOT NULL` 約束時，評估是否還需要 `COALESCE`                                              |
| `S1-04`  | `Q04`  | `pick-counterexample`：課程觀看秒數排行榜沒加 `course_id` 次排序鍵時的平手漂移反例                                                | `choose-query`：同日多倉高運費運單前十名與 `ORDER BY` 欄位方向陷阱                                                                             |
| `S1-05`  | `Q05`  | `choose-query`：統計各訂閱方案付費帳單總額，過濾 `status = 'paid'` 與總額門檻                                                     | `diagnose-plan`：把 `status = 'delivered'` 寫進 `HAVING` 在 SQLite 與 PostgreSQL 的分岔                                                        |
| `S2-01`  | `Q06`  | `choose-query`：計算課程完課率別名並在 `WHERE`／`ORDER BY` 使用的跨引擎寫法                                                       | `diagnose-plan`：把 `fee_cents / 100.0 AS fee_twd` 放進 `WHERE` 在 PostgreSQL 報錯的原因                                                       |
| `S2-02`  | `Q07`  | `pick-counterexample`：用 `COUNT(*)` 統計全部學員完課數，選出哪一筆學員資料會被多算成 1                                           | `choose-query`：列出全部簽約商家與本月運單數（含零寄件商家）                                                                                   |
| `S2-03`  | `Q08`  | `tradeoff-design`（前提翻轉）：只需要「本月有付費帳單的學員」時，把誤寫的 `LEFT JOIN` 簡化回 `INNER JOIN`                         | `pick-counterexample`：查所有倉庫與本週異常運單，把 `status = 'returned'` 寫在 `WHERE` 加上 `OR shipment_id IS NULL` 仍漏掉哪種倉庫            |
| `S2-04`  | `Q09`  | `choose-query`：`users → subscriptions → invoices` 三表串接保留未訂閱學員與未開帳訂閱                                             | `diagnose-plan`：`merchants LEFT JOIN shipments RIGHT JOIN shipment_events` 保護範圍倒轉診斷                                                   |
| `S2-05`  | `Q10`  | `choose-query`：同時算每位學員「累計付費帳單金額」與「完成單元總數」避免雙表連接膨脹                                              | `pick-counterexample`：算各商家總運費時直接 `JOIN shipment_events`，選出多筆掃描事件導致運費翻倍的反例                                         |
| `S2-06`  | `Q11`  | `choose-query`：列出每門課程與先修課名稱（`courses.prerequisite_id` 自連接保留無先修課）                                          | `choose-query`：列出每個衛星倉與所屬主轉運中心名稱（`warehouses.parent_hub_id` 自連接）                                                        |
| `S3-01`  | `Q12`  | `tradeoff-design`（前提翻轉）：需求改成「列出看過後端課程的學員以及他最後觀看的課名」，為何不能再只用 `EXISTS`                    | `choose-query`：找出有寄過退貨運單的商家名單（不重複列，比較 `EXISTS`／`IN`／`DISTINCT JOIN`）                                                 |
| `S3-02`  | `Q13`  | `pick-counterexample`：找「沒有付費帳單的訂閱」，選出哪一筆 `invoices` 紀錄會讓 `NOT IN` 整段回傳 0 列                            | `tradeoff-design`（前提翻轉）：`shipment_events.shipment_id` 加上 `NOT NULL` 約束後，比較 `NOT IN` 與 `NOT EXISTS` 的安全邊界與維護風險        |
| `S3-03`  | `Q14`  | `diagnose-plan`：`users LEFT JOIN subscriptions GROUP BY subscriptions.user_id` 把所有免費未訂閱者併成一組                        | `choose-query`：依商家統計運單數並輸出商家名稱，對照 PostgreSQL、MySQL 8 與 DuckDB 規則                                                        |
| `S3-04`  | `Q15`  | `choose-query`：同時顯示每期帳單金額與該學員歷史累計付款佔比（`SUM() OVER` vs `GROUP BY`）                                        | `pick-counterexample`：計算每張運單相鄰兩次掃描事件間隔時間，漏掉 `PARTITION BY shipment_id` 的錯誤輸出                                        |
| `S3-05`  | `Q16`  | `tradeoff-design`（前提翻轉）：後台管理頁只有 300 筆訂閱且客服明確要跳轉「第 8 頁」，比較全序 `OFFSET` 與 Keyset                  | `diagnose-plan`：百萬筆 `shipment_events` 用 `(recorded_at DESC, event_id ASC)` 混合方向時誤用列值比較 `(a, b) < (x, y)` 的錯誤結果            |
| `S4-01`  | `Q17`  | `choose-query`：批次把到期試用 `subscriptions` 轉 `past_due` 並以 `RETURNING` 觸發催繳通知                                        | `choose-query`：批次把超時未簽收 `shipments` 標記異常並防覆蓋剛完成簽收的列                                                                    |
| `S4-02`  | `Q18`  | `choose-query`：學員請求刪除帳號時，歷史 `invoices` 的外鍵策略與個人資料匿名化取捨                                                | `diagnose-plan`：SQLite 測試環境 `PRAGMA foreign_keys` 未開啟導致孤兒 `shipment_events` 混入的成因                                             |
| `S4-03`  | `Q19`  | `choose-query`：跨引擎匯入外部 BI 報表表名含大寫與保留字 `user` 時的識別字處理                                                    | `diagnose-plan`：PostgreSQL 建表用雙引號 `"warehouseCode"` 後未引號查詢找不到欄位的排查                                                        |
| `S4-04`  | `Q20`  | `choose-query`：優惠代碼與帳號 `email` 同時存在區分大小寫與不分大小寫欄位時的 collation 分層                                      | `tradeoff-design`：商家代碼 `account_key` 前綴查詢 `LIKE 'TW%'` 在 PostgreSQL 預設非 C locale 下走不了 B-tree 索引的修法（`text_pattern_ops`） |
| `S4-05`  | `Q21`  | `choose-query`：客服後台帳號與金流 Webhook 寫入帳號的 PostgreSQL 角色與資料表授權切分                                             | `choose-query`：外部合作商家透過資料列層級政策（RLS）只能讀自己 `merchant_id` 運單的授權設計                                                   |
| `S5-01`  | `Q22`  | `diagnose-plan`：讀 `EXPLAIN` 抓出 `WHERE EXTRACT(YEAR FROM issued_at) = 2026` 走 `Seq Scan` 的原因與改寫                         | `choose-query`：查單日物流簽收事件，比較 `date(recorded_at) = ...`、半開區間與複合索引 `(event_type, recorded_at)`                             |
| `S5-02`  | `Q23`  | `diagnose-plan`：百萬筆 `webhook_events` 稽核重複 `external_id`，對照有無索引與單一重送風暴下的計畫變化                           | `tradeoff-design`：大客戶佔全表 35% 運單（低選擇率）時，查該客戶運單為何最佳化器棄索引改掃全表                                                 |
| `S5-03`  | `Q24`  | `choose-query`：找出各學程中完課秒數高於該學程平均的課程，比較相關子查詢、CTE 與視窗函式                                          | `diagnose-plan`：將相關子查詢改寫成 CTE 後在 SQLite 耗時從秒級降到毫秒級的計畫對照                                                             |
| `S5-04`  | `Q25`  | `pick-counterexample`：審查含 `LEFT JOIN invoices ... WHERE invoices.status = 'paid'` 的查詢，選出把關鍵字換成最弱版本的查證動作  | `choose-query`：審查 `CROSS JOIN` 配 `WHERE` 等值條件與無效 `COALESCE` 的宣告落空修法                                                          |
| `S6-01`  | `Q26`  | `choose-query`：將學習進度報表從 MySQL 遷往 PostgreSQL，區分當場報錯與靜默輸出差異                                                | `pick-counterexample`：從 SQLite 遷到 PostgreSQL 後 `ORDER BY completed_at DESC` 空值排位顛倒導致「未完課排最前面」的反例                      |
| `S6-02`  | `Q27`  | `choose-query`：多裝置同時提交同一單元進度與限量早鳥名額扣減的並行寫入方案比較                                                    | `diagnose-plan`：兩個調度請求同時扣減倉庫剩餘車位出現負數的交易隔離原因與修法                                                                  |
| `S6-03`  | `Q28`  | `choose-query`：多台 worker 認領 `webhook_events` 並以唯一約束擋下重送事件（`FOR UPDATE SKIP LOCKED` + `ON CONFLICT DO NOTHING`） | `choose-query`：防止同一位司機在 `driver_shifts` 被排進重疊時段（`EXCLUDE USING gist` vs `SERIALIZABLE` vs 應用層先查後寫）                    |
| `S6-04`  | `Q29`  | `tradeoff-design`：訂閱調整牌價後，歷史 `invoices` 該存結帳當下金額快照還是外鍵引用方案牌價表                                     | `tradeoff-design`：運單費率改版時，評估在 `shipments` 存成交運費與保留費率版本編號的查詢與稽核成本                                             |
| `S6-05`  | `Q30`  | `tradeoff-design`：主管問「本月流失率比上月惡化的方案有哪些」，從定義流失、造反例到對帳邊界的完整推導                             | `tradeoff-design`：營運問「哪些倉庫本週異常件比例超標」，處理零運單倉庫、跨午夜時區與事後補掃描的完整上線決策                                  |

## 高複雜度示範變體與跨概念複合陷阱挑戰題（`C01`–`C06`）

以下完整展開六道**跨概念複合陷阱題**（每題同時藏入兩到三個彼此互動的 SQL 陷阱，並混用三個商業領域與四種出題視角），作為盲測鑑別模式的高階基準。

### C01（複合陷阱：前提翻轉 + 否定存在性 + 查詢計畫代價）——雲課堂未開帳訂閱稽核

- **領域**：雲課堂（`cloud-academy`）
- **疊加考點**：`NOT IN` 與 `NOT NULL` 約束（前提翻轉）× 反連接執行計畫 × 外鍵空值邊界
- **出題視角**：`tradeoff-design`（前提翻轉）
- **商業需求與前提**：財務對帳要找出「從未產生過任何 `paid` 帳單的 `active` 訂閱」。`subscriptions` 有 20 萬筆、`invoices` 有 400 萬筆；PostgreSQL 18 正式庫上 `invoices.sub_id` **目前允許 `NULL`**（因為有 12 筆歷史人工匯入帳單），且已建索引 `idx_invoices_sub_status ON invoices(sub_id, status)`。同事提出兩個修法：一派主張直接寫 `NOT IN`，另一派主張先加條件排除 `NULL` 或改寫成 `NOT EXISTS`。哪個方案同時滿足正確性與大表效能？
- **選項**：
  - `A`：`SELECT s.sub_id FROM subscriptions s WHERE s.status = 'active' AND s.sub_id NOT IN (SELECT i.sub_id FROM invoices i WHERE i.status = 'paid');`
  - `B`：`SELECT s.sub_id FROM subscriptions s WHERE s.status = 'active' AND s.sub_id NOT IN (SELECT i.sub_id FROM invoices i WHERE i.status = 'paid' AND i.sub_id IS NOT NULL);`
  - `C`：`SELECT s.sub_id FROM subscriptions s WHERE s.status = 'active' AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.sub_id = s.sub_id AND i.status = 'paid');`
  - `D`：`SELECT DISTINCT s.sub_id FROM subscriptions s LEFT JOIN invoices i ON i.sub_id = s.sub_id WHERE s.status = 'active' AND (i.status <> 'paid' OR i.invoice_id IS NULL);`
- **推薦選擇**：`C`（若 `invoices.sub_id` 未來加上 `NOT NULL` 約束，PostgreSQL 仍可能無法把 `NOT IN` 轉成最佳 Anti-Join，在 PostgreSQL 18 環境下依舊優先 `C`）
- **各選項優劣分析**：
  - `A`（優）：語意看似簡短；（缺）：只要那 12 筆人工匯入帳單中有一筆是 `paid` 且 `sub_id IS NULL`，整段查詢靜默回傳 0 列。
  - `B`（優）：補上 `i.sub_id IS NOT NULL` 後輸出結果與 `C` 相同，修掉了三值邏輯回傳 0 列的問題；（缺）：在 PostgreSQL 上 `NOT IN` 無法像 `NOT EXISTS` 直接轉寫成 Hash/Merge Anti-Join（因為最佳化器仍須防範外層 `s.sub_id` 為 `NULL` 的語意差異），400 萬列上常退化成較慢的 `SubPlan` 或 hashed subplan 耗記憶體。
  - `C`（優）：對 `NULL` 免疫，PostgreSQL 直接規劃為 Anti-Join 並可善用 `idx_invoices_sub_status`，不會因多筆帳單膨脹列數，維護者未來移除任何過濾條件都不會重新引入 `NOT IN` 陷阱；（缺）：語法比 `IN` 多寫一層關聯條件 `i.sub_id = s.sub_id`。
  - `D`（優）：看起來處理了 `IS NULL`；（缺）：只要某筆訂閱同時有一期 `paid` 與一期 `void` 帳單，`i.status <> 'paid'` 會在 `void` 那一列成立，把已有付費紀錄的訂閱錯誤算進未付費名單。
- **對應教材**：[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)、[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)、[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)

### C02（複合陷阱：鏈式外連接 + `ON`/`WHERE` 撤銷保護 + 雙重一對多列數膨脹）——紙頁書店顧客毛利與評價月報

- **領域**：紙頁書店（`bookstore`）
- **疊加考點**：鏈式 `LEFT JOIN` 保護範圍 × `WHERE` 撤銷保護 × 一對多與多對多連接膨脹
- **出題視角**：`choose-query`
- **商業需求與前提**：要列出「所有台北顧客（`city = 'Taipei'`）」，顯示他們在 2026 年 3 月的「已付款訂單總金額」與「3 月送出的五星評價則數」。3 月沒下單或沒評價的台北顧客仍要列出來並顯示 `0`。已知一筆訂單可有多則評價，且有些評價沒有對應 3 月訂單（例如 2 月下單、3 月才評）。
- **選項**：
  - `A`：`SELECT c.customer_id, COALESCE(SUM(o.total_amount), 0) AS spent, COUNT(r.review_id) AS five_star_cnt FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01' LEFT JOIN reviews r ON r.order_id = o.order_id AND r.rating = 5 AND r.created_at >= '2026-03-01' AND r.created_at < '2026-04-01' WHERE c.city = 'Taipei' GROUP BY c.customer_id;`
  - `B`：`WITH mar_orders AS (SELECT customer_id, SUM(total_amount) AS spent FROM orders WHERE status = 'paid' AND ordered_at >= '2026-03-01' AND ordered_at < '2026-04-01' GROUP BY customer_id), mar_reviews AS (SELECT o.customer_id, COUNT(*) AS five_star_cnt FROM reviews r JOIN orders o ON o.order_id = r.order_id WHERE r.rating = 5 AND r.created_at >= '2026-03-01' AND r.created_at < '2026-04-01' GROUP BY o.customer_id) SELECT c.customer_id, COALESCE(mo.spent, 0) AS spent, COALESCE(mr.five_star_cnt, 0) AS five_star_cnt FROM customers c LEFT JOIN mar_orders mo ON mo.customer_id = c.customer_id LEFT JOIN mar_reviews mr ON mr.customer_id = c.customer_id WHERE c.city = 'Taipei';`
  - `C`：與 `A` 相同，但把 `SUM(o.total_amount)` 改成 `SUM(DISTINCT o.total_amount)`。
  - `D`：與 `B` 相同，但把最外層 `WHERE c.city = 'Taipei'` 搬進第一個 `LEFT JOIN` 的 `ON` 條件裡。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：把訂單與評價的時間條件放進 `ON`，沒撤銷 `LEFT JOIN` 對台北顧客的保護；（缺）：同時踩中兩個隱蔽錯誤——一筆 3 月訂單若有兩則 3 月五星評價，`SUM(o.total_amount)` 會把訂單金額算兩次；且評價是接在「3 月訂單」後面，2 月下單但 3 月才送出的五星評價全部漏算。
  - `B`（優）：把兩個不同時間軸的指標各自獨立聚合到 `customer_id` 粒度後再與 `customers` 左連接，同時解決列數膨脹、保留未下單台北顧客，並正確計入「2 月下單、3 月評價」的五星則數；（缺）：寫法較長，須對 `orders(ordered_at, status)` 與 `reviews(created_at, rating)` 建索引才能避免大表全掃。
  - `C`（優）：無；（缺）：除了仍漏算「2 月下單、3 月評價」，同一顧客在 3 月下兩張同金額訂單時 `SUM(DISTINCT ...)` 會少算一張。
  - `D`（優）：無；（缺）：把屬於受保護左表 `customers` 的篩選條件 `c.city = 'Taipei'` 放進 `ON` 後，非台北顧客依然會被 `LEFT JOIN` 保留下來（只是金額變成 `0`），名單混入全台灣顧客。
- **對應教材**：[SQL.3 連接的起手式：配對條件的位置與連接種類的選擇](/backend/01-database/sql/join-starts-from-the-relationship/)、[SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)、[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)

### C03（複合陷阱：反例擊破視角——視窗函式 + 分區遺漏 + 跨引擎 `NULL` 排序）——捷配物流異常件追蹤

- **領域**：捷配物流（`swift-logistics`）
- **疊加考點**：`ROW_NUMBER()` 分區與排序 × `NULL` 在 `ORDER BY DESC` 的跨引擎排位 × 造反例驗證
- **出題視角**：`pick-counterexample`
- **商業需求與前提**：分析師在 SQLite 寫了一段查詢，想取出「每張運單最新一筆掃描事件」，準備直接搬去 PostgreSQL 執行：

```sql
SELECT shipment_id, event_type, recorded_at
FROM (
  SELECT shipment_id, event_type, recorded_at,
         ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY recorded_at DESC) AS rn
  FROM shipment_events
) t
WHERE rn = 1;
```

已知 `shipment_events` 在某次離線同步異常時可能寫入 `recorded_at IS NULL` 或同秒兩筆不同 `event_type` 的資料。以下哪一項資料情境在 SQLite 上回傳正常、搬到 PostgreSQL 後卻會靜默把**錯的事件**當成最新狀態？

- **選項**：
  - `A`：一張運單只有一筆 `recorded_at = '2026-03-10 09:00:00'` 的 `picked` 事件。
  - `B`：一張運單有兩筆事件，分別是 `('picked', '2026-03-10 09:00:00')` 與 `('signed', '2026-03-10 18:00:00')`。
  - `C`：一張運單同時有正常的 `('signed', '2026-03-10 18:00:00')` 以及一筆異常的 `('exception', NULL)`（`recorded_at` 為 `NULL`）。
  - `D`：兩張不同運單在同一秒各自有一筆 `picked` 事件。
- **推薦選擇**：`C`（根本修法是補上顯式 `NULLS LAST` 與次排序鍵 `event_id DESC`：`ORDER BY recorded_at DESC NULLS LAST, event_id DESC`）
- **各選項優劣分析**：
  - `A`（優）：單筆資料不會觸發排序歧義；（缺）：無法檢出任何跨引擎排序差異。
  - `B`（優）：兩筆時間相異且皆非 `NULL`；（缺）：在 SQLite 與 PostgreSQL 都會一致選出 `signed`，無法揭露缺陷。
  - `C`（優）：精準命中跨引擎 `NULL` 排序差異——SQLite 的 `ORDER BY recorded_at DESC` 預設把 `NULL` 排最後（`rn = 1` 是 `signed`）；PostgreSQL 的 `ORDER BY DESC` 預設把 `NULL` 排最前（`rn = 1` 變成時間缺漏的 `exception`），完全不報錯卻讓客戶頁面從「已簽收」倒退成「異常」；（缺）：這組反例只抓到 `NULL` 排序，實務驗收還應額外補一組「同一運單同秒兩筆事件」反例來迫使查詢補上 `event_id DESC`。
  - `D`（優）：兩張不同運單被 `PARTITION BY shipment_id` 分在不同分區，彼此不影響排名；（缺）：無法擊破查詢。
- **對應教材**：[SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/)、[SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)、[SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)

### C04（複合陷阱：混合升降冪 Keyset 分頁 + 複合索引順序 + Sargable）——捷配物流百萬級運單搜尋

- **領域**：捷配物流（`swift-logistics`）
- **疊加考點**：複合索引前導欄順序 × Keyset 混合排序方向不可用列值比較 × `OFFSET` 退化
- **出題視角**：`diagnose-plan`
- **商業需求與前提**：`shipments` 表有 800 萬筆資料，列表頁需求為「篩選特定 `warehouse_id = :wid` 且 `status = 'in_transit'`，依 `created_at DESC, shipment_id ASC` 排序，每次取 30 筆做下一頁翻頁」。團隊寫了以下查詢並建了索引 `CREATE INDEX idx_bad ON shipments(created_at, warehouse_id);`，上線後出現兩個事故：翻到下一頁偶爾漏資料，且查詢耗時 1.8 秒。哪一組診斷與修法同時解決正確性與效能？

```sql
SELECT shipment_id, merchant_id, fee_cents, created_at
FROM shipments
WHERE warehouse_id = :wid
  AND status = 'in_transit'
  AND (created_at, shipment_id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, shipment_id ASC
LIMIT 30;
```

- **選項**：
  - `A`：只要把索引改成 `(created_at DESC, shipment_id ASC)` 即可，查詢語句完全正確。
  - `B`：把查詢的列值比較改寫成展開式 `(created_at < :last_created_at OR (created_at = :last_created_at AND shipment_id > :last_id))`，並建立複合索引 `(warehouse_id, status, created_at DESC, shipment_id ASC)`（等值過濾欄放前面、排序與範圍欄放後面）。
  - `C`：把 `ORDER BY` 改成 `ORDER BY created_at DESC LIMIT 30 OFFSET :offset`，捨棄接續標記。
  - `D`：只把查詢裡的 `<` 改成 `<=`，就能避免漏資料且不需改索引。
- **推薦選擇**：`B`（若業務允許把排序改成同向 `created_at DESC, shipment_id DESC`，則可用更簡短且更易走單段索引掃描的列值比較 `(created_at, shipment_id) < (:last_created_at, :last_id)`）
- **各選項優劣分析**：
  - `A`（優）：修正了索引與排序方向；（缺）：漏掉兩件核心缺陷——等值欄位 `warehouse_id` 與 `status` 沒放索引最前面仍須過濾大量別倉資料；更重要的是 `ORDER BY created_at DESC, shipment_id ASC` 是一降一升，列值比較 `(a, b) < (x, y)` 卻對兩欄都做小於（等價於雙降），遇到同秒多筆運單時第二頁會漏掉 `shipment_id` 較大的列。
  - `B`（優）：展開式精確對應「時間較早，或同時間但 `shipment_id` 較大」，徹底修復翻頁漏列；索引把高選擇率等值欄 `(warehouse_id, status)` 放前導，再接 `(created_at DESC, shipment_id ASC)`，一次索引範圍定位即取完 30 筆免排序；（缺）：展開式帶 `OR` 時部分引擎的計畫不如雙降列值比較直覺，實作前應跑 `EXPLAIN` 確認索引使用方式；若可協商改為同向雙降則能兼得語法簡潔與最佳索引掃描。
  - `C`（優）：無；（缺）：800 萬筆下深頁 `OFFSET` 效能更慘，且拿掉 `shipment_id` 後連全序都失去。
  - `D`（優）：無；（缺）：`<=` 會讓每頁第一筆重複出現上一頁最後一筆，且方向矛盾與索引前導欄問題皆未解決。
- **對應教材**：[SQL.12 分頁的排序鍵與接續標記：同分的列、全序與 OFFSET 的代價](/backend/01-database/sql/pagination-needs-a-total-order/)、[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)

### C05（複合陷阱：高並行佇列認領 + 冪等去重 + 外部呼叫持鎖）——雲課堂金流 Webhook 處理管線

- **領域**：雲課堂（`cloud-academy`）
- **疊加考點**：`FOR UPDATE SKIP LOCKED` × 唯一約束冪等寫入 × 交易邊界不包外部 HTTP 呼叫
- **出題視角**：`tradeoff-design`
- **商業需求與前提**：PostgreSQL 上有 6 台 worker 處理金流商送來的 `webhook_events`。同一筆付款事件金流商可能重送兩次（相同 `provider` 與 `external_id`），且 worker 處理每筆事件時需要呼叫外部寄信 API（耗時約 800ms）。團隊該如何切分資料表約束、認領語句與交易邊界？
- **選項**：
  - `A`：開一個大交易，先 `SELECT ... FOR UPDATE LIMIT 1` 鎖住事件，在交易內呼叫外部寄信 API，寄信成功後再 `UPDATE status = 'done'` 並 `COMMIT`。
  - `B`：在 `webhook_events` 建立 `UNIQUE (provider, external_id)`，接收端寫入用 `INSERT ... ON CONFLICT (provider, external_id) DO NOTHING` 擋重送；worker 用短交易執行 `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1` 並立刻把 `status` 改成 `'processing'` 後 `COMMIT` 釋放列鎖；於交易外呼叫外部寄信 API，完成後再開短交易把 `status` 改成 `'done'`（並設逾時回收卡住的 `'processing'` 任務）。
  - `C`：不建唯一約束，由應用層收到 Webhook 時先 `SELECT COUNT(*)` 檢查是否重複再 `INSERT`，worker 用 `SELECT ... LIMIT 1` 輪詢。
  - `D`：把整個資料庫預設隔離等級調成 `SERIALIZABLE`，讓所有 worker 自動排隊且不需改寫任何查詢。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：寄信失敗回滾時狀態自動回到原樣；（缺）：踩中三個並行地雷——沒加 `SKIP LOCKED` 讓 6 台 worker 互等成單一執行緒；在資料庫交易內等 800ms 外部 HTTP 呼叫會把連線池與列鎖塞滿；若外部寄信已送出但 `COMMIT` 失敗仍會重複寄信。
  - `B`（優）：資料庫唯一約束在寫入層原子攔截重複 Webhook、`SKIP LOCKED` 讓 6 台 worker 並行認領互不阻塞、極短交易把連線池與鎖持有時間壓在毫秒級；（缺）：狀態機多了一個中介態 `'processing'`，必須實作逾時心跳或重試回收機制，且外部寄信 API 端仍須帶冪等鍵（idempotency key）防重送。
  - `C`（優）：開發最快；（缺）：兩次幾乎同時到達的重送 Webhook 都會讀到 `COUNT(*) = 0` 而雙重寫入，且 6 台 worker 會重複認領同一筆事件。
  - `D`（優）：無；（缺）：`SERIALIZABLE` 無法替代 `SKIP LOCKED` 的非阻塞認領，高並行下會產生大量 serialization failure 迫使不斷重試，且不解決長交易佔用連線池問題。
- **對應教材**：[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)、[backend 1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)

### C06（複合陷阱：整數除法 + 零分母 + 軟刪除與歷史快照 + 需求模糊）——紙頁書店與雲課堂綜合上線審查

- **領域**：紙頁書店（`bookstore`）
- **疊加考點**：整數除法截斷 × 分母為零 × 宣告落空 × 歷史價格快照與事後退款對帳
- **出題視角**：`diagnose-plan`
- **商業需求與前提**：一位同事在 SQLite 上線了「各分類退款率大於 10% 的預警報表」，SQL 如下，測試環境 20 筆資料沒報錯，上線第一週回傳 0 筆，但客服明明收到大量退款客訴：

```sql
SELECT b.category_id,
       COUNT(CASE WHEN o.status = 'refunded' THEN 1 END) / COUNT(*) AS refund_rate
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
JOIN books b ON b.book_id = oi.book_id
GROUP BY b.category_id
HAVING COUNT(CASE WHEN o.status = 'refunded' THEN 1 END) / COUNT(*) > 0.1;
```

這段查詢同時藏了哪些缺陷，哪個診斷清單最完整？

- **選項**：
  - `A`：只有一個問題——`HAVING` 不能寫計算式，改用別名 `HAVING refund_rate > 0.1` 就會回傳正確結果。
  - `B`：同時存在四個缺陷——（1）SQLite 整數除以整數會無條件捨去小數，只要退款率低於 100%，商永遠是 `0`，不可能大於 `0.1`（應乘以 `1.0` 或改用交叉相乘 `refund_cnt * 10 > total_cnt`）；（2）`LEFT JOIN order_items` 後面緊接 `JOIN books` 已撤銷外連接保護，屬宣告落空；（3）以 `order_items` 粒度做 `COUNT(*)` 計算的是「被退款的訂單明細行數比例」而非「退款金額比例」或「退款訂單筆數比例」，一筆買 5 本書的訂單權重被放大 5 倍；（4）未過濾 `pending` 與 `cancelled` 訂單，把從未付款的訂單灌進分母稀釋了退款率。
  - `C`：只要把 `LEFT JOIN` 改成 `RIGHT JOIN`，並加上 `DISTINCT` 就修好了。
  - `D`：SQLite 不支援 `CASE WHEN` 放進 `COUNT()`，必須拆成兩張暫存表。
- **推薦選擇**：`B`
- **各選項優劣分析**：
  - `A`（優）：無；（缺）：就算改用別名，`refund_rate` 仍是整數除法算出來的 `0`，且完全沒發現分母混入未付款訂單與粒度失真。
  - `B`（優）：一次點出語法層（整數除法）、宣告層（被後段內連接撤銷的 `LEFT JOIN`）、模型層（明細行數 vs 訂單數 vs 金額粒度）與需求層（分母應只算已完成付款的訂單）四層缺陷，直接對應 `SQL.0` 與 `SQL.13` 的檢查方法；（缺）：修復前須回頭跟營運主管確認退款率分子分母的業務定義（按筆數、本數還是金額）。
  - `C`（優）：無；（缺）：改方向與加 `DISTINCT` 完全沒處理整數除法、粒度與分母定義。
  - `D`（優）：無；（缺）：SQLite 與標準 SQL 皆完整支援 `COUNT(CASE WHEN ... THEN 1 END)`（且 SQLite 3.30+ 與 PostgreSQL 還支援更簡潔的 `COUNT(*) FILTER (WHERE ...)`）。
- **對應教材**：[SQL.0 一段查詢從需求到上線的決定：追問需求、設定判斷標準、選寫法、補前提、量代價、對邊界與交付](/backend/01-database/sql/decisions-from-requirement-to-shipping/)、[SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)、[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)、[SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)

## 練習回饋驅動 SQL 教材改進的閉環機制

本練習網站不只是單向測驗工具，也是檢驗[SQL：這個語言為什麼長這樣](/backend/01-database/sql/)可讀性與完整性的探針。學習者在練習過程中遇到的不理解處，依下列分類記錄並回寫到教材。

### 回饋分類與對應改進落點

| 困惑類型     | 具體表現                                                                                    | 對應到 `content/backend/01-database/sql/` 的處置                                                      |
| ------------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 基礎語法缺口 | 看選項時不認得某個語法關鍵字或子句作用（例如 `COALESCE`、`CASE WHEN`、`BETWEEN`、半開區間） | 評估在 `sql/` 補基礎前置文章，或擴充階段一的說明與前置導讀                                            |
| 論證斷層     | 看了題目解析並點進對應 `SQL.x` 文章後，仍推不出為何某選項會出錯或變慢                       | 在該篇 `SQL.x` 補齊跳過的中間步驟、改用更直覺的資料反例，或補一張對照表                               |
| 術語障礙     | 題目或文章裡出現的名詞讀不懂（例如覆蓋索引、sargable、半連接、三值邏輯、排他鎖）            | 檢查 `sql/knowledge-cards/` 是否缺卡或定義過於抽象，補卡或補寫生活化對照例子                          |
| 現實情境缺口 | 練習時想到新的商業邊界（例如退貨部分退款、多幣別匯率、軟刪除與唯一約束衝突）                | 新增進本題庫下一版題目，並同步評估是否寫入 `sql/_index.md` 或 `01-database/_index.md` 的 `## Backlog` |

### 練習回饋紀錄表（開始練習後逐筆填寫）

| 日期               | 題號 | 困惑類型 | 不理解的具體描述 | 預計改進位置 | 狀態 |
| ------------------ | ---- | -------- | ---------------- | ------------ | ---- |
| （開始練習後填寫） | —    | —        | —                | —            | 待填 |

## 未來練習網站的功能與資料結構規格（程式實作前置）

等這份題庫與情境設計確認後，再進入網站實作。實作階段預設採取**純靜態前端網站**（可直接部署在 GitHub Pages，無需後端伺服器），架構規劃如下：

### 核心功能範圍

1. **雙練習模式切換（學習模式 vs 盲測鑑別模式）**：
   - **分階段學習模式**：依階段一到階段六循序解鎖，顯示能力節點與對應教材提示，適合初學建立體系。
   - **盲測鑑別模式**：隱藏階段名稱與考點標籤，跨階段、跨三大商業領域隨機組卷（例如每次抽 10 題，混入 2 題跨概念複合陷阱題），專門檢驗觀念在無提示下的真實遷移能力。
2. **反記憶隨機抽題與選項洗牌**：
   - 每個能力節點優先抽取「未做過 → 曾答錯 → 不同商業領域 → 不同出題視角 → 最久未作答」的變體題，連續兩輪不重複抽同一個 `variantId`。
   - 題目渲染時以 Fisher-Yates 洗牌重排選項顯示位置，進度記錄綁定選項原始 `key` 而非畫面位置。
   - 能力節點進度條區分「尚未練習」「初通（單領域答對）」「待鞏固（盲測或前提翻轉曾答錯）」「已掌握（達跨領域＋多視角＋盲測三條件）」。
3. **Schema 抽屜與邊界資料預覽**：作答時依目前題目的 `domain` 與 `unlockedTables` 動態展開對應商業網站的表結構與邊界範例資料，不用來回切換分頁。
4. **作答與全選項優劣展開**：點選選項後顯示該選項與其餘選項在「正常資料」與「邊界反例」上的輸出對照，以及優點、缺點、成立前提、失效條件四欄解析。
5. **選配的瀏覽器端即時執行（第二期擴充）**：後續可接入 SQLite WASM（`sql.js`），依目前 `domain` 載入對應的記憶體資料庫，讓學習者直接在網頁內跑四個選項、自行插入反例資料並觀察 `EXPLAIN QUERY PLAN`。
6. **一鍵彙出困惑筆記**：在每一題下方提供「記下我不懂的地方」表單，自動帶入 `conceptId`、`variantId` 與 `domain`，支援一鍵複製成 Markdown 表格列，直接貼回本檔的〈練習回饋紀錄表〉進行教材改進。

### 題目資料檔結構草案（JSON）

```json
{
  "conceptId": "S2-03",
  "variantId": "S2-03-bookstore-01",
  "domain": "bookstore",
  "stage": 2,
  "perspective": "choose-query",
  "difficulty": 2,
  "premiseFlip": false,
  "traps": ["outer-join-where-nullifies-protection", "partial-null-or-miss"],
  "title": "所有顧客與他們 2026 年 3 月的訂單：ON 與 WHERE 的職責分岔",
  "unlockedTables": ["customers", "orders"],
  "businessRequirement": "報表要列出每一位顧客，旁邊顯示他在 2026 年 3 月的已付款訂單總額；3 月沒有付款訂單的顧客仍要顯示 0。",
  "assumptions": {
    "engine": "SQLite 3.51 / PostgreSQL 18",
    "scale": "10 萬顧客、100 萬訂單",
    "indexes": ["orders(customer_id, ordered_at)"]
  },
  "options": [
    {
      "key": "opt_where_filter",
      "sql": "...",
      "normalResult": "回傳 3 月有付款的顧客",
      "edgeCaseResult": "2 月有下單、3 月沒下單的顧客整列消失",
      "pros": [],
      "cons": [],
      "validWhen": "只關心 3 月有付款顧客時（此時應改寫為 INNER JOIN）",
      "failsWhen": "需要保留 3 月未付款顧客時"
    }
  ],
  "recommendedKeys": ["opt_on_filter"],
  "alternativeNote": "同一查詢需同時計算多個月份欄位時可改選 conditional aggregation",
  "relatedDocs": [
    "/backend/01-database/sql/on-describes-where-filters/"
  ]
}
```

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                             | 類型 | 前置條件           | 規模 |
| ---------------------------------------------------------------------------------------------------------------- | ---- | ------------------ | ---- |
| 審閱三大領域 Schema、30 節點 × 3 變體規劃與 6 題複合陷阱題，調整難度梯度與題池比例                               | 規格 | 本檔審閱完成       | 小   |
| 補齊領域乙（雲課堂）與領域丙（捷配物流）共 60 題變體的完整四選項 SQL、反例輸出與優劣解析，並擴充複合陷阱題池     | 內容 | 規格定案           | 大   |
| 建立三套領域的可重現 SQLite 基準測試資料腳本（含全部邊界反例列）並對每題選項跑自動化驗證，確保輸出描述與實跑一致 | 實作 | 題庫 JSON 定案     | 中   |
| 實作純靜態選擇題練習網站（學習／盲測雙模式、反記憶抽題、選項洗牌、跨領域熟練度追蹤、Schema 抽屜與困惑匯出）      | 實作 | 題庫 JSON 定案     | 中   |
| 決定網站與 Hugo 的整合落點（獨立 `static/` 頁面＋`sql/` 列表入口，或 Hugo shortcode 內嵌）                       | 規格 | 無                 | 小   |
| 第二期擴充：接入 SQLite WASM 依領域載入記憶體資料庫，支援網頁內實跑選項與 `EXPLAIN QUERY PLAN`                   | 實作 | 第一期練習網站完成 | 中   |
