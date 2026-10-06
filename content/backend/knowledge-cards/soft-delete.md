---
title: "Soft Delete（軟刪除）"
date: 2026-10-06
description: "資料表有 deleted_at 欄位、ORM 的刪除改成 UPDATE，或刪掉的資料再建一次卻撞唯一約束、報表數字和頁面對不上時，查軟刪除的過濾條件由誰加、哪些路徑沒有加"
weight: 459
tags: ["backend", "database", "orm", "knowledge-card"]
---

軟刪除（soft delete）是「刪除」時把那一列留在表裡，在列上記一個刪除標記（多半是 `deleted_at` 時間欄位），之後的查詢一律加上「沒有刪除標記」的條件。被刪的資料因此還在表裡，可以復原、可以稽核，那一列的識別碼也繼續被佔著、不會發給別人，而對使用者來說它已經不存在。這個「一律加上條件」通常由 [ORM](/backend/knowledge-cards/orm/) 代勞，所以軟刪除的行為大半落在 ORM 的慣例裡；單一資料庫裡的軟刪除標記，要傳到副本、離線裝置或下游系統時就是 [Tombstone](/backend/knowledge-cards/tombstone/)；它和資料保存期限的關係見 [Retention](/backend/knowledge-cards/retention/)，和永久刪除的分工見 [資料生命週期](/backend/knowledge-cards/data-lifecycle/)。

## 概念位置

```sql
-- 刪除：把標記寫上去
UPDATE customers SET deleted_at = now() WHERE id = 3 AND deleted_at IS NULL;

-- 之後的每一個查詢都要帶這個條件
SELECT * FROM customers WHERE email = 'yawen@example.com' AND deleted_at IS NULL;
```

各語言的 [ORM](/backend/knowledge-cards/orm/) 用不同的方式加上那個條件：Laravel 的 model 使用 `SoftDeletes` trait 之後，查詢自動帶 `whereNull('deleted_at')`，`withTrashed()` 連同已刪除的一起查、`forceDelete()` 永久刪除、`restore()` 復原；GORM 的 model 帶 `gorm.DeletedAt` 型別的欄位（嵌入 `gorm.Model` 就有）時同樣自動加條件，`Unscoped()` 取消它（實測見 [10.6 GORM 的 gorm.Model、軟刪除與 Save：慣例欄位加上的查詢條件與整列寫回](/go/10-database-access/gorm-model-and-soft-delete/)）；Django ORM 與 SQLAlchemy 沒有內建，要自己加條件（Django 改寫 model 預設的查詢入口 `Manager`，SQLAlchemy 在查詢上加篩選），或用第三方套件。Django 改寫預設 `Manager` 之後，ORM 自己仍有一條路徑不經過它：從訂單存取所屬顧客（`order.customer`）這種正向關聯走的是 `_base_manager`，讀得到已刪除的顧客。

條件由 ORM 加，所以不經過那個 ORM 的路徑都看得到已刪除的資料：手寫的 SQL（GORM 的 `Raw`、Laravel 的 `DB::select`）、報表與資料倉儲的匯出、共用同一個資料庫的其他服務、直接連進資料庫查問題的人。刪除前就存好的讀取結果也一樣：快取裡的那一筆與搜尋索引裡的文件不會因為加了標記就消失，要在刪除時一併清掉（見 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/)、[Search Index](/backend/knowledge-cards/search-index/)）。

## 可觀察訊號與例子

- **刪掉再建立同一筆資料撞唯一約束**：顧客刪除帳號之後用同一個 email 重新註冊，`email` 上的唯一約束仍然看得到那一列，回報重複（PostgreSQL 的 SQLSTATE `23505`）。PostgreSQL 與 SQLite 的處理方式是只對未刪除的列建唯一索引（部分索引（partial index），`CREATE UNIQUE INDEX ... ON customers (email) WHERE deleted_at IS NULL`）；MySQL 沒有部分索引，常見做法有兩種：加一個未刪除時等於 email、刪除後為 NULL 的產生欄位（generated column），在它上面建唯一索引，因為唯一索引允許多個 NULL；或讓 `deleted_at` 用 0 代表未刪除（不用 NULL），再建 `(email, deleted_at)` 的複合唯一索引。換成部分索引之後，`INSERT ... ON CONFLICT (email)` 要寫出同樣的 `WHERE deleted_at IS NULL` 才對得上那個索引，否則 PostgreSQL 回報找不到相符的約束（`42P10`）。應用程式端的唯一性檢查也要排除已刪除的列（Laravel 的驗證規則寫 `Rule::unique('customers')->withoutTrashed()`）。
- **外鍵不會因為軟刪除而動作**：軟刪除是 `UPDATE`，外鍵的 `ON DELETE CASCADE` 與「還有子表資料就不准刪」的檢查都不會被觸發。顧客被軟刪除之後，那位顧客的訂單仍然指著那一列；訂單列表用 ORM 載入顧客時，Laravel 拿到的是 null、GORM 是零值的 struct，Django 的正向關聯則讀到已刪除的顧客。之後要永久刪除那位顧客，外鍵才擋下來（`23503`）。
- **計數對不上**：頁面上的顧客數由 ORM 算（帶條件），報表直接寫 SQL 算（不帶條件），兩個數字差的就是已刪除的那些。
- **刪除請求沒有刪掉個資**：使用者依個資法規要求刪除時，軟刪除只加了標記，資料原封不動，要另外做永久刪除或匿名化（見 [PII](/backend/knowledge-cards/pii/)）。
- **增量同步收不到刪除**：依 `updated_at` 取「上次之後改過的列」的同步，要靠軟刪除同時更新 `updated_at` 才看得到刪除。Laravel 的 `SoftDeletes` 會一併更新，GORM 的軟刪除只寫 `deleted_at`，那種同步永遠看不到 GORM 刪掉的列；同步要另外取 `deleted_at` 晚於上次同步的列，或改用資料庫的變更紀錄（見 [Change Data Capture](/backend/knowledge-cards/change-data-capture/)）。

## 設計責任

用軟刪除之前先決定它要解決的是哪一件事。保留稽核紀錄、誤刪後能復原、表示業務狀態這三個目的各有替代做法，不會帶來唯一約束衝突、手寫 SQL 讀到已刪除列、計數不一致與增量同步收不到刪除這些問題；讓識別碼不被重用則是軟刪除本身要解的問題：

- **保留稽核紀錄**：把刪除事件寫進稽核表、原資料照常刪除（見 [Audit Log](/backend/knowledge-cards/audit-log/)），或整個領域改用事件記錄狀態（見 [Event Sourcing](/backend/knowledge-cards/event-sourcing/)）。
- **誤刪後能復原**：刪除時把那一列搬到封存表（例如 `customers_archive`），復原時搬回來；主表上沒有已刪除的列，唯一約束、手寫 SQL 與計數都不受影響，代價是子表的資料要一起處理。
- **帳號停用、訂單取消這類業務狀態**：它們本來就是業務上的一個狀態，用狀態欄位表示，查詢條件寫在業務邏輯裡，不必套用刪除的慣例。
- **讓識別碼不被重用、讓關聯資料不失去參照**：這是軟刪除最直接的理由，例如短網址被刪除之後，短碼要一直被佔著，不能發給別人（見 [0.24 短網址服務的實作：短碼生成、對照表儲存、轉址快取與點擊紀錄](/backend/00-service-selection/url-shortener-implementation/)〈對照表：儲存選型、欄位與分片〉）。

決定用軟刪除時，同時決定四件事：

- **刪除之後同一個值能不能再用**：能的話（顧客刪除帳號後可以用同一個 email 重新註冊），唯一約束改成只涵蓋未刪除的列；不能的話（短碼），保留涵蓋全表的唯一約束。
- **不經過 ORM 的讀取怎麼排除已刪除的列**：手寫 SQL 自己加條件，或在資料庫端提供只含未刪除列的 view、對報表帳號設 [Row-Level Security](/backend/knowledge-cards/row-level-security/) 政策；其他服務與直接連進資料庫的人，只有資料庫端的做法擋得到。
- **子表的資料在父列被軟刪除時怎麼處理**：一起軟刪除、照常保留並在畫面上標示，或禁止刪除還有子表資料的父列。
- **已刪除的資料保留多久之後永久刪除**：到期時子表若因為法規（例如帳務紀錄）要保留，外鍵會擋下永久刪除，這時改成把個資欄位匿名化（清空姓名、email），只留下那一列與它的主鍵。
