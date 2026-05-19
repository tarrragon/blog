---
title: "MySQL 5.7 → 8.0 Major Version Upgrade：character set / authentication / atomic DDL 三條 paradigm 同時換軌"
date: 2026-05-19
description: "MySQL 5.7 → 8.0 三條 default 同時改：charset utf8 → utf8mb4、auth plugin native_password → caching_sha2_password、DDL non-atomic → atomic。本文走 Type E paradigm shift 結構、6 維 audit、4-phase upgrade、5 production 踩雷、何時不要升級。"
weight: 25
tags: ["backend", "database", "mysql", "vendor", "migration", "type-e", "paradigm-shift", "major-upgrade"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) 內 version upgrade migration playbook、走 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type E paradigm shift 結構。

5.7 → 8.0 看起來是 *minor bump*（從 5.7.40 升到 8.0.36）、但不是。Oracle 把這個 release boundary 當成 *清庫存的機會* — 同時推出 3 個 *behavioral paradigm shift*：

| Paradigm              | 5.7 default                   | 8.0 default                   | 影響                                      |
| --------------------- | ----------------------------- | ----------------------------- | ----------------------------------------- |
| Character set         | latin1 / utf8（=utf8mb3）     | utf8mb4                       | string column 儲存 + emoji / 4-byte UTF-8 |
| Authentication plugin | mysql_native_password         | caching_sha2_password         | client / library 需要支援新 plugin        |
| DDL atomicity         | Non-atomic（crash 留 orphan） | Atomic（crash recovery 乾淨） | 開發信心、crash recovery 行為             |

對應 *任意一個* paradigm 升級失誤、production 都會 down。三條同時換、必須 *三條都規劃*。

這條 upgrade 比 [PostgreSQL major-version-upgrade](/backend/01-database/vendors/postgresql/major-version-upgrade/) 工作量大 — PG major upgrade 主要是 *pg_upgrade* 工具流程、MySQL 是 *behavioral compatibility audit + ecosystem 全 review*。

## 為什麼是 Type E（不是 minor upgrade）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#寫前的-diff-dimension-audit)：

| 維度        | 評          | 說明                                                             |
| ----------- | ----------- | ---------------------------------------------------------------- |
| Schema      | Medium      | SQL 一致、reserved keyword 新增、collation 預設變                |
| Operational | Medium-High | binary upgrade flow 簡單、但 ecosystem 工具兼容性 audit 工作量大 |
| Paradigm    | High        | 3 條 default paradigm shift（charset / auth / atomic DDL）       |
| Components  | Low         | 同 MySQL 引擎、不引新 component                                  |
| App change  | Medium-High | client library / driver / connection string 都可能要改           |
| Topology    | Low         | 部署 topology 不變                                               |

Paradigm = High + App change = Medium-High → **Type E paradigm shift**。

雖然是 *同一個 vendor 的 major version*、實際的 *application 行為差異* 跨越多個 paradigm、6 type 框架仍適用、結構走 partial migration 收斂。

## 4-phase upgrade

### Phase 1：Pre-check audit

8.0 升級前用 *MySQL Shell upgrade checker* + 手動 audit：

```bash
mysqlsh root@5.7-primary.example.com -- util check-for-server-upgrade
```

Upgrade checker 報告：

- *Reserved keyword* 衝突（5.7 不是 keyword 但 8.0 是、例如 `WINDOW` / `RANK` / `LATERAL`）
- 舊 character set / collation 使用點（latin1 / utf8mb3）
- Deprecated feature 使用（GROUP BY 隱含 ORDER BY 等）
- Datatype 變動（DATETIME 行為微差）

手動 audit：

- Application driver / library 版本是否支援 caching_sha2_password
- Connection string 內 `default-authentication-plugin` 設定
- ORM / framework 是否假設 utf8 而非 utf8mb4

完成標準：寫出 *blocker list*（必須在升級前修） + *warning list*（可在升級後處理）。

### Phase 2：Shadow upgrade — Replica 升 8.0

從 *non-critical replica* 升起。先升一個 replica、跑 production traffic（read-only）2-4 週：

```bash
# 1. Stop replica
systemctl stop mysql

# 2. Backup（XtraBackup）
xtrabackup --backup --target-dir=/backup/pre-upgrade

# 3. Install MySQL 8.0 binary（apt / yum 升級）
apt-get install mysql-server-8.0

# 4. 啟動 8.0、自動 upgrade data dictionary
systemctl start mysql

# 5. 8.0 自動跑 server-upgrade（8.0.16+ 內建、mysql_upgrade utility 已 deprecated）
# 若 5.7 升 8.0.16 之前 server、才需要手動跑 mysql_upgrade -u root -p

# 6. 重新 attach 為 5.7 primary 的 replica（8.0 replica 可 attach 5.7 primary）
CHANGE MASTER TO MASTER_AUTO_POSITION=1;
START SLAVE;
```

跑 production read traffic 觀察：

- Query result 是否跟 5.7 一致（特別 character set 相關）
- Replication lag 是否在 baseline 範圍
- 8.0-specific feature 是否需要（hash join / window function 等）

### Phase 3：Promote 8.0 為 primary

確認 shadow replica 穩定後：

```bash
# 1. 升其他 replica 到 8.0
# （per-replica 跑 Phase 2 流程）

# 2. Application application 改用 8.0-compatible driver
# 把 connection string 加 default-authentication-plugin=caching_sha2_password
# 或仍用 mysql_native_password（user 端設定）

# 3. Failover：promote 8.0 replica 為 primary
# 用 Orchestrator / 自管 failover 流程

# 4. 5.7 primary 變成 8.0 replica、升 5.7 → 8.0
```

完成標準：所有 server 都是 8.0、application 連 8.0 endpoint 無 error。

### Phase 4：Decommission 5.7 + 套用 8.0 paradigm

完成 binary upgrade 不是真正完成 — 還要逐步遷移 paradigm：

- **Character set 升級**：歷史 latin1 / utf8 table 改 utf8mb4

    ```sql
    ALTER TABLE orders CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
    ```

    每張 table 走 gh-ost / pt-osc（避免 production 阻塞）
- **Authentication 升級**：逐步把 user 從 `mysql_native_password` 改 `caching_sha2_password`

    ```sql
    ALTER USER 'app'@'%' IDENTIFIED WITH caching_sha2_password BY 'new_password';
    ```

    需確認 application driver 已支援新 plugin（多數 modern driver OK、legacy 可能要升級）
- **Reserved keyword 處理**：column / table 名稱跟新 reserved word 衝突的、改名

    ```sql
    ALTER TABLE events RENAME COLUMN window TO event_window;
    ```

多數 org 在 Phase 3 停留更久 — paradigm 升級不是一次 big bang、是漸進。

## 5 個 Production 踩雷

### 1. Authentication plugin — Application 突然連不上

升 8.0 後 *new user* 預設用 caching_sha2_password、舊 application driver（< 5 年版本）不支援、connect error: `Authentication plugin 'caching_sha2_password' cannot be loaded`。

修法：

- *先升 driver*：每個 application 升級 mysql-connector-* 到支援 caching_sha2 的版本（多數 modern release 已支援）
- 短期 workaround：用 `mysql_native_password`（new user 顯式 create with `IDENTIFIED WITH mysql_native_password`）
- 設 `default_authentication_plugin=mysql_native_password`、強制保留舊 default

### 2. Character set 4-byte UTF-8 — Emoji 進不去

5.7 latin1 / utf8（=utf8mb3）column 升 8.0 後 *仍是 utf8mb3*、不會自動升 utf8mb4。Application 寫入 emoji（4-byte UTF-8）會被 *truncate / 拒絕*。

修法：

- *逐 table CONVERT*：gh-ost / pt-osc 跑 `ALTER TABLE ... CONVERT TO CHARACTER SET utf8mb4`
- 新建 table 預設用 utf8mb4（`character_set_server=utf8mb4` 設定）
- Application 連線 charset 設定一致（`character_set_client / connection / results`）

### 3. Reserved keyword — Application query 突然 syntax error

5.7 跑得好的 query：

```sql
SELECT window, rank FROM events;
```

8.0 報錯：`window` 跟 `rank` 都是 reserved keyword、必須 backtick：

```sql
SELECT `window`, `rank` FROM events;
```

修法：

- Phase 1 upgrade checker 已抓出來、Application code review 改 SQL
- 推薦 *predefer table / column 名 backtick* policy（一律加 backtick、避免未來 reserved word 衝突）
- ORM 多數會自動 backtick、raw SQL 容易踩

### 4. Group Replication / 新 feature 開了就不能 rollback

8.0 升級後 *誘惑使用 8.0-only feature*：

- Group Replication（5.7 也有但 8.0 更穩）
- Resource Group（5.7 沒有）
- Histograms（5.7 沒有）
- CTE / window function（5.7 沒有）

一旦 application 用了這些 feature、不能 rollback 5.7（feature 不存在、query 失敗）。

修法：

- *Phase 1-3 期間禁用 8.0-only feature*、保留 rollback option
- *Phase 4 完成* 且穩定運作 30+ 天後、才開始 evaluate 8.0-only feature
- 加 8.0-only feature 時 *明確記錄不可 rollback*

### 5. Collation default 變動 — Sort order 跟 unique 行為改變

5.7 utf8mb4 預設 collation = `utf8mb4_general_ci`、8.0 預設 = `utf8mb4_0900_ai_ci`。兩者排序行為不一致：

- `utf8mb4_general_ci`：簡化 collation、不嚴格遵循 Unicode
- `utf8mb4_0900_ai_ci`：Unicode 9.0 compliance、accent-insensitive

對 *已存在的 table*、collation 不會被 8.0 升級改變（保留 5.7 設定）。但 *新建 table* 預設用 0900_ai_ci、UNION / JOIN 跨不同 collation 的 column 可能 error: `Illegal mix of collations`。

修法：

- 統一 collation：要麼 *所有 table 改 0900_ai_ci*、要麼 *所有 table 保留 general_ci*
- Schema migration 走 OSC 工具
- Application 內 sort-dependent logic（leaderboard / search ranking）要驗證新 collation 結果

## Capability gap：5.7 有但 8.0 沒有

少數 8.0 *拿走* 的能力：

- **Query Cache**：5.7 內建（但已 deprecated）、8.0 *完全移除*。Query cache 在高並發場景 actually slowing down、移除是好事
- **InnoDB MEMORY engine**：5.7 部分支援、8.0 限制更多
- **Some MyISAM optimizations**：8.0 強制 InnoDB-first、MyISAM-specific 工作流 broken

對 Query Cache user：升 8.0 前評估是否依賴、考慮改 application-side cache（Redis）。

## 容量與成本對照

| 項目                     | 5.7                    | 8.0                                  |
| ------------------------ | ---------------------- | ------------------------------------ |
| Cost                     | Free (CE) / Enterprise | Free (CE) / Enterprise               |
| 升級 hosts × 時間        | -                      | per-instance ~30 分鐘 binary upgrade |
| Application 改動         | -                      | driver upgrade + SQL review          |
| Character set conversion | -                      | per-table OSC、大表小時級            |
| Ops headcount            | -                      | 1-2 個 DBA × 2-4 週                  |
| 對 production 影響       | -                      | Phase 2-3 漸進升級、無大 downtime    |

5.7 → 8.0 upgrade 整體成本是 *1-2 個 FTE 月* 規模。對中型 deployment（100+ DB）可能更多。

## 何時不升

- **App 用 Query Cache 重度**：8.0 沒了、要 application 改造
- **Old driver 不能升**：legacy enterprise application 用 10 年前 driver、driver vendor 已倒、無法升 8.0-compatible
- **Compliance freeze**：某些金融 / 醫療場景 freeze technology 多年、升級需要重 audit + recertification
- **5.7 已 EOL（2023-10）後仍堅持不升**：security risk 高、應該 *優先升*

## 跟 PostgreSQL Major Version Upgrade 對比

| 維度           | MySQL 5.7 → 8.0                                                       | PostgreSQL N → N+1                  |
| -------------- | --------------------------------------------------------------------- | ----------------------------------- |
| Tool           | binary upgrade + 自動 server-upgrade（8.0.16+；舊版用 mysql_upgrade） | pg_upgrade（in-place）              |
| Downtime       | < 5 分鐘 per instance（binary + DD upgrade）                          | < 1 分鐘 per instance（pg_upgrade） |
| Paradigm shift | 3 條（charset / auth / atomic DDL）                                   | 一般 0-1 條（PG major 多保 compat） |
| App 必須改     | 多（driver + query）                                                  | 少（多數 query 兼容）               |
| Risk           | 高（paradigm 多）                                                     | 中-低                               |
| Rollback       | 不可（一旦 atomic DDL data 寫入、5.7 不認）                           | 不可（pg_upgrade 不可逆）           |

PG major upgrade 比 MySQL 簡單。MySQL 5.7 → 8.0 是 *特例* — Oracle 把多年 deprecated 一次清。8.0 → 8.4 / 9.x 預期更平順。

## 跟其他模組整合

### 跟 Replication topology

8.0 replica 可 attach 5.7 primary（向下兼容）、但 5.7 replica *不能 attach 8.0 primary*（向上不兼容）。Upgrade 順序必須 *replica 先升、primary 後升*。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 InnoDB Tuning

8.0 InnoDB 改寫了 redo log（atomic、可動態調整）、`innodb_log_file_size` 升級後可以 *online 改*、不必停機。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 Modern SQL Features

8.0 補 CTE / window / JSON_TABLE / hash join — 是 *為什麼要升 8.0* 的 driver。詳見 [Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)。

### 跟 Group Replication

GR 在 5.7 有、但 8.0 才成熟。Group Replication 的 *MySQL Shell + Router* 整套 stack 主要在 8.0 才完整。詳見 [Group Replication](/backend/01-database/vendors/mysql/group-replication/)。

### 跟 Aurora / PlanetScale 等 managed

從 5.7 升 8.0 是個好時機 *同時評估* 是否要遷 Aurora / PlanetScale — 既然要做 paradigm shift、不如一次到位。詳見 [migrate-to-aurora](/backend/01-database/vendors/mysql/migrate-to-aurora/) / [migrate-to-planetscale](/backend/01-database/vendors/mysql/migrate-to-planetscale/)。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（升級順序 replica-first）
- [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)（升 8.0 的主要 driver）
- [MySQL Group Replication](/backend/01-database/vendors/mysql/group-replication/)（8.0 成熟）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（8.0 redo log 改寫）
- [migrate-to-aurora](/backend/01-database/vendors/mysql/migrate-to-aurora/) / [migrate-to-planetscale](/backend/01-database/vendors/mysql/migrate-to-planetscale/)
- [PostgreSQL Major Version Upgrade](/backend/01-database/vendors/postgresql/major-version-upgrade/)（PG sibling）
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type E paradigm shift）
- 官方：[MySQL 8.0 Upgrade Guide](https://dev.mysql.com/doc/refman/8.0/en/upgrading.html)
