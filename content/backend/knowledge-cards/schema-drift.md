---
title: "Schema Drift（資料庫 schema 跟 migration 歷史的漂移）"
date: 2026-11-21
description: "正式環境有人手動加過 index 或欄位、新環境照 migration 建出來的 schema 跟正式環境對不上，或 migration 只在某個環境失敗時，查資料庫 schema 漂移是什麼、各工具怎麼偵測"
weight: 510
tags: ["backend", "database", "schema migration", "drift", "knowledge-card"]
---

Schema Drift（資料庫 schema 跟 migration 歷史的漂移）指資料庫的實際 schema 跟依 [Schema Migration](/backend/knowledge-cards/schema-migration/) 歷史推出來的 schema 不一致：有人直接在正式環境加了 index 或欄位、hotfix 改了型別，或已經套用的 migration 檔案事後被修改。歷史表只記錄套用過哪幾份 migration，不記錄資料庫實際長什麼樣，所以漂移不會讓 migration 工具報錯，要另外比對才看得出來。這張卡的所指限定在資料庫 schema；站上的 schema drift 另外指三件不同的事：結構化 log 與 telemetry 事件的欄位隨版本改變（欄位怎麼設計在 [Log Schema](/backend/knowledge-cards/log-schema/) 卡）、CDC 串流收到的上游表結構改變（CDC 的機制在 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 卡），以及兩個部署環境之間的設定不一致。

## 跟其他概念的關係

漂移的來源是 migration 歷史以外的變更路徑，所以它跟 migration 怎麼套用有關：歷史表是工具判斷「還要跑哪幾份」的依據，[Expand-Contract](/backend/knowledge-cards/expand-contract/) 拆出來的每一步都假設前一步留下的 schema 跟歷史一致。完整性檢查（Flyway 的 checksum、Atlas 的 `atlas.sum`）抓的是 migration 檔案被改過，跟漂移是兩個方向：檔案沒動而資料庫被改，checksum 照樣通過。

## 可觀察訊號與例子

漂移的訊號是 migration 只在某個環境失敗（正式環境已經有手動加的那個 index，同名的 `CREATE INDEX` 撞名），或照 migration 新建的環境少了正式環境上的 index，查詢計畫因此不同。實測兩個工具：Alembic 的 `alembic check` 把手動建的 index 報成 `remove_index`；Prisma ORM 7.10.1 的 `migrate dev` 印出 `Drift detected` 並要求 reset 資料庫，而正式環境用的 `migrate deploy` 與 `migrate status` 都回報正常。Django 的 `makemigrations --check` 依文件只比對 model 與 migration 檔，看不到資料庫的現狀。各工具比對的兩方寫在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/)〈schema 漂移的偵測〉。

## 判斷條件與後果

服務的 schema 只經由 migration 改動、而且部署流程定期比對資料庫與 migration 重建出的 schema 時，漂移在下一次比對就被發現，處置是把手動的變更補寫成一份 migration（內容寫成重跑也成立的形式），讓歷史追上現狀。沒有比對時，漂移留到某一次 migration 在某個環境失敗才浮現，或一直留著，讓測試與正式環境的查詢計畫不一樣。偵測工具的兩方要看清楚：比對 model 與資料庫的（`alembic check`、Atlas 宣告式的 `schema apply`）抓得到，比對 model 與 migration 檔的（Django 的 `makemigrations --check`）抓不到，正式環境用的套用指令（Prisma 的 `migrate deploy`）不比對。
