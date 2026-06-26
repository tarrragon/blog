---
title: "資料庫大版本升級"
date: 2026-06-26
description: "MySQL 5.7→8.0、PostgreSQL 13→16 等大版本升級的相容性評估、備份保險、平行驗證、切換策略與升級後監控"
weight: 4
tags: ["infra", "upgrade", "database", "mysql", "postgresql"]
---

資料庫大版本升級是所有升級類型中風險最高的一種，因為資料庫承載的是不可重建的狀態。Runtime 升級（PHP 5.6→8.x）改壞了可以切回舊版本重新部署（切換 PHP 版本即可回退）；平台遷移（共享主機→雲端）改壞了可以把 DNS 切回去（TTL 期間內生效）。資料庫升級改壞了，回退手段是從備份還原——而還原需要時間，還原期間服務不可用，且還原點之後的寫入會遺失。這個不對稱決定了資料庫升級的操作模式：每一步都需要驗證通過才進下一步，且每一步都有明確的回退路徑。

## 升級前的相容性評估

大版本升級不只是換一個二進位檔——新版本可能改變 SQL 行為、儲存格式、認證方式與預設值。在動任何生產資源之前，先在本地或測試環境把相容性問題找出來。

### MySQL 5.7 → 8.0 的常見破壞性變更

| 變更項                         | 影響                                                    | 檢查方式                                                           |
| ------------------------------ | ------------------------------------------------------- | ------------------------------------------------------------------ |
| `GROUP BY` 隱式排序移除        | 依賴 `GROUP BY` 順序的查詢結果可能改變                  | 搜尋沒有 `ORDER BY` 的 `GROUP BY` 查詢                             |
| 預設字元集 utf8 → utf8mb4      | 欄位長度與索引大小計算改變，索引可能超過限制            | 檢查 `VARCHAR(255)` + 唯一索引的欄位                               |
| 認證方式改為 caching_sha2      | 舊版 client / driver 可能無法連線                       | 確認應用程式的 MySQL driver 版本支援 caching_sha2_password         |
| 保留字新增（RANK、ROW_NUMBER） | 用這些字當欄位名或別名的查詢會報語法錯                  | `grep -rn "RANK\|ROW_NUMBER\|GROUPS\|CUME_DIST" --include="*.sql"` |
| JSON 函式行為變更              | `JSON_MERGE` 改名為 `JSON_MERGE_PRESERVE`、行為語意不同 | 搜尋 `JSON_MERGE` 呼叫                                             |

### PostgreSQL 大版本升級的檢查點

PostgreSQL 的大版本升級相對穩定，但仍有需要確認的項目：extension 版本是否跟新 PostgreSQL 版本相容（特別是 PostGIS、pg_partman、timescaledb 這類複雜 extension）、`pg_upgrade` 的 `--check` 模式可以在不實際升級的前提下驗證相容性。

```bash
# PostgreSQL: 升級前 dry-run 檢查
pg_upgrade --old-datadir /var/lib/postgresql/13/main \
           --new-datadir /var/lib/postgresql/16/main \
           --old-bindir /usr/lib/postgresql/13/bin \
           --new-bindir /usr/lib/postgresql/16/bin \
           --check
```

### 應用程式層的查詢相容性

把應用程式的所有 SQL 查詢（ORM 產生的也算）對新版本跑一遍。重點是行為變更而非語法錯誤——語法錯誤會立刻報錯、容易抓；行為變更（排序結果不同、型別轉換規則不同）不會報錯、但結果錯誤。

```bash
# MySQL 升級前檢查工具
mysqlcheck --all-databases --check-upgrade
mysql_upgrade --upgrade-system-tables --dry-run
```

ORM 和 database driver 也要確認版本支援。PHP 的 `mysqli` 在 PHP 7.4+ 預設支援 caching_sha2_password、但舊版不支援。Node.js 的 `mysql2` 原生支援、但 `mysql`（舊套件）不支援。Python 的 `mysqlclient` 1.4+ 支援。

## 備份：升級前的保險

升級前的備份不是日常備份——它是一份明確的、經過驗證的、標記為「升級前保險點」的快照。

### 備份操作

```bash
# MySQL: 完整 dump（InnoDB 用 --single-transaction 避免鎖表）
mysqldump --all-databases --single-transaction --routines --triggers \
  --set-gtid-purged=OFF > pre-upgrade-$(date +%Y%m%d-%H%M).sql

# PostgreSQL: 完整 dump
pg_dumpall > pre-upgrade-$(date +%Y%m%d-%H%M).sql
```

RDS 環境：在升級操作前手動建立 snapshot，而非依賴自動備份。自動備份在升級過程中可能被新的快照覆蓋，手動 snapshot 不會被自動清除。

```bash
aws rds create-db-snapshot \
  --db-instance-identifier mydb-prod \
  --db-snapshot-identifier pre-upgrade-$(date +%Y%m%d)
```

### 備份驗證

備份存在不等於備份可用。驗證方式是把備份還原到一台獨立的測試實例、確認資料完整：

```bash
# 還原到測試實例
mysql -h test-instance -u admin -p < pre-upgrade-20260626-1400.sql

# 驗證關鍵表的 row count
mysql -h test-instance -e "SELECT COUNT(*) FROM orders; SELECT COUNT(*) FROM users;"
```

記錄還原時間：「從這份備份還原到可服務狀態需要 N 分鐘/小時」。這個數字是升級失敗時的停機時間下限——管理層需要這個數字來評估升級的風險。

## 平行驗證策略

在生產環境切換之前，先在新版本的平行環境上跑完所有驗證。平行驗證的目標是讓切換那一刻的風險降到最低——切換時已經知道新版本在相同資料和相同負載下的行為。

### 建立平行環境

| 方式                    | 適用情境                     | 資料同步方式                   |
| ----------------------- | ---------------------------- | ------------------------------ |
| Read replica + 版本升級 | RDS 環境、支援跨版本 replica | RDS 原生複寫                   |
| Logical replication     | 需要跨大版本                 | pg_logical / binlog → 新實例   |
| Dump / restore          | 任何環境、資料量可控         | 一次性 dump + 增量 binlog 回放 |

### 驗證項目

| 項目             | 方法                          | 通過標準                        |
| ---------------- | ----------------------------- | ------------------------------- |
| 應用程式測試套件 | 對新版本實例跑完整測試        | 0 failure                       |
| 查詢效能         | 對比兩個版本的 slow query log | p99 延遲無顯著退化（<10% 差異） |
| 資料一致性       | 關鍵表 row count + checksum   | 完全一致                        |
| 連線行為         | 應用程式連新版本、觀察連線池  | 無 authentication failure       |
| 備份還原         | 從新版本做一次 dump + restore | 還原成功、資料完整              |

平行驗證至少跑一週。時間越長、覆蓋到的邊界情境越多——月結批次、週期性報表、低頻排程任務都可能觸發只在特定條件下才出現的相容性問題。

## 切換策略

切換策略的選擇取決於三個變數的取捨：操作複雜度、停機時間、回退速度。

### In-place 升級

直接在原實例上升級版本。RDS 的操作是修改 engine version、等待升級完成。

- **停機**：升級期間實例不可用（MySQL 5.7→8.0 在 RDS 上約 10-30 分鐘，視資料量而定）
- **回退**：從 pre-upgrade snapshot 還原，需要 snapshot restore 時間（分鐘到小時級）
- **適用**：可接受計畫性停機的環境、資料量不大

### Blue-green 切換

在新版本上建立獨立實例、透過 replication 同步資料、切換應用程式的連線端點。

- **停機**：接近零（DNS TTL 或 endpoint 切換的傳播時間）
- **回退**：把連線端點切回舊實例，舊實例持續運行
- **複雜度**：需要維護兩個實例的同步、切換時要處理複寫延遲
- **適用**：不能接受停機的 production 環境

RDS 從 2022 年開始提供原生的 Blue/Green Deployments 功能，簡化了同步與切換的操作：

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name mydb-upgrade \
  --source arn:aws:rds:ap-northeast-1:123456789012:db:mydb-prod \
  --target-engine-version 8.0.35
```

### Read replica 升級後提升

建立指定新版本的 read replica，replica 同步完成後提升為獨立實例，應用程式切換連線。

- **停機**：提升 replica 的幾秒 + 連線切換
- **回退**：舊 primary 仍在，切回即可
- **限制**：不是所有版本組合都支援跨版本 replica

### 選型判準

| 考量       | In-place               | Blue-green       | Replica 提升         |
| ---------- | ---------------------- | ---------------- | -------------------- |
| 操作複雜度 | 低                     | 中               | 中                   |
| 停機時間   | 10-30 分鐘             | 接近零           | 幾秒                 |
| 回退速度   | 慢（snapshot restore） | 快（切回舊端點） | 快（切回舊 primary） |
| 成本       | 最低                   | 升級期間雙倍     | 升級期間雙倍         |

## 升級後的驗證與監控

切換完成後的 48-72 小時是觀察期。這段時間舊實例保持可用狀態，直到確認新版本穩定才退役。

### 切換後立即驗證

1. 應用程式的所有關鍵路徑可正常操作（登入、查詢、寫入、交易）
2. 連線池行為正常（沒有持續的 authentication failure 或 connection reset）
3. 排程任務（cron job、背景 worker）正常連線並執行

### 效能監控

比較升級前後的關鍵指標：

```bash
# 觀察升級後的 slow query 數量
mysql -e "SHOW GLOBAL STATUS LIKE 'Slow_queries';"

# 比較 p99 延遲（需要 application-level metrics）
# CloudWatch: DBInstanceIdentifier → ReadLatency, WriteLatency
```

升級後效能退化的常見原因：optimizer 行為改變（新版本選了不同的執行計畫）、buffer pool 冷啟動（升級後快取是空的、前幾小時延遲偏高是正常的）。如果 48 小時後延遲仍未回到基線，檢查 slow query log 找出退化的具體查詢。

### 舊實例退役

觀察期結束、新版本確認穩定後：

1. 停止舊實例的 replication（如果仍在同步）
2. 保留舊實例的 final snapshot
3. 刪除舊實例（先確認 deletion protection 關閉是刻意的、不是誤操作）
4. 更新文件：記錄升級日期、版本號、升級過程中遇到的問題

## 時程與管理層溝通

| 升級類型                           | 典型時程                            | 停機窗口   |
| ---------------------------------- | ----------------------------------- | ---------- |
| Minor version（5.7.x → 5.7.y）     | 2-4 小時計畫維護                    | 10-15 分鐘 |
| Major version（5.7 → 8.0）in-place | 1-2 週（評估 + 驗證 + 切換 + 監控） | 10-30 分鐘 |
| Major version blue-green           | 2-3 週（含平行運行期）              | 接近零     |

向管理層說明時的關鍵框架：資料是不可重建的，升級策略是「在旁邊建一個新版本的資料庫、驗證它在相同資料和相同負載下行為正確、然後切過去」。多出來的時間買的是「切換那一刻的信心」和「出問題時能快速回退」——兩者對生產服務都是必要的保險。

## 跨分類引用

- → [升級的共通操作框架](/infra/upgrade/upgrade-framework/)：四階段模型的通用說明
- → [Stateful 資源保護與依賴表達](/infra/05-core-services/stateful-protection-dependency/)：multi-AZ、備份、deletion protection 的 IaC 描述
- → [無 SSH 環境的資料庫備份與變更管理](/infra/takeover/legacy-database-backup-migration/)：接手環境的資料庫備份策略
